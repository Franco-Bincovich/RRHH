"""
Cálculo del saldo anual de vacaciones (extraído de vacaciones_service para dejar
margen de líneas al sumar el chequeo de ownership en las escrituras).

Función pura sobre el repo — misma regla de negocio de siempre, solo relocalizada.
"""
from datetime import date

from schemas.vacaciones import SaldoVacacionesResponse
from services._vacaciones_utils import derive_estado
from utils.errors import AppError


def calcular_saldo(repo, empleado_id, empresa_id=None) -> SaldoVacacionesResponse:
    """Saldo anual de vacaciones pagas de un empleado. Solo tipo='vacaciones' no cancelado
    descuenta: gozados (estado 'tomada') + pedidos ('planificada'); disponibles = asignados −
    ambos. Raises EMPLEADO_NOT_FOUND (404) si el empleado no existe.

    `empresa_id` acota AMBAS consultas (None = consolidado). El caller ya validó el empleado con
    ensure_empleado_visible; propagarlo igual mantiene el filtro donde se leen los datos, para que
    la consulta no dependa de que el gate de arriba exista."""
    asignados = repo.find_dias_asignados(str(empleado_id), empresa_id)
    if asignados is None:
        raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
    today = date.today()
    gozados = pedidos = 0
    for s in repo.find_vacaciones_empleado(str(empleado_id), empresa_id):
        s = derive_estado(s, today)
        if s.estado == "tomada":
            gozados += s.dias
        elif s.estado == "planificada":
            pedidos += s.dias
    return SaldoVacacionesResponse(
        empleado_id=str(empleado_id), asignados=asignados,
        gozados=gozados, pedidos=pedidos, disponibles=asignados - gozados - pedidos,
    )
