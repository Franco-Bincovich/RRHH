"""Repositorio de proyecto_asignaciones. Acceso a Supabase con supabase_admin."""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.proyectos import AsignacionResponse
from utils.errors import AppError

_T = "proyecto_asignaciones"


def _build(rows: List[dict]) -> List[AsignacionResponse]:
    """Enriquece con empleado_nombre y empresa_nombre del empleado."""
    if not rows:
        return []
    emp_ids = list({r["empleado_id"] for r in rows})
    emp_empresa_ids = list({r["empleado_empresa_id"] for r in rows})
    emp_map = {
        e["id"]: f"{e['nombre']} {e['apellido']}"
        for e in (supabase_admin.table("empleados").select("id, nombre, apellido")
                  .in_("id", emp_ids).execute().data or [])
    }
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", emp_empresa_ids).execute().data or [])
    }
    return [
        AsignacionResponse.model_validate({
            **r,
            "empleado_nombre": emp_map.get(r["empleado_id"]),
            "empleado_empresa_nombre": empresa_map.get(r["empleado_empresa_id"]),
        })
        for r in rows
    ]


def find_empresa_for_empleado(empleado_id: str) -> Optional[str]:
    """Retorna empresa_id del empleado. None si no existe."""
    res = (supabase_admin.table("empleados").select("empresa_id")
           .eq("id", empleado_id).maybe_single().execute())
    return str(res.data["empresa_id"]) if (res and res.data) else None


def get_estado_empleado(empleado_id: str) -> Optional[str]:
    """Retorna estado del empleado. None si no existe."""
    res = (supabase_admin.table("empleados").select("estado")
           .eq("id", empleado_id).maybe_single().execute())
    return res.data.get("estado") if (res and res.data) else None


class AsignacionesRepo:
    def find_by_proyecto(self, proyecto_id: str) -> List[AsignacionResponse]:
        """Asignaciones del proyecto, ordenadas por fecha de creación."""
        rows = (supabase_admin.table(_T).select("*")
                .eq("proyecto_id", proyecto_id).order("created_at").execute().data or [])
        return _build(rows)

    def find_by_id(self, id: str) -> Optional[AsignacionResponse]:
        res = supabase_admin.table(_T).select("*").eq("id", id).maybe_single().execute()
        return _build([res.data])[0] if (res and res.data) else None

    def save(
        self, proyecto_id: str, empleado_id: str, empleado_empresa_id: str,
        rol: str, valor_hora: float, fecha_desde=None, fecha_hasta=None,
    ) -> AsignacionResponse:
        """Inserta asignación. empleado_empresa_id proviene del service (lookup empleado)."""
        payload: dict = {
            "proyecto_id": proyecto_id, "empleado_id": empleado_id,
            "empleado_empresa_id": empleado_empresa_id,
            "rol": rol, "valor_hora": valor_hora,
        }
        if fecha_desde:
            payload["fecha_desde"] = str(fecha_desde)
        if fecha_hasta:
            payload["fecha_hasta"] = str(fecha_hasta)
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            raise AppError("Error al crear la asignación", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, patch: dict) -> Optional[AsignacionResponse]:
        if patch:
            supabase_admin.table(_T).update(patch).eq("id", id).execute()
        return self.find_by_id(id)

    def delete(self, id: str) -> bool:
        return bool(supabase_admin.table(_T).delete().eq("id", id).execute().data)

    def has_horas(self, asignacion_id: str) -> bool:
        res = (supabase_admin.table("horas_proyecto").select("id")
               .eq("asignacion_id", asignacion_id).limit(1).execute())
        return bool(res.data)
