"""
Servicio de catálogo de capacitaciones.
Flujo: router → service → repository → DB

Reglas de negocio:
  - empresa_id viene explícito en el body al crear (catálogo por empresa).
  - Borrado: soft-delete (activo=False) si tiene asignaciones; hard-delete si no.
"""
from typing import Optional
from uuid import UUID

from repositories.capacitacion_repo import CapacitacionRepo
# 🔴 `_capacitaciones_catalogo_export`, NO `_capacitaciones_export`: aquel es el export de
# ASIGNACIONES (quién hizo cuál) y este el del CATÁLOGO (qué capacitaciones existen).
from services._capacitaciones_catalogo_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.export import Descarga, build_export
from schemas.capacitacion import (
    CapacitacionCreate, CapacitacionListResponse, CapacitacionResponse, CapacitacionUpdate,
)
from utils.errors import AppError
from utils.logger import logger


class CapacitacionService:
    def __init__(self, repo: Optional[CapacitacionRepo] = None) -> None:
        self._repo = repo or CapacitacionRepo()

    def get_all(self, empresa_id: Optional[UUID] = None, solo_activos: bool = True) -> CapacitacionListResponse:
        """Retorna el catálogo filtrado por empresa (None=todas). Por defecto solo activos."""
        items = self._repo.find_all(empresa_id, solo_activos)
        return CapacitacionListResponse(items=items, total=len(items))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", solo_activos: bool = True) -> Descarga:
        """Exporta el catálogo con el MISMO filtro que el listado (`solo_activos`), por el mismo
        `find_all`. Sin ese parámetro el archivo traería las inactivas que la pantalla oculta —
        exactamente el bug que la invariante list↔export existe para evitar."""
        items = self._repo.find_all(empresa_id, solo_activos)
        verificar_limite_export(len(items))
        datos = {"Capacitaciones": construir_filas_export(items)}
        return build_export(nombre="Catálogo de capacitaciones", datos=datos, filename_base="capacitaciones", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> CapacitacionResponse:
        """
        Retorna una capacitación por ID.

        Raises:
            AppError: CAPACITACION_NOT_FOUND (404) si no existe o no pertenece a la empresa.
        """
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Capacitación no encontrada", "CAPACITACION_NOT_FOUND", 404)
        return row

    def create(self, data: CapacitacionCreate, created_by: str) -> CapacitacionResponse:
        """
        Crea una capacitación en el catálogo de la empresa.

        Raises:
            AppError: NOMBRE_REQUERIDO (422) si el nombre está en blanco.
        """
        if not data.nombre.strip():
            raise AppError("El nombre es requerido", "NOMBRE_REQUERIDO", 422)
        row = self._repo.save(data)
        logger.info("Capacitación creada", extra={"capacitacion_id": row.id, "created_by": created_by})
        return row

    def update(self, id: UUID, data: CapacitacionUpdate, empresa_id: Optional[UUID] = None) -> CapacitacionResponse:
        """
        Actualiza parcialmente una capacitación.

        Raises:
            AppError: CAPACITACION_NOT_FOUND (404), NOMBRE_REQUERIDO (422).
        """
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Capacitación no encontrada", "CAPACITACION_NOT_FOUND", 404)
        payload = data.model_dump(exclude_none=True)
        if "nombre" in payload and not payload["nombre"].strip():
            raise AppError("El nombre es requerido", "NOMBRE_REQUERIDO", 422)
        updated = self._repo.update(str(id), empresa_id, payload)
        logger.info("Capacitación actualizada", extra={"capacitacion_id": str(id)})
        return updated  # type: ignore[return-value]

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """
        Soft-delete si tiene asignaciones; hard-delete si no.

        Raises:
            AppError: CAPACITACION_NOT_FOUND (404) si no existe.
        """
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Capacitación no encontrada", "CAPACITACION_NOT_FOUND", 404)
        if self._repo.has_asignaciones(str(id)):
            self._repo.set_activo(str(id), empresa_id, False)
            logger.info("Capacitación desactivada (tiene asignaciones)", extra={"capacitacion_id": str(id)})
        else:
            self._repo.delete(str(id), empresa_id)
            logger.info("Capacitación eliminada", extra={"capacitacion_id": str(id)})
