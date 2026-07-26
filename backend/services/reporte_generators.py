"""
Dispatcher/re-export de los generadores de reportes. La lógica vive dividida por dominio en
services/reportes/_reporte_*.py (headcount/rotación/dotación, costos, selección, movimientos,
distribución). Este módulo se mantiene para no romper los imports existentes (reporte_service);
la reubicación es pura, sin cambios de lógica.
"""
from services.reportes._common import periodo_str, rango_mes
from services.reportes._reporte_costos import generate_costos
from services.reportes._reporte_distribucion import generate_distribucion
from services.reportes._reporte_dotacion import generate_headcount, generate_rotacion
from services.reportes._reporte_movimientos import generate_altas_bajas
from services.reportes._reporte_seleccion import generate_onboarding, generate_vacantes

__all__ = [
    "periodo_str", "rango_mes",
    "generate_headcount", "generate_rotacion", "generate_altas_bajas", "generate_distribucion",
    "generate_costos", "generate_vacantes", "generate_onboarding",
]
