"""
La forma ÚNICA de una integración en la respuesta de la API.

Módulo propio y no una función dentro de `integracion_service.py` porque aquel llegó a 154
contra un límite de 150 al sumar `designar_remitente`. De fondo hay un motivo mejor que el
conteo: la construcción la comparten DOS métodos —`get_integraciones` (la lista de la pantalla)
y `designar_remitente` (la casilla recién marcada)—, y dos armados que se separen darían dos
verdades sobre la misma fila.
"""
from typing import Optional

from schemas.integracion import IntegracionResponse
from services._google_scopes import puede_enviar


def armar_response(tipo: str, row: Optional[dict]) -> IntegracionResponse:
    """Arma la respuesta de UNA integración a partir de su fila (o de su ausencia).

    Args:
        tipo: 'google' | 'anthropic' | 'zernio'.
        row: la fila de usuario_integraciones, o None si el usuario no la tiene.

    Returns:
        IntegracionResponse; desconectada si la fila no existe o no está activa.
    """
    if not (row and row.get("activo")):
        return IntegracionResponse(tipo=tipo, email_cuenta=None, activo=False, connected=False)
    return IntegracionResponse(
        tipo=tipo, email_cuenta=row.get("email_cuenta"), activo=True, connected=True,
        # Solo google puede enviar; en las otras dos el scope no significa nada.
        puede_enviar=tipo == "google" and puede_enviar(row.get("scopes")),
        es_remitente_sistema=bool(row.get("es_remitente_sistema")))
