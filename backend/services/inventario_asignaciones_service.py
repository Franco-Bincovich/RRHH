"""
Servicio de asignaciones de inventario.
Flujo: router → service → repository → DB

Reglas:
  - empresa_id se hereda del ítem al asignar — no lo provee el usuario.
  - La FK compuesta en DB garantiza que ítem y empleado son de la misma empresa.
  - El índice único parcial en DB garantiza un solo ítem activo a la vez.
  - Al asignar: ítem pasa a estado='asignado'.
  - Al devolver con ok: ítem pasa a 'disponible'. Con con_daño: 'en_reparacion'.
"""
from typing import Optional
from uuid import UUID

from repositories.inventario_asignaciones_repo import InventarioAsignacionesRepo
from repositories.inventario_items_repo import InventarioItemsRepo
from schemas.inventario import (
    AsignacionCreate, AsignacionListResponse, AsignacionResponse, DevolucionRequest,
)
from services._inventario_export import construir_filas_export
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class InventarioAsignacionesService:
    def __init__(
        self,
        repo: Optional[InventarioAsignacionesRepo] = None,
        items_repo: Optional[InventarioItemsRepo] = None,
    ) -> None:
        self._repo = repo or InventarioAsignacionesRepo()
        self._items = items_repo or InventarioItemsRepo()

    def get_all(self, empresa_id: Optional[UUID] = None, empleado_id: Optional[str] = None) -> AsignacionListResponse:
        """Retorna asignaciones activas (sin fecha_devolucion). None = todas las empresas."""
        items = self._repo.find_all(empresa_id, empleado_id)
        return AsignacionListResponse(items=items, total=len(items))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", empleado_id: Optional[str] = None) -> Descarga:
        """Exporta las asignaciones activas (columnas legibles, sin UUIDs) respetando el filtro
        de empleado. None = consolidado (todas las empresas). El motor genérico no se toca."""
        datos = {"Asignaciones": construir_filas_export(self._repo.find_all(empresa_id, empleado_id))}
        return build_export(nombre="Inventario asignado", datos=datos, filename_base="inventario_asignaciones", formato=formato)

    def get_historial(self, item_id: UUID, empresa_id: Optional[UUID] = None) -> AsignacionListResponse:
        """
        Retorna el historial completo de asignaciones de un ítem.

        Raises:
            AppError: ITEM_NOT_FOUND (404) si el ítem no existe o no pertenece a la empresa.
        """
        if not self._items.find_by_id(str(item_id), empresa_id):
            raise AppError("Ítem no encontrado", "ITEM_NOT_FOUND", 404)
        items = self._repo.find_historial(str(item_id))
        return AsignacionListResponse(items=items, total=len(items))

    def asignar(self, data: AsignacionCreate, created_by: str) -> AsignacionResponse:
        """
        Asigna un ítem a un empleado.
        empresa_id se resuelve del ítem — no lo provee el usuario.
        La FK compuesta en DB rechaza cruces entre empresas.

        Raises:
            AppError: ITEM_NOT_FOUND (404).
            AppError: ITEM_NO_DISPONIBLE (409) si estado != 'disponible'.
        """
        empresa_id = self._items.find_empresa_for(str(data.item_id))
        if not empresa_id:
            raise AppError("Ítem no encontrado", "ITEM_NOT_FOUND", 404)
        item = self._items.find_by_id(str(data.item_id))
        if not item or item.estado != "disponible":
            estado_actual = item.estado if item else "desconocido"
            raise AppError(
                f"El ítem no está disponible (estado: {estado_actual})",
                "ITEM_NO_DISPONIBLE", 409,
            )
        row = self._repo.save(str(data.item_id), empresa_id, str(data.empleado_id))
        self._items.set_estado(str(data.item_id), "asignado")
        logger.info("Ítem asignado", extra={
            "item_id": str(data.item_id), "empleado_id": str(data.empleado_id), "created_by": created_by,
        })
        return row

    def devolver(self, asignacion_id: UUID, data: DevolucionRequest,
                 empresa_id: Optional[UUID] = None) -> AsignacionResponse:
        """
        Registra la devolución de un ítem.
        Estado resultante del ítem: 'disponible' (ok) | 'en_reparacion' (con_daño).

        `empresa_id` acota la asignación a la empresa activa (None = consolidado); una ajena da
        el MISMO 404 que una inexistente.

        Raises:
            AppError: ESTADO_DEVOLUCION_INVALIDO (422).
            AppError: ASIGNACION_NOT_FOUND (404) si no existe, es de otra empresa o ya fue devuelta.
        """
        if data.estado_devolucion not in ("ok", "con_daño"):
            raise AppError("Usá 'ok' o 'con_daño'", "ESTADO_DEVOLUCION_INVALIDO", 422)
        asig = self._repo.find_by_id(str(asignacion_id), empresa_id)
        if not asig or asig.fecha_devolucion is not None:
            raise AppError("Asignación no encontrada o ya devuelta", "ASIGNACION_NOT_FOUND", 404)
        updated = self._repo.devolver(str(asignacion_id), data.estado_devolucion, data.notas)
        nuevo_estado = "disponible" if data.estado_devolucion == "ok" else "en_reparacion"
        self._items.set_estado(asig.item_id, nuevo_estado)
        logger.info("Ítem devuelto", extra={"asignacion_id": str(asignacion_id), "estado": data.estado_devolucion})
        return updated  # type: ignore[return-value]
