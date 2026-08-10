"""
Middleware de autenticación JWT.
Verifica la firma del token de Supabase contra el JWKS público del proyecto (ES256)
y expone el user_id, rol y empresa_id en request.state para los handlers.
empresa_id proviene del header X-Empresa-Id: queda None si viene "todas", ausente, malformado
o apuntando a una empresa que no existe (ver middleware/_empresa_header.py). None = vista consolidada.
"""
import re
from typing import Optional

import jwt
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.settings import settings
from middleware._empresa_header import resolver_empresa_id
from utils._sesion_inactividad import sesion_expirada
from utils.logger import logger
from utils.usuario_estado import estado_usuario, registrar_actividad

# Las rutas SIN auth viven en `_rutas_publicas.py` — ese archivo es el inventario completo
# de la superficie sin autenticación del sistema, y explica por qué la quinta está gateada
# por flag. Se re-exporta `PUBLIC_ROUTES` porque hay tests que lo importan de acá.
from middleware._rutas_publicas import (  # noqa: F401
    PUBLIC_ROUTES, RUTA_IDENTIFICACION, rutas_publicas_activas,
)

_ASSESSMENT_API_RE = re.compile(r"^/api/assessment/evaluacion/[^/]+(/submit)?$")

# JWKS del proyecto: publica las claves públicas vigentes y las rota solo.
# Se instancia UNA vez a nivel módulo. El __init__ de PyJWKClient no hace red (verificado):
# el primer fetch ocurre en el primer get_signing_key_from_jwt, así que no penaliza el
# cold start. Con cache_jwk_set/lifespan=300 (defaults) el set se refetchea como mucho
# cada 5 min por proceso, nunca por request. timeout=5: fallar rápido si el JWKS no
# responde, en vez de colgar el request los 30s del default.
_JWKS_URL = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
_jwks_client = jwt.PyJWKClient(_JWKS_URL, timeout=5)

# Solo ES256: el JWKS publica únicamente claves asimétricas. La Legacy HS256 es simétrica
# y por definición no se publica, así que los tokens viejos HS256 no son verificables —
# expiran solos y sus dueños vuelven a loguearse. Decisión tomada, no reabrir.
_ALGORITHMS = ["ES256"]


def _is_public(path: str) -> bool:
    # `rutas_publicas_activas()` ya resuelve el gateo por flag de la ruta de identificación.
    if path in rutas_publicas_activas():
        return True
    return settings.assessment_enabled and bool(_ASSESSMENT_API_RE.match(path))


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def _verificar_token(token: str, path: str) -> Optional[str]:
    """Verifica firma y expiración del JWT contra el JWKS; retorna el claim `sub`.

    No exige audiencia (verify_aud=False): Supabase emite aud="authenticated", pero
    fijarla acá dejaría a todos afuera si alguna vez cambia. La firma ES256 ya ata el
    token a este proyecto. La expiración SÍ se verifica: es el default de PyJWT al
    verificar firma y no se desactiva.

    Fail-closed: cualquier fallo (firma inválida, token expirado, kid ausente del JWKS,
    JWKS inaccesible) retorna None y el caller responde 401 genérico. El motivo real se
    loguea solo del lado servidor — nunca se expone al cliente, para no dar señal sobre
    por qué falló.

    Args:
        token: JWT crudo extraído del header Authorization.
        path: Ruta del request, solo para trazabilidad en el log.

    Returns:
        El `sub` (UUID del usuario) si el token es válido; None si no lo es.
    """
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=_ALGORITHMS,
            options={"verify_aud": False},
        )
        return payload.get("sub")
    except Exception as exc:
        logger.warning(
            "Token JWT rechazado",
            extra={"path": path, "motivo": type(exc).__name__},
        )
        return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        if _is_public(request.url.path):
            return await call_next(request)

        token = _extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": True, "message": "No autorizado", "code": "MISSING_TOKEN"},
            )

        user_id = _verificar_token(token, request.url.path)

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"error": True, "message": "No autorizado", "code": "INVALID_TOKEN"},
            )

        # El rol y el activo salen de un caché por proceso (TTL 60s), no de una query por
        # request. Es fail-closed: si no se puede resolver, viene rol=None y permisos.py niega
        # todo — exactamente lo que hacía el try/except que vivía acá. Ver utils/usuario_estado.
        estado = estado_usuario(user_id)

        # Un usuario dado de baja tiene un JWT que sigue siendo válido —la firma y el exp no
        # saben nada de esto— así que el corte tiene que estar acá. Se chequea ANTES de armar
        # request.state: no hay endpoint, gateado o no, que deba correr para alguien de baja.
        # `resuelto` evita que un blip de base se le presente al usuario como "te dieron de
        # baja": en ese caso rol=None y decide permisos.py, igual que antes de este cambio.
        if estado.resuelto and not estado.activo:
            logger.warning("Request de usuario inactivo", extra={"user_id": user_id, "path": request.url.path})
            return JSONResponse(
                status_code=403,
                content={"error": True, "message": "Tu usuario fue desactivado", "code": "USUARIO_INACTIVO"},
            )

        # 🔴 El chequeo va ANTES de registrar la actividad, y el orden es todo: al revés, este
        # mismo request sellaría `ultimo_acceso` y la sesión no vencería NUNCA.
        if sesion_expirada(estado):
            logger.info("Sesión vencida por inactividad", extra={"user_id": user_id})
            return JSONResponse(
                status_code=401,
                content={"error": True, "message": "Tu sesión venció por inactividad",
                         "code": "SESION_EXPIRADA"},
            )
        registrar_actividad(user_id)

        request.state.user = {"id": user_id, "rol": estado.rol}

        request.state.empresa_id = resolver_empresa_id(
            request.headers.get("X-Empresa-Id", "").strip(), request.url.path
        )

        return await call_next(request)
