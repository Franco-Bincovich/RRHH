"""
Helpers para resolución de empresa activa.
Usados por routers que necesitan filtrar o validar la empresa del request.
"""
from typing import Optional
from uuid import UUID

from starlette.requests import Request

from utils.errors import AppError


def get_empresa_id(request: Request) -> Optional[UUID]:
    """
    Retorna el empresa_id del request (seteado por AuthMiddleware).
    None significa 'todas las empresas' — válido para lecturas consolidadas.
    """
    raw = getattr(request.state, "empresa_id", None)
    return UUID(raw) if raw else None


def require_empresa_id(request: Request) -> UUID:
    """
    Retorna el empresa_id del request o lanza AppError 400 si es None.
    Usar en escrituras (POST/PUT/DELETE) donde empresa concreta es obligatoria.

    🔴 EL MENSAJE ES PARA ALGUIEN DE RRHH, NO PARA UN DEV. Decía *"empresa_id requerido para esta
    operación"* — jerga de backend que llega tal cual a la pantalla (el front muestra el `message`
    del error) y que no dice qué hacer. Quien lo lee no sabe que "empresa_id" es el selector del
    sidebar. El `code` sigue siendo el mismo, así que nada que dependa de él se entera.

    Mismo criterio que `MAIL_SIN_REMITENTE` ("Conectá una cuenta de Gmail en Configuración") y que
    el 422 del límite de export: el mensaje dice el paso siguiente, no el nombre del parámetro.
    """
    eid = get_empresa_id(request)
    if eid is None:
        raise AppError(
            "Elegí una empresa en el selector de arriba a la izquierda: esto se hace sobre una "
            "empresa concreta y no sobre la vista consolidada.",
            "EMPRESA_ID_REQUIRED", 400)
    return eid
