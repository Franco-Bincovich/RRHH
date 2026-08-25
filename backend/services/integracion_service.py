"""
Servicio de integraciones por usuario.
Gestiona el estado de las integraciones y el guardado de API keys (Anthropic, Zernio).

El flujo OAuth de Google vive en services/_google_oauth.py; acá quedan solo los dos métodos
que lo delegan en una línea. Por eso este módulo no importa nada de Google ni de httpx.
"""
from typing import Optional
from uuid import UUID

from repositories.integracion_remitente_repo import IntegracionRemitenteRepo
from repositories.integracion_repo import IntegracionRepo
from schemas.integracion import IntegracionResponse
from services._audit_payloads_integraciones import (
    payload_baja_integracion, payload_conexion_integracion, payload_remitente_sistema,
)
from services._google_oauth import construir_url_autorizacion, procesar_callback
from services._google_scopes import puede_enviar
from services._integracion_response import armar_response
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger


class IntegracionService:
    def __init__(self, repo: Optional[IntegracionRepo] = None,
                 remitente_repo: Optional[IntegracionRemitenteRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or IntegracionRepo()
        self._remitente_repo = remitente_repo or IntegracionRemitenteRepo()
        self._audit = audit or AuditService()

    def get_integraciones(self, user_id: str) -> list[IntegracionResponse]:
        """
        Retorna el estado de todas las integraciones soportadas para el usuario.

        Args:
            user_id: UUID del usuario autenticado.

        Returns:
            Lista de IntegracionResponse para 'google', 'anthropic' y 'zernio'.
        """
        existing = {r["tipo"]: r for r in self._repo.get_by_user(user_id)}
        return [armar_response(t, existing.get(t)) for t in ("google", "anthropic", "zernio")]

    def designar_remitente(self, user_id: str) -> IntegracionResponse:
        """
        Marca la integración de Google del usuario como la casilla del sistema.

        🔴 LAS DOS VALIDACIONES NO SON OPCIONALES, y su orden tampoco. `set_remitente` son DOS
        UPDATE sin transacción: DESMARCA la casilla vigente y recién después marca la nueva,
        filtrando por `user_id + tipo`. Si esa segunda sentencia matchea 0 filas —el usuario no
        tiene Google conectado— el sistema queda SIN remitente y la función devuelve None igual,
        sin forma de enterarse. Que la fila exista se verifica ACÁ porque el repo no lo reporta.

        El scope se exige por lo mismo un escalón más arriba: una casilla sin `gmail.send` se ve
        configurada y recién falla con un 403 de Google en el primer envío.

        Args:
            user_id: UUID del usuario autenticado, como string (es lo que entrega el router).

        Returns:
            IntegracionResponse de 'google', ya con es_remitente_sistema=True.

        Raises:
            AppError: INTEGRACION_NOT_FOUND (404) si no hay integración de Google activa.
            AppError: SCOPE_ENVIO_FALTANTE (409) si la cuenta no concedió `gmail.send`.
        """
        row = self._repo.get_by_user_and_tipo(user_id, "google")
        if not row or not row.get("activo"):
            raise AppError("Integración no encontrada", "INTEGRACION_NOT_FOUND", 404)
        if not puede_enviar(row.get("scopes")):
            raise AppError(
                "Esta cuenta de Google está conectada solo para lectura. Volvé a conectarla para "
                "conceder el permiso de envío antes de designarla como casilla del sistema.",
                "SCOPE_ENVIO_FALTANTE", 409)
        # El repo declara UUID y el router entrega str: el casteo va acá, no en el repo.
        self._remitente_repo.set_remitente(UUID(user_id))
        self._audit.registrar(**payload_remitente_sistema(
            {**row, "es_remitente_sistema": True}, user_id))
        logger.info("Casilla del sistema designada", extra={"user_id": user_id})
        return armar_response("google", {**row, "es_remitente_sistema": True})

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

        Args: user_id (UUID del usuario) · api_key (a almacenar; NO viaja al evento).

        Returns:
            IntegracionResponse confirmando que la key fue guardada.
        """
        self._repo.save_api_key(user_id, "anthropic", api_key)
        # 🔴 La KEY NO viaja al evento — ver el encabezado de _audit_payloads_integraciones.
        self._audit.registrar(**payload_conexion_integracion(
            {"tipo": "anthropic", "activo": True}, user_id))
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
        self._audit.registrar(**payload_conexion_integracion(
            {"tipo": "zernio", "activo": True}, user_id))
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

        🔴 EL PRIOR SE LEE ANTES DEL DELETE (la fila se va entera, con el `email_cuenta` y el
        flag de casilla del sistema) y el evento se emite DESPUÉS (uno previo afirmaría una baja
        que todavía puede fallar). Este evento es lo único que va a quedar.

        Raises:
            AppError: INTEGRACION_NOT_FOUND (404) si el usuario no tenía esa integración.
        """
        prior = self._repo.get_by_user_and_tipo(user_id, tipo)
        if not self._repo.delete(user_id, tipo):
            raise AppError("Integración no encontrada", "INTEGRACION_NOT_FOUND", 404)
        self._audit.registrar(**payload_baja_integracion(prior, tipo, user_id))
        logger.info("Integración desconectada", extra={"user_id": user_id, "tipo": tipo})
        return True
