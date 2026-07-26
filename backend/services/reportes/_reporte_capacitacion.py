"""
R16 — Capacitación por área. Desde empleado_capacitacion, JOIN a empleados (área) y a
capacitaciones (duracion_horas). Por área: asignaciones, completadas/en_curso/pendientes
(por estado) y horas totales asignadas. El área vive en empleados → filtro por JOIN inner.
Período por fecha_asignacion (no fecha_completado: las pendientes/en_curso la tienen NULL y
filtrar por completado las excluiría, rompiendo el conteo por estado). Con tabla vacía → filas
vacías y totales en 0 (empty state coherente).
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid, periodo_str, rango_mes


def generate_capacitacion(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                          area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Capacitación por área (asignaciones, estados y horas). Filtra por empresa_id y/o area_id
    (join inner por empleado). Período por fecha_asignacion."""
    ini, fin = rango_mes(mes, anio)
    eid, aid = _eid(empresa_id), _eid(area_id)
    emb = ("empleados!inner(areas!empleados_area_id_fkey(nombre))" if aid
           else "empleados(areas!empleados_area_id_fkey(nombre))")
    q = (supabase_admin.table("empleado_capacitacion")
         .select(f"estado, capacitaciones(duracion_horas), {emb}")
         .gte("fecha_asignacion", ini).lte("fecha_asignacion", fin))
    if eid:
        q = q.eq("empresa_id", eid)
    if aid:
        q = q.eq("empleados.area_id", aid)

    acum: dict[str, dict[str, Any]] = {}
    for row in (q.execute().data or []):
        nombre = ((row.get("empleados") or {}).get("areas") or {}).get("nombre") or "Sin área"
        d = acum.setdefault(nombre, {"asignaciones": 0, "completadas": 0, "en_curso": 0,
                                     "pendientes": 0, "horas_totales": 0.0})
        d["asignaciones"] += 1
        estado = row.get("estado")
        if estado == "completado":
            d["completadas"] += 1
        elif estado == "en_curso":
            d["en_curso"] += 1
        else:
            d["pendientes"] += 1
        d["horas_totales"] += float((row.get("capacitaciones") or {}).get("duracion_horas") or 0)

    por_area = [
        {"area": nombre, **{k: (round(v[k], 2) if k == "horas_totales" else v[k]) for k in
                            ("asignaciones", "completadas", "en_curso", "pendientes", "horas_totales")}}
        for nombre, v in acum.items()
    ]

    return {
        "titulo": f"Capacitación por área — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_asignaciones": sum(v["asignaciones"] for v in acum.values()),
        "por_area": sorted(por_area, key=lambda x: x["asignaciones"], reverse=True),
    }
