"""
Generador del informe anual consolidado de RRHH.
Calcula métricas del año filtradas por empresa. Retorna estructura _sheets para
export multi-hoja Excel + datos planos como fallback para PDF.
Módulo auxiliar — invocado desde ReporteService. Las mediciones que no pasan por `_count_rango`
viven en `_reporte_anual_metricas.py` (este archivo estaba en 154 líneas contra el límite de 150).
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services._reporte_anual_metricas import actividad, headcount_por_area, movimientos


def _eid(empresa_id: Optional[UUID]) -> Optional[str]:
    return str(empresa_id) if empresa_id else None


def _count_rango(
    tabla: str,
    eid: Optional[str],
    ini: str,
    fin: str,
    campo_fecha: str = "created_at",
    **filtros: str,
) -> int:
    """Count con rango de fecha (date o timestamp) y filtros de igualdad opcionales."""
    q = supabase_admin.table(tabla).select("id", count="exact").gte(campo_fecha, ini).lte(campo_fecha, fin)
    for k, v in filtros.items():
        q = q.eq(k, v)
    if eid:
        q = q.eq("empresa_id", eid)
    return q.execute().count or 0


def generate_anual_consolidado(anio: int, empresa_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera métricas anuales consolidadas. Filtra por empresa_id (None = todas).
    ev_instancias.fecha_evaluacion es la fecha en que se finalizó (Optional[date]);
    instancias sin fecha_evaluacion (pre-campo o sin finalizar) no se contabilizan.

    Returns:
        Dict con '_sheets' (multi-hoja Excel) y campos planos (fallback PDF).

    Raises:
        Exception: propagada al caller para que ReporteService la envuelva en AppError.
    """
    eid = _eid(empresa_id)
    ini = f"{anio}-01-01"
    fin = f"{anio}-12-31"
    ini_ts = f"{ini}T00:00:00"
    fin_ts = f"{fin}T23:59:59"

    # ── 1. Movimientos de personal ─────────────────────────────────────────────
    ingresos, egresos = movimientos(eid, ini, fin, ini_ts, fin_ts)

    # ── 2. Headcount actual por área ───────────────────────────────────────────
    total_activos, headcount_list = headcount_por_area(eid)

    # ── 3. Procesos del año ────────────────────────────────────────────────────
    onb_iniciados = _count_rango("onboarding_instancias", eid, ini_ts, fin_ts)
    vacantes_del_ano = _count_rango("vacantes", eid, ini_ts, fin_ts)
    vacantes_cerradas = _count_rango("vacantes", eid, ini_ts, fin_ts, estado="cerrada")

    # ── 4. Actividad del año ───────────────────────────────────────────────────
    act = actividad(eid, ini, fin, ini_ts, fin_ts)
    solicitudes_vacaciones = act["solicitudes_vacaciones"]
    dias_vacaciones = act["dias_vacaciones"]
    cap_completadas = act["cap_completadas"]
    obj_terminados = act["obj_terminados"]
    ev_finalizadas = act["ev_finalizadas"]

    # ── Estructura de retorno ──────────────────────────────────────────────────
    return {
        "_sheets": {
            "Resumen": {
                "Año": anio,
                "Empleados activos": total_activos,
                "Ingresos del año": ingresos,
                "Egresos del año": egresos,
                "Variación neta": ingresos - egresos,
            },
            "Headcount por área": {"por_area": headcount_list},
            "Procesos del año": {
                "Onboardings iniciados": onb_iniciados,
                "Vacantes del año": vacantes_del_ano,
                "Vacantes cerradas": vacantes_cerradas,
            },
            "Actividad del año": {
                "Solicitudes de vacaciones": solicitudes_vacaciones,
                "Días de vacaciones tomados": dias_vacaciones,
                "Capacitaciones completadas": cap_completadas,
                "Evaluaciones finalizadas": ev_finalizadas,
                "Objetivos terminados": obj_terminados,
            },
        },
        "titulo": f"Informe Anual {anio}",
        "anio": anio,
        "total_empleados_activos": total_activos,
        "ingresos_del_ano": ingresos,
        "egresos_del_ano": egresos,
        "variacion_neta": ingresos - egresos,
        "onboardings_iniciados": onb_iniciados,
        "vacantes_del_ano": vacantes_del_ano,
        "vacantes_cerradas": vacantes_cerradas,
        "solicitudes_vacaciones": solicitudes_vacaciones,
        "dias_vacaciones_tomados": dias_vacaciones,
        "capacitaciones_completadas": cap_completadas,
        "evaluaciones_finalizadas": ev_finalizadas,
        "objetivos_terminados": obj_terminados,
        "headcount_por_area": headcount_list,
    }
