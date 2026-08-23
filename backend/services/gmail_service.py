"""Conversación HTTP con la API de mensajes de Gmail. No sabe de vacantes ni de candidatos.

🔴 LEE DE LA CASILLA DEL SISTEMA, NO DE LA DEL USUARIO QUE APRETÓ EL BOTÓN.

Hasta el 8/8/2026 el token salía de `access_token_valido(IntegracionRepo(), user_id)`, o sea la
cuenta de Google de quien disparaba la acción. Pasaba desapercibido porque hay UNA sola
integración en la base y esa fila es a la vez la del usuario y la marcada `es_remitente_sistema`.
Con un segundo usuario conectado, el mismo botón habría devuelto listas distintas según quién lo
apretara, sin ningún error. Y un proceso automático no tiene `user_id`: la automatización era
imposible. El porqué completo está en `services/_casilla_sistema.py`.

## 🔴 QUÉ SE FUE DE ACÁ, Y POR QUÉ NO VOLVIÓ COMO "MODO VIEJO"

Este archivo tenía dos métodos de caso de uso —`get_emails_candidatos` (listar mails que
"parecían" postulaciones) y `crear_candidato_desde_email` (alta de a uno, a mano)— que la
ingesta por código REEMPLAZA. No conviven: el botón viejo listaba con `format=metadata` (que ni
siquiera trae los adjuntos) y decidía qué era una postulación con `_is_cv_email`, un filtro por
palabras clave que **descarta en silencio mails que sí traen el código**. Dejar los dos habría
significado dos criterios distintos sobre la misma casilla.

Lo que queda acá es lo que no dependía de ese caso de uso: hablar con la API. La orquestación
vive en `services/cv_ingesta_service.py`, el recorrido MIME y el decode en `_gmail_mensaje.py`,
y la descarga del adjunto en `_gmail_adjuntos.py`.
"""
from contextlib import contextmanager
from typing import List

import httpx

from repositories.integracion_remitente_repo import IntegracionRemitenteRepo
from services._casilla_sistema import token_de_lectura
from utils.errors import AppError
from utils.logger import logger

_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# 🔴 El filtro lo hace GMAIL, no nosotros. `has:attachment` descarta del lado del servidor todo
# lo que no puede traer un CV —notificaciones, respuestas, spam— así que los 50 que vuelven son
# 50 candidatos reales a procesar y no 50 mails de los cuales sobreviven 3. Es lo contrario del
# `_is_cv_email` que se sacó: aquel filtraba DESPUÉS de traer, por palabras clave, y descartaba
# mails con código adentro.
_QUERY = "has:attachment"
_MAX_MENSAJES = 50


class GmailService:
    def __init__(self) -> None:
        # La casilla del SISTEMA (sin filtro por usuario), no `IntegracionRepo` (scopeado por
        # user_id). Ver el encabezado del módulo.
        self._remitente_repo = IntegracionRemitenteRepo()

    def token(self) -> str:
        """Access token vigente de la casilla del sistema.

        Raises: GMAIL_SIN_CASILLA (400) | GMAIL_NOT_CONFIGURED (400) |
            GMAIL_TOKEN_EXPIRED (502) | GMAIL_RENOVACION_FALLIDA (502).
        """
        return token_de_lectura(self._remitente_repo)

    def ids_con_adjunto(self, client, access_token: str) -> List[str]:
        """Ids de los mensajes con adjunto de la casilla, más recientes primero.

        Devuelve SOLO ids: el contenido se pide por mensaje y con presupuesto de tiempo, así que
        traerlos todos acá sería trabajo que quizás no se llega a usar.
        """
        datos = self._get(client, access_token, f"{_GMAIL_BASE}/messages",
                          {"q": _QUERY, "maxResults": _MAX_MENSAJES})
        return [m["id"] for m in (datos.get("messages") or []) if m.get("id")]

    def mensaje_completo(self, client, access_token: str, message_id: str) -> dict:
        """UN mensaje con `format=full`.

        🔴 `full` y no `metadata`: `metadata` no trae `payload.parts[]`, o sea que con ese
        formato los adjuntos no existen. Es la primera de las cuatro piezas que faltaban para
        poder bajar un CV.
        """
        return self._get(client, access_token, f"{_GMAIL_BASE}/messages/{message_id}",
                         {"format": "full"})

    @staticmethod
    def _get(client, access_token: str, url: str, params: dict) -> dict:
        """GET contra Gmail, con el error traducido a un code propio.

        El cliente httpx se recibe abierto: una corrida son 1+N llamadas y abrir uno por request
        multiplicaría el handshake sin ganar nada.
        """
        try:
            resp = client.get(url, headers={"Authorization": f"Bearer {access_token}"},
                              params=params)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception as exc:  # noqa: BLE001 — se traduce, no se propaga crudo
            logger.error("Error al consultar Gmail", extra={"error": str(exc), "url": url})
            raise AppError("Error al consultar Gmail", "GMAIL_ERROR", 502)


def cliente_gmail() -> httpx.Client:
    """Un cliente httpx para toda la corrida. Timeout por request, no por lote."""
    return httpx.Client(timeout=15.0)


@contextmanager
def cliente_o(dado):
    """El cliente httpx de una operación: el que se pasó, o uno propio que se cierra solo.

    Lo comparten los dos casos de uso (ingesta automática y revisión manual) porque los dos son
    1+N llamadas: abrir un cliente por request multiplicaría el handshake sin ganar nada. El
    parámetro existe para inyectarlo en test.
    """
    propio = dado is None
    cliente = dado or cliente_gmail()
    try:
        yield cliente
    finally:
        if propio:
            cliente.close()
