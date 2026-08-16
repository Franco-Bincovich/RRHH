"""Repositorio de inventario_asignaciones. Acceso a Supabase con supabase_admin.

El mapper y sus tres lookups por lote viven en `_inventario_asignacion_row.py`: este archivo
estaba en 100/100 cuando le tocaba sumar la paginacion, y el corte es el que ya tienen
`_empleado_row.py` y `_hora_row.py` — el mapper crece con cada columna que se muestra, el repo
con cada filtro, y juntos no entran.
"""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._inventario_asignacion_row import build as _build
from repositories._scope_filtros import empleados_de_area
from schemas.inventario import AsignacionResponse
from utils.errors import AppError
from utils.logger import logger

_T = "inventario_asignaciones"


class InventarioAsignacionesRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_id: Optional[str] = None,
                 area_id: Optional[UUID] = None, page: int = 1, page_size: int = 20,
                 ) -> Tuple[List[AsignacionResponse], int]:
        """Asignaciones activas (fecha_devolucion IS NULL), filtradas por empresa, empleado y/o área.

        El área se resuelve a empleados en scope_filtros (un lookup batch, no uno por fila). La
        semántica de VIGENCIA la hereda del filtro de arriba: el listado ya muestra solo
        asignaciones sin devolver, así que "ítems del área X" son los que esa área tiene HOY en
        su poder — no hay que decidir nada sobre histórico.
        """
        if area_id:
            emp_ids = empleados_de_area(area_id, empresa_id)
            if not emp_ids:
                return [], 0
        # `.order("id")` = desempate: `fecha_asignacion` es FECHA sin hora y un alta masiva entra
        # toda con la misma, así que los empates son la norma. ASC aunque la fecha vaya DESC —
        # es la forma de `idx_inv_asig_empresa_fecha` (migración 118), que además es PARCIAL
        # sobre `fecha_devolucion IS NULL`: exactamente el `.is_()` que esta query ya lleva.
        q = (supabase_admin.table(_T).select("*", count="exact").is_("fecha_devolucion", "null")
             .order("fecha_asignacion", desc=True).order("id"))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_id:
            q = q.eq("empleado_id", empleado_id)
        if area_id:
            q = q.in_("empleado_id", emp_ids)
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return _build(res.data or []), (res.count or 0)

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
