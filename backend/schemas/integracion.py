"""Schemas de integraciones por usuario."""
from typing import Optional

from pydantic import BaseModel


class IntegracionResponse(BaseModel):
    """Estado de una integración del usuario.

    `puede_enviar` y `es_remitente_sistema` solo tienen sentido para 'google'; en las demás van
    en False. Se declaran en el schema base igual, y no en uno aparte, para que el front consuma
    UNA sola forma: un tipo distinto por integración obligaría a ramificar en la UI para leer un
    booleano que ya se sabe False."""
    tipo: str
    email_cuenta: Optional[str] = None
    activo: bool
    connected: bool
    # ¿Esta cuenta tiene el scope `gmail.send`? False también en las conectadas ANTES de que el
    # scope existiera — son las que hay que avisar que reconecten. Ver `_google_scopes`.
    puede_enviar: bool = False
    # ¿Es la casilla desde la que salen los mails del sistema? Ver `integracion_remitente_repo`.
    es_remitente_sistema: bool = False


class ApiKeyUpdate(BaseModel):
    api_key: str
