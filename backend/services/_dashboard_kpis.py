"""
calcular_extras: los 5 KPIs de Sesión 5 del dashboard (23/26/27/28/30). Reusan los cálculos de
los reportes (ausentismo/costos/distribución) — no duplican ni la base de días hábiles (que
desde la migración 085 sale de parametros_empresa, no de una constante) ni la lógica de
distribución.
Filtra por empresa_id del contexto (header X-Empresa-Id: el dashboard es vista, respeta el sidebar).

`calcular_headcount` vivía acá y se mudó a `_dashboard_headcount` al pasarse este archivo de
su límite: son dos cosas distintas (5 escalares con fail-safe compartido vs una lista por área
que dashboard_service pide por separado).
"""
import calendar
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import DistribItem, KPIsExtraResponse, PersonaFecha
from services.reportes._reporte_ausentismo import _tasa, base_dias_habiles, nota
from services.reportes._reporte_costos import generate_costos
from services.reportes._reporte_distribucion import generate_distribucion
from utils.logger import logger


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


def _ausentismo(anio: int, mes: int, eid: Optional[str],
                empresa_id: Optional[UUID]) -> Tuple[float, str]:
    """
    % ausentismo del mes = días de ausencia / (base * headcount) * 100, y su nota (KPI 26).
    Reusa _tasa y la base configurada de R10 — no duplica ni el cálculo ni el número.

    Devuelve el porcentaje y la nota JUNTOS a propósito: los dos dependen de la misma base, y
    calculados por separado podrían salir de dos lecturas distintas de la configuración y
    mostrar en pantalla una tasa dividida por 22 con un texto que dice 20.
    """
    base = base_dias_habiles(empresa_id)
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
    return _tasa(dias, hc_q.execute().count or 0, base), nota(base)


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


def _masa_salarial(anio: int, mes: int, empresa_id: Optional[UUID]) -> Tuple[float, float, float]:
    """Masa salarial del mes actual vs anterior + variación % (KPI 27). Reusa generate_costos (R5)."""
    pa, pm = _mes_anterior(anio, mes)
    actual = float(generate_costos(mes, anio, empresa_id)["total_nomina"])
    anterior = float(generate_costos(pm, pa, empresa_id)["total_nomina"])
    variacion = round((actual - anterior) / anterior * 100, 2) if anterior else 0.0
    return round(actual, 2), round(anterior, 2), variacion


def _distribucion(empresa_id: Optional[UUID]) -> Tuple[List[DistribItem], List[DistribItem]]:
    """Distribución por seniority/modalidad (KPI 28). Reusa generate_distribucion (R4)."""
    d = generate_distribucion(empresa_id)
    return ([DistribItem(**x) for x in d["por_seniority"]],
            [DistribItem(**x) for x in d["por_modalidad"]])


def calcular_extras(hoy: date, empresa_id: Optional[UUID] = None) -> KPIsExtraResponse:
    """Los 5 KPIs nuevos (23/26/27/28/30), filtrando por empresa_id (header, respeta el sidebar).
    Fail-safe POR KPI: si uno falla, queda en vacío/0 y se anota en `errores`; los demás salen igual."""
    eid = str(empresa_id) if empresa_id else None
    anio, mes = hoy.year, hoy.month
    errores: List[str] = []

    def _safe(fn, default, nombre):
        try:
            return fn()
        except Exception as exc:
            logger.error("kpi_dashboard_fallo", extra={"kpi": nombre, "error": str(exc)})
            errores.append(nombre)
            return default

    # La tasa y su nota salen del MISMO _safe: si la configuración no se puede leer, el KPI
    # entero queda en 0 y sin nota, y aparece en `errores`. Un fallback al viejo 22 mostraría
    # una tasa calculada con una base que quizás ya nadie configuró.
    aus_pct, aus_nota = _safe(lambda: _ausentismo(anio, mes, eid, empresa_id), (0.0, ""), "ausentismo_mes")
    masa = _safe(lambda: _masa_salarial(anio, mes, empresa_id), (0.0, 0.0, 0.0), "masa_salarial")
    seniority, modalidad = _safe(lambda: _distribucion(empresa_id), ([], []), "distribucion")
    cumples, aniversarios = _safe(lambda: _cumple_aniversario(hoy, eid), ([], []), "cumpleanos_aniversarios")

    return KPIsExtraResponse(
        ausencias_activas_hoy=_safe(lambda: _ausencias_activas_hoy(hoy, eid), 0, "ausencias_activas_hoy"),
        ausentismo_mes_pct=aus_pct,
        ausentismo_nota=aus_nota,
        masa_salarial_actual=masa[0],
        masa_salarial_anterior=masa[1],
        masa_salarial_variacion_pct=masa[2],
        distribucion_seniority=seniority,
        distribucion_modalidad=modalidad,
        cumpleanos_mes=cumples,
        aniversarios_mes=aniversarios,
        errores=errores,
    )
