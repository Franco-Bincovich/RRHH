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
from repositories.oauth_state_repo import OAuthStateRepo
from schemas.integracion import IntegracionResponse
from services._google_scopes import SCOPES_PEDIDOS
from services._oauth_state import consumir, generar
from utils.errors import AppError
from utils.logger import logger

_PROVEEDOR = "google"

if settings.app_env == "development":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

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


def construir_url_autorizacion(user_id: str, state_repo=None) -> str:
    """
    Genera la URL de autorización de Google OAuth 2.0.

    Args:
        user_id: UUID del usuario que inicia el flujo. Queda persistido junto al state, y de
            ahí lo recupera el callback.
        state_repo: OAuthStateRepo; se instancia solo si no viene (inyectable para tests).

    Returns:
        URL de autorización de Google a la que redirigir al usuario.

    Raises:
        AppError: GOOGLE_NOT_CONFIGURED (503) si faltan las credenciales OAuth.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError("Google OAuth no está configurado", "GOOGLE_NOT_CONFIGURED", 503)

    state = generar(state_repo or OAuthStateRepo(), user_id, _PROVEEDOR)
    flow = Flow.from_client_config(_google_client_config(), scopes=SCOPES_PEDIDOS)
    flow.redirect_uri = settings.google_redirect_uri
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",
    )
    logger.info("Google OAuth iniciado", extra={"user_id": user_id})
    return auth_url


def procesar_callback(repo, state, code: str, state_repo=None) -> IntegracionResponse:
    """
    Procesa el callback de Google: verifica el state, intercambia el código por tokens y guarda.

    El `user_id` sale de la fila persistida al emitir el state, NO del query param: la cuenta
    de Google se conecta al usuario que inició este flujo y a ningún otro.

    Args:
        repo: IntegracionRepo donde persistir los tokens.
        state: Nonce recibido en el callback; se consume acá y no vuelve a servir.
        code: Código de autorización recibido de Google.
        state_repo: OAuthStateRepo; se instancia solo si no viene (inyectable para tests).

    Returns:
        IntegracionResponse con la cuenta conectada.

    Raises:
        AppError: OAUTH_STATE_INVALIDO (400) si el state no verifica.
        AppError: GOOGLE_CALLBACK_ERROR (400) si falla el intercambio de tokens.
        AppError: GOOGLE_USERINFO_ERROR (400) si no se puede obtener el email.
    """
    user_id = consumir(state_repo or OAuthStateRepo(), state, _PROVEEDOR)
    try:
        flow = Flow.from_client_config(
            _google_client_config(), scopes=SCOPES_PEDIDOS, state=state
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
        # Se guardan los scopes REALMENTE concedidos, no los pedidos: el usuario puede destildar
        # permisos en la pantalla de consentimiento. Sin esto, la única forma de saber si esta
        # cuenta puede enviar es intentarlo y comerse un 403 en medio de un envío.
        "scopes": list(credentials.scopes or []),
    }
    repo.save_google_tokens(user_id, tokens)
    logger.info("Google conectado", extra={"user_id": user_id, "email": email})
    return IntegracionResponse(tipo="google", email_cuenta=email, activo=True, connected=True)
