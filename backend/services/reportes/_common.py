"""
Helpers compartidos por los generadores de reportes (services/reportes/_reporte_*.py):
formato de período, rango de fechas del mes y normalización de empresa_id. Sin lógica de dominio.
"""
import calendar
from datetime import date
from typing import Optional
from uuid import UUID

_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def periodo_str(mes: int, anio: int) -> str:
    return f"{_MESES_ES[mes]} {anio}"


def rango_mes(mes: int, anio: int) -> tuple[str, str]:
    """Retorna (inicio, fin) ISO del mes como strings."""
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, 1).isoformat(), date(anio, mes, ultimo_dia).isoformat()


def _eid(empresa_id: Optional[UUID]) -> Optional[str]:
    return str(empresa_id) if empresa_id else None
