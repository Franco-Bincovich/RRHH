"""
Headcount de activos por área, para el dashboard.

Vive aparte de `_dashboard_kpis` —que quedó en su límite al cablear la base de días hábiles
configurable (migración 085)— y el corte no es arbitrario: es otra cosa. `_dashboard_kpis`
calcula los 5 KPIs escalares de la Sesión 5, que se devuelven juntos en KPIsExtraResponse con
fail-safe compartido; esto arma una LISTA por área y `dashboard_service` la pide por separado,
con su propio `_safe`.

Se movió verbatim: no cambia nada de su comportamiento.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import HeadcountAreaResponse


def calcular_headcount(empresa_id: Optional[UUID] = None) -> List[HeadcountAreaResponse]:
    """Headcount de activos agrupado por área, filtrado por empresa."""
    eid = str(empresa_id) if empresa_id else None

    areas_q = supabase_admin.table("areas").select("id, nombre").eq("activo", True)
    if eid:
        areas_q = areas_q.eq("empresa_id", eid)
    area_nombres: dict[str, str] = {a["id"]: a["nombre"] for a in areas_q.execute().data}

    emp_q = supabase_admin.table("empleados").select("area_id").eq("estado", "activo")
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    conteo: dict[str, int] = {}
    for emp in emp_q.execute().data:
        aid = emp.get("area_id")
        if aid and aid in area_nombres:
            conteo[aid] = conteo.get(aid, 0) + 1
    return sorted(
        [HeadcountAreaResponse(area_id=k, area=area_nombres[k], total=v) for k, v in conteo.items()],
        key=lambda x: x.total, reverse=True,
    )
