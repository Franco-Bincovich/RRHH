"""Repositorio de asignaciones de capacitaciones (empleado_capacitacion). supabase_admin."""
from datetime import date
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

# El enriquecido vive en `_asignacion_row` (molde `_ausencia_row`): este archivo estaba en 97/100
# y el manejo de `empleado_id` NULL de la migración 116 no entraba con su porqué escrito.
from repositories._asignacion_row import _build
from schemas.capacitacion import AsignacionResponse
from utils.errors import AppError
from utils.logger import logger

_T = "empleado_capacitacion"


class AsignacionRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None, capacitacion_id: Optional[UUID] = None, estado: Optional[str] = None, area_id: Optional[UUID] = None) -> List[AsignacionResponse]:
        """Retorna asignaciones filtradas por empresa, empleado, capacitación, estado y/o área."""
        emp_ids: Optional[List[str]] = None
        if area_id:
            q = supabase_admin.table("empleados").select("id").eq("area_id", str(area_id))
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            data = q.execute().data or []
            if not data:
                return []
            emp_ids = [e["id"] for e in data]
        q = supabase_admin.table(_T).select("*").order("created_at", desc=True)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_id:
            q = q.eq("empleado_id", str(empleado_id))
        if capacitacion_id:
            q = q.eq("capacitacion_id", str(capacitacion_id))
        if estado:
            q = q.eq("estado", estado)
        if emp_ids:
            q = q.in_("empleado_id", emp_ids)
        return _build(q.execute().data or [])

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[AsignacionResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if res.data else None

    def save(self, capacitacion_id: str, empleado_id: str, empresa_id: str, fecha_asignacion: Optional[date], fecha_limite: Optional[date]) -> AsignacionResponse:
        """Inserta asignación y retorna el registro enriquecido."""
        res = supabase_admin.table(_T).insert({
            "capacitacion_id": capacitacion_id, "empleado_id": empleado_id, "empresa_id": empresa_id,
            "estado": "pendiente",
            "fecha_asignacion": str(fecha_asignacion) if fecha_asignacion else None,
            "fecha_limite": str(fecha_limite) if fecha_limite else None,
        }).execute()
        if not res.data:
            logger.error("Supabase insert vacío en empleado_capacitacion")
            raise AppError("Error al asignar la capacitación", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, empresa_id: Optional[UUID], payload: dict) -> Optional[AsignacionResponse]:
        if payload:
            q = supabase_admin.table(_T).update(payload).eq("id", id)
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            q.execute()
        return self.find_by_id(id, empresa_id)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = supabase_admin.table(_T).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)

    def find_empresa_for_empleado(self, empleado_id: str) -> Optional[str]:
        """Retorna empresa_id del empleado, o None si no existe."""
        res = supabase_admin.table("empleados").select("empresa_id").eq("id", empleado_id).maybe_single().execute()
        return str(res.data["empresa_id"]) if res.data else None
