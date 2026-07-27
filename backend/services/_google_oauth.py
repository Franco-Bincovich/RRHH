"""
Wrapper del flujo OAuth 2.0 de Google (extraído para mantener el service ≤150 líneas).

Funciones libres que reciben los colaboradores (el repo) — mismo molde que
_onboarding_iniciar.iniciar(repo, ...) y _ausencias_write. El service las delega en una
línea. La lógica se movió VERBATIM desde IntegracionService: scopes, construcción del flow,
intercambio de tokens, lectura del userinfo y persistencia son idénticos a antes.

Acá vive TODO lo específico de Google: es el único de los tres tipos de integración
(google · anthropic · zernio) que tiene flujo OAuth; los otros dos son guardar y borrar una
API key contra el repo, y se quedaron en el service.
"""
import os
from datetime import timezone

import httpx
from google_auth_oauthlib.flow import Flow

from config.settings import settings
from schemas.integracion import IntegracionResponse
from utils.errors import AppError
from utils.logger import logger

if settings.app_env == "development":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _google_client_config() -> dict:
    """Construye el dict de configuración OAuth requerido por google-auth-oauthlib."""
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def construir_url_autorizacion(user_id: str) -> str:
    """
    Genera la URL de autorización de Google OAuth 2.0.

    Args:
        user_id: UUID del usuario — se codifica en state para recuperarlo en el callback.

    Returns:
        URL de autorización de Google a la que redirigir al usuario.

    Raises:
        AppError: GOOGLE_NOT_CONFIGURED (503) si faltan las credenciales OAuth.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError("Google OAuth no está configurado", "GOOGLE_NOT_CONFIGURED", 503)

    flow = Flow.from_client_config(_google_client_config(), scopes=_GOOGLE_SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=user_id,
        prompt="consent",
    )
    logger.info("Google OAuth iniciado", extra={"user_id": user_id})
    return auth_url


def procesar_callback(repo, user_id: str, code: str) -> IntegracionResponse:
    """
    Procesa el callback de Google: intercambia el código por tokens y guarda en DB.

    Args:
        repo: IntegracionRepo donde persistir los tokens.
        user_id: UUID del usuario (extraído del state param del callback).
        code: Código de autorización recibido de Google.

    Returns:
        IntegracionResponse con la cuenta conectada.

    Raises:
        AppError: GOOGLE_CALLBACK_ERROR (400) si falla el intercambio de tokens.
        AppError: GOOGLE_USERINFO_ERROR (400) si no se puede obtener el email.
    """
    try:
        flow = Flow.from_client_config(
            _google_client_config(), scopes=_GOOGLE_SCOPES, state=user_id
        )
        flow.redirect_uri = settings.google_redirect_uri
        flow.fetch_token(code=code)
        credentials = flow.credentials
    except Exception as exc:
        logger.error("Error en callback de Google", extra={"error": str(exc)})
        raise AppError("Error al conectar con Google", "GOOGLE_CALLBACK_ERROR", 400)

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            resp.raise_for_status()
            email: str = resp.json().get("email", "")
    except Exception as exc:
        logger.error("Error obteniendo userinfo de Google", extra={"error": str(exc)})
        raise AppError("No se pudo obtener la cuenta de Google", "GOOGLE_USERINFO_ERROR", 400)

    expiry = credentials.expiry
    tokens = {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": expiry.replace(tzinfo=timezone.utc).isoformat() if expiry else None,
        "email_cuenta": email,
    }
    repo.save_google_tokens(user_id, tokens)
    logger.info("Google conectado", extra={"user_id": user_id, "email": email})
    return IntegracionResponse(tipo="google", email_cuenta=email, activo=True, connected=True)
