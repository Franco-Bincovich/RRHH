"""
Servicio de ítems de inventario.
Flujo: router → service → repository → DB

Reglas:
  - empresa_id viene explícito en Create (catálogo por empresa).
  - Estado del ítem lo gestiona este service (CRUD) y el de asignaciones (asignar/devolver).
  - Borrado: soft-delete (estado='baja') si tiene historial de asignaciones; hard-delete si no.
  - No se puede eliminar un ítem actualmente asignado.
"""
from typing import Optional
from uuid import UUID

from repositories.inventario_items_repo import InventarioItemsRepo
from schemas.inventario import ItemCreate, ItemListResponse, ItemResponse, ItemUpdate
from services._inventario_items_export import construir_filas_export
from services._paginacion import cantidad_paginas
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class InventarioItemsService:
    def __init__(self, repo: Optional[InventarioItemsRepo] = None) -> None:
        self._repo = repo or InventarioItemsRepo()

    def get_all(self, empresa_id: Optional[UUID] = None, estado: Optional[str] = None,
                area_id: Optional[UUID] = None, page: int = 1, page_size: int = 20) -> ItemListResponse:
        """Página de ítems filtrados por empresa, estado y/o área. None = todos.

        `total` sale del `count="exact"` de la MISMA query, no de `len(items)`: es el total del
        filtro sin paginar, que es lo que la barra necesita y lo que el export chequea."""
        items, total = self._repo.find_all(empresa_id, estado, area_id, page, page_size)
        return ItemListResponse(items=items, total=total, page=page, page_size=page_size,
                                total_pages=cantidad_paginas(total, page_size))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", estado: Optional[str] = None, area_id: Optional[UUID] = None) -> Descarga:
        """Exporta el catálogo de ítems (columnas legibles, sin UUIDs) respetando los filtros
        de estado y área. None = consolidado (todas las empresas). El motor genérico no se toca."""
        pagina = self.get_all(empresa_id, estado, area_id, 1, LIMITE_FILAS_EXPORT)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        datos = {"Ítems": construir_filas_export(pagina.items)}
        return build_export(nombre="Inventario de ítems", datos=datos, filename_base="inventario_items", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> ItemResponse:
        """Raises ITEM_NOT_FOUND (404) si no existe o no pertenece a la empresa."""
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Ítem no encontrado", "ITEM_NOT_FOUND", 404)
        return row

    def create(self, data: ItemCreate, created_by: str) -> ItemResponse:
        """
        Crea un ítem en el catálogo de la empresa.

        Raises:
            AppError: NOMBRE_REQUERIDO (422), TIPO_REQUERIDO (422).
        """
        if not data.nombre.strip():
            raise AppError("El nombre es requerido", "NOMBRE_REQUERIDO", 422)
        if not data.tipo.strip():
            raise AppError("El tipo es requerido", "TIPO_REQUERIDO", 422)
        row = self._repo.save(data)
        logger.info("Ítem de inventario creado", extra={"item_id": row.id, "created_by": created_by})
        return row

    def update(self, id: UUID, data: ItemUpdate, empresa_id: Optional[UUID] = None) -> ItemResponse:
        """
        Actualización parcial de un ítem.

        Raises:
            AppError: ITEM_NOT_FOUND (404).
        """
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Ítem no encontrado", "ITEM_NOT_FOUND", 404)
        updated = self._repo.update(str(id), data, empresa_id)
        logger.info("Ítem actualizado", extra={"item_id": str(id)})
        return updated  # type: ignore[return-value]

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """
        Soft-delete (estado='baja') si tiene historial; hard-delete si no tiene asignaciones.

        Raises:
            AppError: ITEM_NOT_FOUND (404).
            AppError: ITEM_ASIGNADO (409) si el ítem está actualmente asignado.
        """
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Ítem no encontrado", "ITEM_NOT_FOUND", 404)
        if row.estado == "asignado":
            raise AppError(
                "No se puede eliminar un ítem asignado. Primero registrá su devolución.",
                "ITEM_ASIGNADO", 409,
            )
        if self._repo.has_asignaciones(str(id)):
            self._repo.set_estado(str(id), "baja")
            logger.info("Ítem dado de baja (tiene historial)", extra={"item_id": str(id)})
        else:
            self._repo.delete(str(id), empresa_id)
            logger.info("Ítem eliminado", extra={"item_id": str(id)})
