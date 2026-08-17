"""
Reportes de dotación: headcount (total + por área + altas/bajas del período) y rotación
(ingresos, bajas y tasa por motivo). Movidos verbatim desde reporte_generators.py.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid, periodo_str, rango_mes


def generate_headcount(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                       area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales de headcount: total activos, ingresos/bajas del período y distribución por área.
    Filtra por empresa_id y/o area_id si se proveen (empleados.area_id, directo).
    """
    ini, fin = rango_mes(mes, anio)
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    db = supabase_admin

    activos_q = db.table("empleados").select("area_id", count="exact").eq("estado", "activo")
    if eid:
        activos_q = activos_q.eq("empresa_id", eid)
    if aid:
        activos_q = activos_q.eq("area_id", aid)
    activos_res = activos_q.execute()
    total = activos_res.count or 0

    ingresos_q = db.table("empleados").select("id", count="exact").gte("fecha_ingreso", ini).lte("fecha_ingreso", fin)
    if eid:
        ingresos_q = ingresos_q.eq("empresa_id", eid)
    if aid:
        ingresos_q = ingresos_q.eq("area_id", aid)
    ingresos = ingresos_q.execute().count or 0

    # 🔴 POR `fecha_egreso`, NO POR `updated_at` — ver el mismo cambio en `dashboard_service`.
    # `updated_at` imputaba la baja al mes del trámite y la RE-IMPUTABA cada vez que alguien
    # tocaba el legajo, así que el número de un mes cerrado podía cambiar meses después.
    # `fecha_egreso` es nullable, y el rango `gte/lte` ya excluye los NULL (un NULL no matchea
    # `>= ini`), así que no hace falta un filtro extra: un empleado de baja sin fecha cargada
    # simplemente no cae en ningún período, que es la respuesta honesta.
    bajas_q = (db.table("empleados").select("id", count="exact").eq("estado", "baja")
               .gte("fecha_egreso", ini).lte("fecha_egreso", fin))
    if eid:
        bajas_q = bajas_q.eq("empresa_id", eid)
    if aid:
        bajas_q = bajas_q.eq("area_id", aid)
    bajas = bajas_q.execute().count or 0

    areas_q = db.table("areas").select("id, nombre").eq("activo", True)
    if eid:
        areas_q = areas_q.eq("empresa_id", eid)
    area_map: dict[str, str] = {a["id"]: a["nombre"] for a in (areas_q.execute().data or [])}

    conteo: dict[str, dict[str, int]] = {}
    for emp in (activos_res.data or []):
        aid = emp.get("area_id")
        if aid and aid in area_map:
            if aid not in conteo:
                conteo[aid] = {"nombre": area_map[aid], "total": 0}
            conteo[aid]["total"] += 1

    return {
        "titulo": f"Headcount — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_empleados": total,
        "ingresos_periodo": ingresos,
        "bajas_periodo": bajas,
        "variacion_neta": ingresos - bajas,
        "por_area": sorted(conteo.values(), key=lambda x: x["total"], reverse=True),
    }


def generate_rotacion(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                      area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales de rotación: ingresos, bajas y tasa del período.
    Filtra por empresa_id (y area_id: empleados.area_id directo en activos/ingresos; en bajas,
    offboarding_instancias no tiene area_id → join inner por empleado).
    """
    ini, fin = rango_mes(mes, anio)
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    db = supabase_admin

    activos_q = db.table("empleados").select("id", count="exact").eq("estado", "activo")
    if eid:
        activos_q = activos_q.eq("empresa_id", eid)
    if aid:
        activos_q = activos_q.eq("area_id", aid)
    empleados_activos = activos_q.execute().count or 0

    ingresos_q = db.table("empleados").select("id", count="exact").gte("fecha_ingreso", ini).lte("fecha_ingreso", fin)
    if eid:
        ingresos_q = ingresos_q.eq("empresa_id", eid)
    if aid:
        ingresos_q = ingresos_q.eq("area_id", aid)
    ingresos = ingresos_q.execute().count or 0

    # offboarding_instancias tiene DOS FKs a empleados → nombrar la FK o PostgREST da PGRST201.
    off_sel = ("motivo_egreso, empleados!offboarding_instancias_empleado_id_fkey!inner(area_id)"
               if aid else "motivo_egreso")
    off_q = (db.table("offboarding_instancias").select(off_sel)
             .gte("created_at", f"{ini}T00:00:00").lte("created_at", f"{fin}T23:59:59"))
    if eid:
        off_q = off_q.eq("empresa_id", eid)
    if aid:
        off_q = off_q.eq("empleados.area_id", aid)
    off_res = off_q.execute()
    bajas = len(off_res.data or [])

    motivos: dict[str, int] = {}
    for row in (off_res.data or []):
        m = row.get("motivo_egreso") or "otro"
        motivos[m] = motivos.get(m, 0) + 1

    base = empleados_activos + bajas
    tasa = round(bajas / base * 100, 2) if base > 0 else 0.0

    return {
        "titulo": f"Rotación — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "empleados_activos": empleados_activos,
        "ingresos_periodo": ingresos,
        "bajas_periodo": bajas,
        "tasa_rotacion_pct": tasa,
        "motivos_egreso": motivos,
    }
