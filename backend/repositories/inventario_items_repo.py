"""Repositorio de inventario_items. Acceso a Supabase con supabase_admin."""
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._inventario_items_row import _build
from repositories._inventario_scope import items_de_area
from schemas.inventario import ItemCreate, ItemResponse, ItemUpdate
from utils.errors import AppError
from utils.logger import logger

_T = "inventario_items"


class InventarioItemsRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, estado: Optional[str] = None,
                 area_id: Optional[UUID] = None, page: int = 1, page_size: int = 20,
                 ) -> Tuple[List[ItemResponse], int]:
        """Retorna ítems filtrados por empresa, estado y/o área, ordenados por nombre.

        El área se resuelve a ítems en `_inventario_scope`, que documenta qué significa el
        filtro y por qué un ítem sin asignación activa no cae bajo ninguna área.
        """
        if area_id:
            ids = items_de_area(area_id, empresa_id)
            if not ids:
                # área sin ítems en mano: `.in_([])` no es un WHERE válido. El total es 0, no
                # `len([])` de una lista que nunca se consultó — son lo mismo acá, pero el
                # contrato de la tupla no admite devolver solo la lista.
                return [], 0
        # `.order("id")` = desempate: `nombre` no es único (dos notebooks del mismo modelo
        # empatan), y sin él una fila puede salir en dos páginas o en ninguna. ASC, que es la
        # forma de `idx_inv_items_empresa_nombre` (migración 118).
        q = supabase_admin.table(_T).select("*", count="exact").order("nombre").order("id")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if estado:
            q = q.eq("estado", estado)
        if area_id:
            q = q.in_("id", ids)
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return _build(res.data or []), (res.count or 0)

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[ItemResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if res.data else None

    def find_empresa_for(self, id: str) -> Optional[str]:
        """Retorna empresa_id del ítem, o None si no existe."""
        res = supabase_admin.table(_T).select("empresa_id").eq("id", id).maybe_single().execute()
        return str(res.data["empresa_id"]) if res.data else None

    def has_asignaciones(self, id: str) -> bool:
        """True si el ítem tiene al menos una asignación (histórica o activa)."""
        res = supabase_admin.table("inventario_asignaciones").select("id").eq("item_id", id).limit(1).execute()
        return bool(res.data)

    def save(self, data: ItemCreate) -> ItemResponse:
        """Inserta un ítem y retorna el registro enriquecido."""
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        payload["empresa_id"] = str(data.empresa_id)
        if data.fecha_alta:
            payload["fecha_alta"] = str(data.fecha_alta)
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            logger.error("Supabase insert vacío en inventario_items")
            raise AppError("Error al crear el ítem", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, data: ItemUpdate, empresa_id: Optional[UUID] = None) -> Optional[ItemResponse]:
        patch = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        if patch:
            q = supabase_admin.table(_T).update(patch).eq("id", id)
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            q.execute()
        return self.find_by_id(id, empresa_id)

    def set_estado(self, id: str, estado: str) -> None:
        """Actualiza solo el estado del ítem (llamado por el service de asignaciones)."""
        supabase_admin.table(_T).update({"estado": estado}).eq("id", id).execute()

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = supabase_admin.table(_T).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)
