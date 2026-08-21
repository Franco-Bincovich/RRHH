"""
`calcular_extras`: el ARMADOR de los KPIs escalares del dashboard, con fail-safe por KPI. Reusan
los cálculos de los reportes (ausentismo/costos/distribución) — no duplican ni la base de días
hábiles (que desde la migración 085 sale de parametros_empresa, no de una constante) ni la
lógica de distribución.
Filtra por empresa_id del contexto (header X-Empresa-Id: el dashboard es vista, respeta el sidebar).

🔴 ESTE ARCHIVO ES LA COSTURA, NO LA CALCULADORA. Cada vez que se pasó de su límite se sacó de
acá un CÁLCULO, nunca la costura: `calcular_headcount` se fue a `_dashboard_headcount`, y en la
tanda del 21/8/2026 —la de los KPIs que faltaban de `docs/SISTEMA-DE-DISENO.md` §6— se fueron
`_masa_salarial` a `_dashboard_masa_salarial` (con el porqué de cuál de las dos sobrevivía) y
nacieron `_dashboard_operacion` y `_dashboard_antiguedad`. Lo que queda acá es lo que solo esta
función puede hacer: envolver cada KPI en su `_safe` y armar UNA respuesta.
Corolario para el próximo KPI: se escribe en un módulo propio y se cablea acá con una línea.
"""
import calendar
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import DistribItem, KPIsExtraResponse, PersonaFecha
from services._dashboard_antiguedad import antiguedad
from services._dashboard_atencion_calculadas import contar_ingresos_proximos
from services._dashboard_masa_salarial import masa_salarial
from services._dashboard_operacion import recategorizaciones_mes, rotacion_12m
from services.reportes._reporte_ausentismo import _tasa, base_dias_habiles, nota
from services.reportes._reporte_distribucion import generate_distribucion
from utils.logger import logger


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
    # 🔴 El default del fallo es `(0.0, 0.0, None)`, con `None` en la variación y no `0.0`: si el
    # KPI no se pudo calcular, mucho menos se sabe cuánto varió. Un `0.0` acá volvería a afirmar
    # "no cambió" — el mismo bug que la tanda del 21/8 vino a cerrar, reintroducido por el default.
    masa = _safe(lambda: masa_salarial(anio, mes, empresa_id), (0.0, 0.0, None), "masa_salarial")
    rotacion = _safe(lambda: rotacion_12m(hoy, empresa_id), (0, 0.0), "rotacion_12m")
    antig = _safe(lambda: antiguedad(hoy, empresa_id), (0.0, 0.0), "antiguedad")
    seniority, modalidad = _safe(lambda: _distribucion(empresa_id), ([], []), "distribucion")
    cumples, aniversarios = _safe(lambda: _cumple_aniversario(hoy, eid), ([], []), "cumpleanos_aniversarios")

    return KPIsExtraResponse(
        ausencias_activas_hoy=_safe(lambda: _ausencias_activas_hoy(hoy, eid), 0, "ausencias_activas_hoy"),
        ausentismo_mes_pct=aus_pct,
        ausentismo_nota=aus_nota,
        masa_salarial_actual=masa[0],
        masa_salarial_anterior=masa[1],
        masa_salarial_variacion_pct=masa[2],
        ingresos_proximos_30=_safe(lambda: contar_ingresos_proximos(empresa_id, hoy), 0,
                                   "ingresos_proximos_30"),
        recategorizaciones_mes=_safe(lambda: recategorizaciones_mes(anio, mes, empresa_id), 0,
                                     "recategorizaciones_mes"),
        rotacion_12m_bajas=rotacion[0],
        rotacion_12m_pct=rotacion[1],
        antiguedad_promedio_anios=antig[0],
        antiguedad_mediana_anios=antig[1],
        distribucion_seniority=seniority,
        distribucion_modalidad=modalidad,
        cumpleanos_mes=cumples,
        aniversarios_mes=aniversarios,
        errores=errores,
    )
