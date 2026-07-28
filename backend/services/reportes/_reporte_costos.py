"""
Reportes del dominio costos:
- R5 generate_costos: masa salarial (nómina total) vs presupuesto, desvío por área.
- R8 generate_presupuesto: presupuesto vs ejecutado (ambos de presupuesto_areas), desvío y % ejecución.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import EMBED_AREA_DE_PRESUPUESTO as _AREA_PRE
from services.reportes._common import _eid, periodo_str


def generate_costos(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                    area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales de costos: nómina total, presupuesto y desvío, desagregados por área.
    Filtra por empresa_id; y por area_id (nómina: costos_nomina no tiene area_id → join inner por
    empleado; presupuesto_areas: area_id directo).
    """
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    db = supabase_admin

    # costos_nomina tiene DOS FKs a empleados (empleado_id_fkey + empleado_emp_fkey compuesta) →
    # hay que nombrar la FK explícita o PostgREST devuelve PGRST201 (embed ambiguo).
    nom_sel = ("total, empleados!costos_nomina_empleado_id_fkey!inner(area_id, areas!empleados_area_id_fkey(nombre))"
               if aid else "total, empleados!costos_nomina_empleado_id_fkey(areas!empleados_area_id_fkey(nombre))")
    nom_q = db.table("costos_nomina").select(nom_sel).eq("mes", mes).eq("anio", anio)
    if eid:
        nom_q = nom_q.eq("empresa_id", eid)
    if aid:
        nom_q = nom_q.eq("empleados.area_id", aid)

    pre_q = (db.table("presupuesto_areas")
             .select(f"monto_presupuestado, {_AREA_PRE}")
             .eq("mes", mes).eq("anio", anio).eq("tipo_costo", "nomina"))
    if eid:
        pre_q = pre_q.eq("empresa_id", eid)
    if aid:
        pre_q = pre_q.eq("area_id", aid)

    area_datos: dict[str, dict[str, float]] = {}
    total_nomina = 0.0
    for row in (nom_q.execute().data or []):
        area_nombre = ((row.get("empleados") or {}).get("areas") or {}).get("nombre") or "Sin área"
        total = float(row.get("total") or 0)
        total_nomina += total
        if area_nombre not in area_datos:
            area_datos[area_nombre] = {"nomina": 0.0, "presupuesto": 0.0}
        area_datos[area_nombre]["nomina"] += total

    total_presupuesto = 0.0
    for row in (pre_q.execute().data or []):
        area_nombre = (row.get("areas") or {}).get("nombre") or "Sin área"
        monto = float(row.get("monto_presupuestado") or 0)
        total_presupuesto += monto
        if area_nombre not in area_datos:
            area_datos[area_nombre] = {"nomina": 0.0, "presupuesto": 0.0}
        area_datos[area_nombre]["presupuesto"] = monto

    por_area = [
        {
            "area": nombre,
            "nomina": round(v["nomina"], 2),
            "presupuesto": round(v["presupuesto"], 2),
            "desvio": round(v["nomina"] - v["presupuesto"], 2),
        }
        for nombre, v in area_datos.items()
    ]

    return {
        "titulo": f"Costos — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_nomina": round(total_nomina, 2),
        "total_presupuesto": round(total_presupuesto, 2),
        "desvio": round(total_nomina - total_presupuesto, 2),
        "por_area": sorted(por_area, key=lambda x: x["nomina"], reverse=True),
    }


def _pct(ejecutado: float, presupuestado: float) -> float:
    return round(ejecutado / presupuestado * 100, 2) if presupuestado else 0.0


def generate_presupuesto(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                         area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Presupuesto vs real por área: monto_presupuestado, monto_ejecutado, desvío
    (ejecutado − presupuestado) y % ejecución. Filtra por empresa_id y/o area_id
    (presupuesto_areas.area_id, directo). Suma todos los tipo_costo del área."""
    eid, aid = _eid(empresa_id), _eid(area_id)
    q = (supabase_admin.table("presupuesto_areas")
         .select(f"monto_presupuestado, monto_ejecutado, {_AREA_PRE}")
         .eq("mes", mes).eq("anio", anio))
    if eid:
        q = q.eq("empresa_id", eid)
    if aid:
        q = q.eq("area_id", aid)

    acum: dict[str, dict[str, float]] = {}
    for row in (q.execute().data or []):
        nombre = (row.get("areas") or {}).get("nombre") or "Sin área"
        d = acum.setdefault(nombre, {"presupuestado": 0.0, "ejecutado": 0.0})
        d["presupuestado"] += float(row.get("monto_presupuestado") or 0)
        d["ejecutado"] += float(row.get("monto_ejecutado") or 0)

    por_area = [
        {
            "area": nombre,
            "presupuestado": round(v["presupuestado"], 2),
            "ejecutado": round(v["ejecutado"], 2),
            "desvio": round(v["ejecutado"] - v["presupuestado"], 2),
            "ejecucion_pct": _pct(v["ejecutado"], v["presupuestado"]),
        }
        for nombre, v in acum.items()
    ]
    total_pre = sum(v["presupuestado"] for v in acum.values())
    total_eje = sum(v["ejecutado"] for v in acum.values())

    return {
        "titulo": f"Presupuesto vs real — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_presupuestado": round(total_pre, 2),
        "total_ejecutado": round(total_eje, 2),
        "desvio": round(total_eje - total_pre, 2),
        "ejecucion_pct": _pct(total_eje, total_pre),
        "por_area": sorted(por_area, key=lambda x: x["presupuestado"], reverse=True),
    }
