"""
Servicio de áreas. Lógica de negocio del módulo de Áreas.
Flujo: router → service → repository → DB
"""
from typing import List, Optional
from uuid import UUID

from repositories.area_repo import AreaRepo
from schemas.area import AreaCreate, AreaResponse, AreaUpdate
from services._areas_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class AreaService:
    def __init__(self, repo: Optional[AreaRepo] = None) -> None:
        self._repo = repo or AreaRepo()

    def get_areas(self, empresa_id: Optional[str] = None) -> List[AreaResponse]:
        """
        Retorna la lista de áreas activas con su cantidad de empleados.

        Args:
            empresa_id: Si se provee, filtra las áreas de esa empresa.
                        Si es None, retorna todas las áreas.

        Returns:
            Lista de AreaResponse ordenada por nombre.
        """
        return self._repo.find_all(empresa_id)

    def exportar(self, empresa_id: Optional[str] = None, formato: str = "excel") -> Descarga:
        """Exporta el listado de áreas (columnas legibles, sin UUIDs) con el MISMO filtro que el
        listado. Va por el mismo `find_all`, así que el archivo no puede traer filas que la
        pantalla no muestre. None = todas las empresas. El motor genérico no se toca."""
        items = self._repo.find_all(empresa_id)
        verificar_limite_export(len(items))
        datos = {"Áreas": construir_filas_export(items)}
        return build_export(nombre="Áreas", datos=datos, filename_base="areas", formato=formato)

    def get_area(self, id: UUID, empresa_id: Optional[str] = None) -> AreaResponse:
        """
        Retorna el detalle de un área por ID.

        Args:
            id: UUID del área a consultar.

        Returns:
            AreaResponse con todos los campos del área.

        Raises:
            AppError: AREA_NOT_FOUND (404) si no existe, está inactiva o es de otra empresa
                (mismo code y mensaje: no confirma la existencia de áreas ajenas).
        """
        area = self._repo.find_by_id(str(id), empresa_id)
        if not area:
            raise AppError("Área no encontrada", "AREA_NOT_FOUND", 404)
        return area

    def create_area(self, data: AreaCreate, created_by: str) -> AreaResponse:
        """
        Crea una nueva área en el sistema.

        Args:
            data: Datos del área a crear (empresa_id + nombre requeridos).
            created_by: ID del usuario que realiza la operación (trazabilidad).

        Returns:
            AreaResponse con los datos del área creada, incluyendo su ID generado.
        """
        area = self._repo.save(data)
        logger.info("Área creada", extra={"area_id": area.id, "created_by": created_by})
        return area

    def update_area(self, id: UUID, data: AreaUpdate, empresa_id: Optional[str] = None) -> AreaResponse:
        """
        Actualiza los datos de un área existente (actualización parcial).

        Args:
            id: UUID del área a actualizar.
            data: Campos a actualizar — solo los no-None se aplican.

        Returns:
            AreaResponse con los datos actualizados.

        Raises:
            AppError: AREA_NOT_FOUND (404) si no existe o es de otra empresa.
        """
        area = self._repo.update(str(id), data, empresa_id)
        if not area:
            raise AppError("Área no encontrada", "AREA_NOT_FOUND", 404)
        logger.info("Área actualizada", extra={"area_id": str(id)})
        return area

    def delete_area(self, id: UUID, empresa_id: Optional[str] = None) -> bool:
        """
        Elimina lógicamente un área (soft delete — pone activo=False).

        Args:
            id: UUID del área a eliminar.

        Returns:
            True si la operación fue exitosa.

        Raises:
            AppError: AREA_NOT_FOUND (404) si no existe o es de otra empresa.
        """
        if not self._repo.delete(str(id), empresa_id):
            raise AppError("Área no encontrada", "AREA_NOT_FOUND", 404)
        logger.info("Área eliminada", extra={"area_id": str(id)})
        return True
