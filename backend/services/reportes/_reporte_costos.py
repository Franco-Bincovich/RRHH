"""
Reporte de costos: nómina total y presupuesto con desvío, desagregado por área.
Movido verbatim desde reporte_generators.py.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid, periodo_str


def generate_costos(mes: int, anio: int, empresa_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales de costos: nómina total, presupuesto y desvío, desagregados por área.
    Filtra por empresa_id si se provee.
    """
    eid = _eid(empresa_id)
    db = supabase_admin

    nom_q = (db.table("costos_nomina")
             .select("total, empleados(areas!empleados_area_id_fkey(nombre))")
             .eq("mes", mes).eq("anio", anio))
    if eid:
        nom_q = nom_q.eq("empresa_id", eid)

    pre_q = (db.table("presupuesto_areas")
             .select("monto_presupuestado, areas(nombre)")
             .eq("mes", mes).eq("anio", anio).eq("tipo_costo", "nomina"))
    if eid:
        pre_q = pre_q.eq("empresa_id", eid)

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
