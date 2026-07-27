"""
Servicio de integraciones por usuario.
Gestiona el estado de las integraciones y el guardado de API keys (Anthropic, Zernio).

El flujo OAuth de Google vive en services/_google_oauth.py; acá quedan solo los dos métodos
que lo delegan en una línea. Por eso este módulo no importa nada de Google ni de httpx.
"""
from typing import Optional

from repositories.integracion_repo import IntegracionRepo
from schemas.integracion import IntegracionResponse
from services._google_oauth import construir_url_autorizacion, procesar_callback
from utils.errors import AppError
from utils.logger import logger


class IntegracionService:
    def __init__(self, repo: Optional[IntegracionRepo] = None) -> None:
        self._repo = repo or IntegracionRepo()

    def get_integraciones(self, user_id: str) -> list[IntegracionResponse]:
        """
        Retorna el estado de todas las integraciones soportadas para el usuario.

        Args:
            user_id: UUID del usuario autenticado.

        Returns:
            Lista de IntegracionResponse para 'google' y 'anthropic'.
        """
        rows = self._repo.get_by_user(user_id)
        existing = {r["tipo"]: r for r in rows}

        result = []
        for tipo in ("google", "anthropic", "zernio"):
            row = existing.get(tipo)
            if row and row.get("activo"):
                result.append(IntegracionResponse(
                    tipo=tipo,
                    email_cuenta=row.get("email_cuenta"),
                    activo=True,
                    connected=True,
                ))
            else:
                result.append(IntegracionResponse(
                    tipo=tipo,
                    email_cuenta=None,
                    activo=False,
                    connected=False,
                ))
        return result

    def init_google_oauth(self, user_id: str) -> str:
        """URL de autorización de Google. Delegado a _google_oauth.construir_url_autorizacion."""
        return construir_url_autorizacion(user_id)

    def handle_google_callback(self, state: str, code: str) -> IntegracionResponse:
        """Callback de Google: state + tokens + userinfo + persistencia. Delegado a
        _google_oauth.procesar_callback."""
        return procesar_callback(self._repo, state, code)

    def save_anthropic_key(self, user_id: str, api_key: str) -> IntegracionResponse:
        """
        Guarda o actualiza la API key de Anthropic del usuario.

        Args:
            user_id: UUID del usuario.
            api_key: API key de Anthropic a almacenar.

        Returns:
            IntegracionResponse confirmando que la key fue guardada.
        """
        self._repo.save_api_key(user_id, "anthropic", api_key)
        logger.info("API key Anthropic guardada", extra={"user_id": user_id})
        return IntegracionResponse(tipo="anthropic", email_cuenta=None, activo=True, connected=True)

    def save_zernio_key(self, user_id: str, api_key: str) -> IntegracionResponse:
        """
        Guarda o actualiza la API key de Zernio del usuario.

        Args:
            user_id: UUID del usuario.
            api_key: API key de Zernio a almacenar.

        Returns:
            IntegracionResponse confirmando que la key fue guardada.
        """
        self._repo.save_api_key(user_id, "zernio", api_key)
        logger.info("API key Zernio guardada", extra={"user_id": user_id})
        return IntegracionResponse(tipo="zernio", email_cuenta=None, activo=True, connected=True)

    def disconnect(self, user_id: str, tipo: str) -> bool:
        """
        Desconecta una integración eliminando sus tokens/key de la base de datos.

        Args:
            user_id: UUID del usuario.
            tipo: Tipo de integración a desconectar ('google' o 'anthropic').

        Returns:
            True si la integración fue eliminada.

        Raises:
            AppError: INTEGRACION_NOT_FOUND (404) si el usuario no tenía esa integración.
        """
        deleted = self._repo.delete(user_id, tipo)
        if not deleted:
            raise AppError("Integración no encontrada", "INTEGRACION_NOT_FOUND", 404)
        logger.info("Integración desconectada", extra={"user_id": user_id, "tipo": tipo})
        return True
