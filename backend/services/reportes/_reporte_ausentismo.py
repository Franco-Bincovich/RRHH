"""
R10 — Ausentismo por área. Por cada área, días totales y días injustificados del período, más
sus tasas % sobre una base de 22 días hábiles/mes/empleado (headcount del área como denominador).
El área vive en empleados → filtro de área por JOIN inner por empleado. El parámetro `vista`
(total | injustificado | ambos, default ambos) decide qué columnas de métrica salen.
La nota del cálculo va como escalar en `datos` → sale visible en el "Resumen" de PDF/Excel.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import EMBED_AREA_DE_EMPLEADO as _AREA
from services.reportes._common import _eid, periodo_str, rango_mes

_BASE_DIAS_HABILES = 22
_NOTA = "Las tasas se calculan sobre una base de 22 días hábiles por mes por empleado."


def _tasa(dias: int, headcount: int) -> float:
    base = _BASE_DIAS_HABILES * headcount
    return round(dias / base * 100, 2) if base > 0 else 0.0


def generate_ausentismo(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                        area_id: Optional[UUID] = None, vista: str = "ambos") -> Dict[str, Any]:
    """Ausentismo por área (días totales/injustificados + tasas). Filtra por empresa_id y/o
    area_id (join inner por empleado en las ausencias; directo en el headcount del denominador)."""
    ini, fin = rango_mes(mes, anio)
    eid, aid = _eid(empresa_id), _eid(area_id)
    db = supabase_admin

    # Denominador: headcount de activos por área.
    # `areas` se alcanza nombrando la FK: hay DOS relaciones entre empleados y areas
    # (empleados.area_id y areas.responsable_id), y sin el hint PostgREST devuelve PGRST201.
    emp_q = db.table("empleados").select(f"area_id, {_AREA}").eq("estado", "activo")
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    if aid:
        emp_q = emp_q.eq("area_id", aid)
    headcount: dict[str, int] = {}
    for e in (emp_q.execute().data or []):
        nombre = (e.get("areas") or {}).get("nombre") or "Sin área"
        headcount[nombre] = headcount.get(nombre, 0) + 1

    aus_sel = (f"dias, justificada, empleados!inner({_AREA})" if aid
               else f"dias, justificada, empleados({_AREA})")
    aus_q = (db.table("solicitudes_ausencia").select(aus_sel)
             .gte("fecha_desde", ini).lte("fecha_desde", fin))
    if eid:
        aus_q = aus_q.eq("empresa_id", eid)
    if aid:
        aus_q = aus_q.eq("empleados.area_id", aid)
    totales: dict[str, int] = {}
    injust: dict[str, int] = {}
    for a in (aus_q.execute().data or []):
        nombre = ((a.get("empleados") or {}).get("areas") or {}).get("nombre") or "Sin área"
        d = int(a.get("dias") or 0)
        totales[nombre] = totales.get(nombre, 0) + d
        if not a.get("justificada"):
            injust[nombre] = injust.get(nombre, 0) + d

    ver_total = vista in ("total", "ambos")
    ver_injust = vista in ("injustificado", "ambos")
    filas = []
    for nombre in sorted(set(headcount) | set(totales)):
        hc = headcount.get(nombre, 0)
        fila: Dict[str, Any] = {"area": nombre, "headcount": hc}
        if ver_total:
            fila["dias_totales"] = totales.get(nombre, 0)
            fila["tasa_total_pct"] = _tasa(totales.get(nombre, 0), hc)
        if ver_injust:
            fila["dias_injustificados"] = injust.get(nombre, 0)
            fila["tasa_injustificada_pct"] = _tasa(injust.get(nombre, 0), hc)
        filas.append(fila)

    orden = "dias_totales" if ver_total else "dias_injustificados"
    return {
        "titulo": f"Ausentismo por área — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "nota": _NOTA,
        "ausentismo": sorted(filas, key=lambda x: x.get(orden, 0), reverse=True),
    }
