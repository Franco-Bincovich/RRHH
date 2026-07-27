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
from services._dashboard_kpis import calcular_extras, calcular_headcount
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

        ingresos_q = (
            db.table("empleados").select("id", count="exact")
            .gte("fecha_ingreso", ini).lte("fecha_ingreso", fin)
        )
        if eid:
            ingresos_q = ingresos_q.eq("empresa_id", eid)
        ingresos_mes = ingresos_q.execute().count or 0

        bajas_q = (
            db.table("empleados").select("id", count="exact")
            .eq("estado", "baja")
            .gte("updated_at", f"{ini}T00:00:00").lte("updated_at", f"{fin}T23:59:59")
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
        """Alertas a partir de KPIs + una alerta por empleado activo sin email."""
        alertas: List[AlertaResponse] = []
        if kpis.vacantes_activas > 0:
            alertas.append(AlertaResponse(tipo="vacantes", nivel="info",
                mensaje=f"Hay {kpis.vacantes_activas} vacante(s) activa(s) en proceso de selección"))
        if kpis.onboardings_activos > 0:
            alertas.append(AlertaResponse(tipo="onboarding", nivel="info",
                mensaje=f"Hay {kpis.onboardings_activos} proceso(s) de onboarding en curso"))
        alertas.extend(self._alertas_sin_email(empresa_id))
        return alertas

    def _alertas_sin_email(self, empresa_id: Optional[UUID] = None) -> List[AlertaResponse]:
        """Una alerta (warning) por empleado no-baja con email null; se auto-resuelve al cargarlo."""
        q = (supabase_admin.table("empleados").select("id, nombre, apellido")
             .is_("email_corporativo", "null").neq("estado", "baja"))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [
            AlertaResponse(
                tipo="empleado_sin_email", nivel="warning", entidad_id=e["id"],
                mensaje=f"{e['nombre']} {e['apellido']} no tiene email cargado",
            )
            for e in (q.execute().data or [])
        ]
