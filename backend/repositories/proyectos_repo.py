"""Repositorio de proyectos. Acceso a Supabase con supabase_admin."""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._area_scope import proyecto_ids_con_area
from repositories._proyectos_enrich import batch_costos, enriquecer
from schemas.proyectos import ProyectoCreate, ProyectoResponse
from utils.errors import AppError

_T = "proyectos"


class ProyectosRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, estado: Optional[str] = None,
                 area_id: Optional[UUID] = None) -> List[ProyectoResponse]:
        """Proyectos de la empresa dueña (None = todas), con costeo batch.
        `area_id` acota a los que tienen al menos un empleado asignado de esa área — la
        semántica completa (y por qué no se acota por empresa) está en _area_scope."""
        if area_id:
            ids = proyecto_ids_con_area(area_id)
            if not ids:
                return []
        q = supabase_admin.table(_T).select("*").order("created_at", desc=True)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if estado:
            q = q.eq("estado", estado)
        if area_id:
            q = q.in_("id", ids)
        rows = q.execute().data or []
        if not rows:
            return []
        return enriquecer(rows, batch_costos([r["id"] for r in rows]))

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[ProyectoResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        if not res.data:
            return None
        return enriquecer([res.data], batch_costos([res.data["id"]]))[0]

    def find_empresa_for(self, proyecto_id: str) -> Optional[str]:
        """Retorna empresa_id (dueña) del proyecto."""
        res = supabase_admin.table(_T).select("empresa_id").eq("id", proyecto_id).maybe_single().execute()
        return str(res.data["empresa_id"]) if res.data else None

    def save(self, data: ProyectoCreate) -> ProyectoResponse:
        payload = {k: (str(v) if isinstance(v, UUID) else (str(v) if hasattr(v, "isoformat") else v))
                   for k, v in data.model_dump().items() if v is not None}
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            raise AppError("Error al crear el proyecto", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, patch: dict, empresa_id: Optional[UUID] = None) -> Optional[ProyectoResponse]:
        if patch:
            q = supabase_admin.table(_T).update(patch).eq("id", id)
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            q.execute()
        return self.find_by_id(id, empresa_id)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = supabase_admin.table(_T).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)

    def has_horas(self, proyecto_id: str) -> bool:
        res = supabase_admin.table("horas_proyecto").select("id").eq("proyecto_id", proyecto_id).limit(1).execute()
        return bool(res.data)
