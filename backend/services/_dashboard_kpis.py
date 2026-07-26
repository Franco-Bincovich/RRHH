"""
Cálculos del dashboard extraídos de dashboard_service (que estaba en su límite):
- calcular_headcount: headcount de activos por área (movido verbatim).
- calcular_extras: los 5 KPIs de Sesión 5 (23/26/27/28/30). Reusan los cálculos de los reportes
  (ausentismo/costos/distribución) — no duplican el "22" ni la lógica de distribución.
Todo filtra por empresa_id del contexto (header X-Empresa-Id: el dashboard es vista, respeta el sidebar).
"""
import calendar
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import DistribItem, HeadcountAreaResponse, KPIsExtraResponse, PersonaFecha
from services.reportes._reporte_ausentismo import _NOTA, _tasa
from services.reportes._reporte_costos import generate_costos
from services.reportes._reporte_distribucion import generate_distribucion


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


def _mes_anterior(anio: int, mes: int) -> Tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _ausencias_activas_hoy(hoy: date, eid: Optional[str]) -> int:
    """solicitudes_ausencia donde hoy ∈ [fecha_desde, fecha_hasta] (KPI 23, de acción)."""
    h = hoy.isoformat()
    q = (supabase_admin.table("solicitudes_ausencia").select("id", count="exact")
         .lte("fecha_desde", h).gte("fecha_hasta", h))
    if eid:
        q = q.eq("empresa_id", eid)
    return q.execute().count or 0


def _ausentismo_mes_pct(anio: int, mes: int, eid: Optional[str]) -> float:
    """% ausentismo del mes = días de ausencia / (22 * headcount) * 100. Reusa _tasa de R10 (KPI 26)."""
    ini = date(anio, mes, 1).isoformat()
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1]).isoformat()
    aus_q = (supabase_admin.table("solicitudes_ausencia").select("dias")
             .gte("fecha_desde", ini).lte("fecha_desde", fin))
    if eid:
        aus_q = aus_q.eq("empresa_id", eid)
    dias = sum(int(r.get("dias") or 0) for r in (aus_q.execute().data or []))
    hc_q = supabase_admin.table("empleados").select("id", count="exact").eq("estado", "activo")
    if eid:
        hc_q = hc_q.eq("empresa_id", eid)
    return _tasa(dias, hc_q.execute().count or 0)


def _cumple_aniversario(hoy: date, eid: Optional[str]) -> Tuple[List[PersonaFecha], List[PersonaFecha]]:
    """Cumpleaños (fecha_nacimiento) y aniversarios de ingreso (fecha_ingreso) del mes actual (KPI 30)."""
    q = (supabase_admin.table("empleados")
         .select("nombre, apellido, fecha_nacimiento, fecha_ingreso").eq("estado", "activo"))
    if eid:
        q = q.eq("empresa_id", eid)
    cumples: List[PersonaFecha] = []
    aniversarios: List[PersonaFecha] = []
    for e in (q.execute().data or []):
        nombre = f"{e.get('nombre', '')} {e.get('apellido', '')}".strip()
        for campo, destino in (("fecha_nacimiento", cumples), ("fecha_ingreso", aniversarios)):
            f = e.get(campo)
            if f and int(str(f)[5:7]) == hoy.month:
                destino.append(PersonaFecha(empleado=nombre, fecha=f"{str(f)[8:10]}/{str(f)[5:7]}"))
    return sorted(cumples, key=lambda p: p.fecha), sorted(aniversarios, key=lambda p: p.fecha)


def calcular_extras(hoy: date, empresa_id: Optional[UUID] = None) -> KPIsExtraResponse:
    """Los 5 KPIs nuevos (23/26/27/28/30), filtrando por empresa_id (header, respeta el sidebar)."""
    eid = str(empresa_id) if empresa_id else None
    anio, mes = hoy.year, hoy.month
    pa, pm = _mes_anterior(anio, mes)

    masa_actual = float(generate_costos(mes, anio, empresa_id)["total_nomina"])
    masa_anterior = float(generate_costos(pm, pa, empresa_id)["total_nomina"])
    variacion = round((masa_actual - masa_anterior) / masa_anterior * 100, 2) if masa_anterior else 0.0

    distrib = generate_distribucion(empresa_id)
    cumples, aniversarios = _cumple_aniversario(hoy, eid)

    return KPIsExtraResponse(
        ausencias_activas_hoy=_ausencias_activas_hoy(hoy, eid),
        ausentismo_mes_pct=_ausentismo_mes_pct(anio, mes, eid),
        ausentismo_nota=_NOTA,
        masa_salarial_actual=round(masa_actual, 2),
        masa_salarial_anterior=round(masa_anterior, 2),
        masa_salarial_variacion_pct=variacion,
        distribucion_seniority=[DistribItem(**d) for d in distrib["por_seniority"]],
        distribucion_modalidad=[DistribItem(**d) for d in distrib["por_modalidad"]],
        cumpleanos_mes=cumples,
        aniversarios_mes=aniversarios,
    )
