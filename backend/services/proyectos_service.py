"""
Servicio de proyectos. CRUD con costeo calculado en batch.
Flujo: router → service → repository → DB
costo_acumulado = SUM(horas × valor_hora_snapshot) — patrón get_saldo de vacaciones.
"""
from typing import Optional
from uuid import UUID

from repositories.proyectos_repo import ProyectosRepo
from schemas.proyectos import (
    ProyectoCreate, ProyectoListResponse, ProyectoResponse, ProyectoUpdate,
)
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._paginacion import cantidad_paginas
from services._proyectos_export import construir_filas_export
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger

_ESTADOS = {"activo", "pausado", "cerrado", "cancelado"}


class ProyectosService:
    def __init__(self, repo: Optional[ProyectosRepo] = None) -> None:
        self._repo = repo or ProyectosRepo()

    def get_all(self, empresa_id: Optional[UUID] = None, estado: Optional[str] = None,
                area_id: Optional[UUID] = None, page: int = 1, page_size: int = 20) -> ProyectoListResponse:
        """
        Lista proyectos de la empresa dueña. None = todas. Costeo calculado en batch.

        Returns:
            ProyectoListResponse con cada proyecto incluyendo costo_acumulado, presupuesto_restante, pct_consumido.
        """
        items, total = self._repo.find_all(empresa_id, estado, area_id, page, page_size)
        return ProyectoListResponse(items=items, total=total, page=page, page_size=page_size,
                                    total_pages=cantidad_paginas(total, page_size))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", estado: Optional[str] = None, area_id: Optional[UUID] = None) -> Descarga:
        """Exporta el listado de proyectos (columnas legibles, sin UUIDs) con los MISMOS filtros
        que el listado. Va por el mismo `find_all`, así que el archivo no puede traer filas que
        la pantalla no muestre. None = consolidado. El motor genérico no se toca."""
        pagina = self.get_all(empresa_id, estado, area_id, 1, LIMITE_FILAS_EXPORT)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        datos = {"Proyectos": construir_filas_export(pagina.items)}
        return build_export(nombre="Proyectos", datos=datos, filename_base="proyectos", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> ProyectoResponse:
        """
        Retorna un proyecto con costeo actualizado.

        Raises:
            AppError: PROYECTO_NOT_FOUND (404).
        """
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        return row

    def create(self, data: ProyectoCreate) -> ProyectoResponse:
        """
        Crea un proyecto para la empresa dueña indicada en el body.

        Raises:
            AppError: NOMBRE_REQUERIDO (422), ESTADO_INVALIDO (422).
        """
        if not data.nombre.strip():
            raise AppError("El nombre es requerido", "NOMBRE_REQUERIDO", 422)
        if data.estado not in _ESTADOS:
            raise AppError(f"Estado inválido: {data.estado}", "ESTADO_INVALIDO", 422)
        row = self._repo.save(data)
        logger.info("Proyecto creado", extra={"proyecto_id": str(row.id)})
        return row

    def update(self, id: UUID, data: ProyectoUpdate, empresa_id: Optional[UUID] = None) -> ProyectoResponse:
        """
        Actualización parcial. empresa_id (dueña) no es modificable.

        Raises:
            AppError: PROYECTO_NOT_FOUND (404), ESTADO_INVALIDO (422).
        """
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        if data.estado and data.estado not in _ESTADOS:
            raise AppError(f"Estado inválido: {data.estado}", "ESTADO_INVALIDO", 422)
        patch = {}
        for k, v in data.model_dump(exclude_none=True).items():
            patch[k] = str(v) if hasattr(v, "isoformat") else v
        updated = self._repo.update(str(id), patch, empresa_id)
        logger.info("Proyecto actualizado", extra={"proyecto_id": str(id)})
        return updated  # type: ignore[return-value]

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """
        Elimina proyecto. Rechaza si tiene horas registradas o gente asignada.

        🔴 LAS DOS GUARDAS, no una: `horas_proyecto` y `proyecto_asignaciones` son las dos
        ON DELETE RESTRICT. Con sólo la de horas, un proyecto con gente asignada y sin horas
        cargadas llegaba al DELETE y salía **500** (23503) en vez de un 409 que se pueda leer.

        Raises:
            AppError: PROYECTO_NOT_FOUND (404), PROYECTO_CON_HORAS (409),
                      PROYECTO_CON_ASIGNACIONES (409).
        """
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        if self._repo.has_horas(str(id)):
            raise AppError(
                "No se puede eliminar un proyecto con horas registradas",
                "PROYECTO_CON_HORAS", 409,
            )
        if self._repo.has_asignaciones(str(id)):
            raise AppError(
                "No se puede eliminar un proyecto con colaboradores asignados. "
                "Quitá primero las asignaciones.",
                "PROYECTO_CON_ASIGNACIONES", 409,
            )
        self._repo.delete(str(id), empresa_id)
        logger.info("Proyecto eliminado", extra={"proyecto_id": str(id)})
