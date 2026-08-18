"""
Servicio del Dashboard Ejecutivo. Agrega KPIs, headcount y alertas en tiempo real.
Flujo: router → service → DB
Todas las queries filtran por empresa_id del contexto (None = consolidado de todas).
"""
import calendar
from datetime import date
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import AlertaResponse, DashboardResponse, KPIResponse
from services._dashboard_alertas import generar_alertas
from services._dashboard_headcount import calcular_headcount
from services._dashboard_kpis import calcular_extras
from utils.estados_empleado import ESTADO_PREINGRESO
from utils.logger import logger

_KPIS_VACIOS = KPIResponse(empleados_activos=0, ingresos_mes=0, bajas_mes=0,
                           costo_nomina=0.0, onboardings_activos=0, vacantes_activas=0)


def _safe(fn, default, seccion: str):
    """Ejecuta fn; si falla, loguea y devuelve default (fail-safe por sección, no fail-closed global)."""
    try:
        return fn()
    except Exception as exc:
        logger.error("dashboard_seccion_fallo", extra={"seccion": seccion, "error": str(exc)})
        return default


class DashboardService:
    def get_dashboard(self, empresa_id: Optional[UUID] = None) -> DashboardResponse:
        """
        Calcula el resumen ejecutivo del período actual: KPIs, headcount, alertas y KPIs extra.
        Filtra por empresa_id si se provee; None retorna datos consolidados de todas.

        Fail-safe por sección: si una sección falla, queda en vacío/0 y las demás se devuelven
        igual (nunca un 500 global). Los KPIs extra además fallan de forma independiente entre sí
        (ver KPIsExtraResponse.errores).
        """
        hoy = date.today()
        kpis = _safe(lambda: self._calcular_kpis(hoy, empresa_id), _KPIS_VACIOS, "kpis")
        headcount = _safe(lambda: calcular_headcount(empresa_id), [], "headcount")
        alertas = _safe(lambda: self._generar_alertas(kpis, empresa_id), [], "alertas")
        extra = calcular_extras(hoy, empresa_id)  # fail-safe por KPI internamente
        return DashboardResponse(kpis=kpis, headcount_por_area=headcount, alertas=alertas, kpis_extra=extra)

    def _calcular_kpis(self, hoy: date, empresa_id: Optional[UUID] = None) -> KPIResponse:
        """Calcula los 6 KPIs principales filtrando por empresa_id."""
        anio, mes = hoy.year, hoy.month
        ini = date(anio, mes, 1).isoformat()
        fin = date(anio, mes, calendar.monthrange(anio, mes)[1]).isoformat()
        db = supabase_admin
        eid = str(empresa_id) if empresa_id else None

        def _count(table: str, **filters) -> int:
            """Count con filtro automático de empresa."""
            q = db.table(table).select("id", count="exact")
            for k, v in filters.items():
                q = q.eq(k, v)
            if eid:
                q = q.eq("empresa_id", eid)
            return q.execute().count or 0

        empleados_activos = _count("empleados", estado="activo")

        # 🔴 EXCLUYE PREINGRESOS. Este contador cuenta por FECHA y no miraba `estado` en absoluto,
        # así que ningún valor del CHECK lo protegía: un preingreso de este mes se contaba como un
        # alta de este mes SIN HABER ENTRADO, y se volvía a contar en el mes nuevo si alguien le
        # corregía la fecha prevista de ingreso.
        # Va por COMPLEMENTO (`neq` al preingreso) y NO enumerando los estados en plantilla:
        # alguien que entró en marzo y renunció en julio sigue siendo un alta de marzo, así que
        # `baja` TIENE que quedar del lado que cuenta. El razonamiento largo está en
        # `utils/estados_empleado.py`; enumerar acá reintroduciría el bug de los números de un mes
        # cerrado que cambian meses después, que es el mismo que ya se corrigió al dejar de contar
        # por `updated_at`.
        ingresos_q = (
            db.table("empleados").select("id", count="exact")
            .neq("estado", ESTADO_PREINGRESO)
            .gte("fecha_ingreso", ini).lte("fecha_ingreso", fin)
        )
        if eid:
            ingresos_q = ingresos_q.eq("empresa_id", eid)
        ingresos_mes = ingresos_q.execute().count or 0

        # 🔴 POR `fecha_egreso`, NO POR `updated_at`. Con `updated_at` la baja se imputaba al mes
        # del TRÁMITE, no al del egreso — y peor: `updated_at` lo mueve CUALQUIER edición del
        # legajo, así que corregirle el teléfono a alguien en noviembre lo sacaba del conteo de
        # marzo y lo metía en el de noviembre. Un contador que se mueve solo.
        # Es el mismo criterio que ya usaba `_reporte_movimientos` (bajas por `fecha_egreso`), y
        # que los dos coincidan para el mismo mes es el objetivo explícito del cambio.
        bajas_q = (
            db.table("empleados").select("id", count="exact")
            .eq("estado", "baja")
            .gte("fecha_egreso", ini).lte("fecha_egreso", fin)
        )
        if eid:
            bajas_q = bajas_q.eq("empresa_id", eid)
        bajas_mes = bajas_q.execute().count or 0

        costos_q = db.table("costos_nomina").select("salario_bruto").eq("anio", anio).eq("mes", mes)
        if eid:
            costos_q = costos_q.eq("empresa_id", eid)
        costos_res = costos_q.execute()
        costo_nomina = float(sum(r.get("salario_bruto") or 0 for r in costos_res.data))

        onboardings_activos = _count("onboarding_instancias", estado="en_progreso")

        vacantes_q = db.table("vacantes").select("id", count="exact").neq("estado", "cerrada")
        if eid:
            vacantes_q = vacantes_q.eq("empresa_id", eid)
        vacantes_activas = vacantes_q.execute().count or 0

        return KPIResponse(
            empleados_activos=empleados_activos,
            ingresos_mes=ingresos_mes,
            bajas_mes=bajas_mes,
            costo_nomina=costo_nomina,
            onboardings_activos=onboardings_activos,
            vacantes_activas=vacantes_activas,
        )

    def _generar_alertas(self, kpis: KPIResponse, empresa_id: Optional[UUID] = None) -> List[AlertaResponse]:
        """Alertas del dashboard. Delegado a _dashboard_alertas.generar_alertas.
        Se conserva como método —y no se llama a la función suelta desde get_dashboard— porque
        ESTA es la costura: `_safe` la envuelve para el fail-safe por sección, y los tests la
        parchean por instancia. Mover la implementación no debe mover el punto de corte."""
        return generar_alertas(kpis, empresa_id)
