"""Repositorio de inventario_asignaciones. Acceso a Supabase con supabase_admin."""
from datetime import date
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._scope_filtros import empleados_de_area
from schemas.inventario import AsignacionResponse
from utils.errors import AppError
from utils.logger import logger

_T = "inventario_asignaciones"


def _build(rows: List[dict]) -> List[AsignacionResponse]:
    """Enriquece filas con empresa_nombre, campos del ítem y empleado_nombre."""
    if not rows:
        return []
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", list({r["empresa_id"] for r in rows})).execute().data or [])
    }
    item_data = (supabase_admin.table("inventario_items")
                 .select("id, nombre, tipo, numero_serie")
                 .in_("id", list({r["item_id"] for r in rows})).execute().data or [])
    item_map = {i["id"]: i for i in item_data}

    emp_data = (supabase_admin.table("empleados").select("id, nombre, apellido")
                .in_("id", list({r["empleado_id"] for r in rows})).execute().data or [])
    emp_map = {e["id"]: f"{e['nombre']} {e['apellido']}" for e in emp_data}

    return [
        AsignacionResponse.model_validate({
            **r,
            "empresa_nombre":    empresa_map.get(r["empresa_id"]),
            "item_nombre":       item_map.get(r["item_id"], {}).get("nombre"),
            "item_tipo":         item_map.get(r["item_id"], {}).get("tipo"),
            "item_numero_serie": item_map.get(r["item_id"], {}).get("numero_serie"),
            "empleado_nombre":   emp_map.get(r["empleado_id"]),
        })
        for r in rows
    ]


class InventarioAsignacionesRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_id: Optional[str] = None,
                 area_id: Optional[UUID] = None) -> List[AsignacionResponse]:
        """Asignaciones activas (fecha_devolucion IS NULL), filtradas por empresa, empleado y/o área.

        El área se resuelve a empleados en scope_filtros (un lookup batch, no uno por fila). La
        semántica de VIGENCIA la hereda del filtro de arriba: el listado ya muestra solo
        asignaciones sin devolver, así que "ítems del área X" son los que esa área tiene HOY en
        su poder — no hay que decidir nada sobre histórico.
        """
        if area_id:
            emp_ids = empleados_de_area(area_id, empresa_id)
            if not emp_ids:
                return []
        q = (supabase_admin.table(_T).select("*").is_("fecha_devolucion", "null")
             .order("fecha_asignacion", desc=True))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_id:
            q = q.eq("empleado_id", empleado_id)
        if area_id:
            q = q.in_("empleado_id", emp_ids)
        return _build(q.execute().data or [])

    def find_historial(self, item_id: str) -> List[AsignacionResponse]:
        """Historial completo de asignaciones de un ítem, más reciente primero."""
        rows = (supabase_admin.table(_T).select("*").eq("item_id", item_id)
                .order("fecha_asignacion", desc=True).execute().data or [])
        return _build(rows)

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[AsignacionResponse]:
        """Asignación por id. Si empresa_id se provee, valida pertenencia (None = consolidado)."""
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if res.data else None

    def save(self, item_id: str, empresa_id: str, empleado_id: str) -> AsignacionResponse:
        """Crea una asignación activa. El índice único parcial en DB previene duplicados."""
        res = supabase_admin.table(_T).insert({
            "item_id": item_id, "empresa_id": empresa_id, "empleado_id": empleado_id,
        }).execute()
        if not res.data:
            logger.error("Supabase insert vacío en inventario_asignaciones")
            raise AppError("Error al registrar la asignación", "DB_ERROR", 500)
        return _build([res.data[0]])[0]

    def devolver(self, id: str, estado_devolucion: str, notas: Optional[str]) -> Optional[AsignacionResponse]:
        """Cierra la asignación seteando fecha_devolucion y estado_devolucion."""
        patch: dict = {"fecha_devolucion": str(date.today()), "estado_devolucion": estado_devolucion}
        if notas:
            patch["notas"] = notas
        res = supabase_admin.table(_T).update(patch).eq("id", id).execute()
        return _build([res.data[0]])[0] if res.data else None
