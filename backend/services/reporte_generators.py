"""
Dispatcher/re-export de los generadores de reportes. La lógica vive dividida por dominio en
services/reportes/_reporte_*.py (headcount/rotación/dotación, costos, selección, movimientos,
distribución). Este módulo se mantiene para no romper los imports existentes (reporte_service);
la reubicación es pura, sin cambios de lógica.
"""
from services.reportes._common import periodo_str, rango_mes
from services.reportes._reporte_ausentismo import generate_ausentismo
from services.reportes._reporte_auditoria import generate_auditoria
from services.reportes._reporte_capacitacion import generate_capacitacion
from services.reportes._reporte_costos import generate_costos, generate_presupuesto
from services.reportes._reporte_distribucion import generate_distribucion
from services.reportes._reporte_dotacion import generate_headcount, generate_rotacion
from services.reportes._reporte_movimientos import generate_altas_bajas
from services.reportes._reporte_seleccion import generate_onboarding, generate_vacantes
from services.reportes._reporte_saldos import generate_saldos_vacaciones
from services.reportes._reporte_vacaciones import generate_listado_vac_aus

__all__ = [
    "periodo_str", "rango_mes",
    "generate_headcount", "generate_rotacion", "generate_altas_bajas", "generate_distribucion",
    "generate_costos", "generate_vacantes", "generate_onboarding",
    "generate_saldos_vacaciones", "generate_ausentismo", "generate_listado_vac_aus",
    "generate_presupuesto", "generate_capacitacion", "generate_auditoria",
]
