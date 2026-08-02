"""
El ÚNICO módulo del sistema que sabe de la API de Gmail.

Nadie fuera de `services/mailer/` lo importa, y hay un test estructural que lo verifica
(`tests/test_mailer_punto_unico.py`). Es lo que hace que cambiar de proveedor —a SES en la
migración a AWS, por ejemplo— sea agregar un archivo hermano y una entrada en `_PROVEEDORES`,
no un barrido por todo el repo.

## Lo que NO hace, a propósito
No loguea, no audita y no resuelve la casilla remitente. Todo eso vive en `engine.py`. Si viviera
acá, **el próximo proveedor nacería sin log** — que es exactamente lo que pasó con los exports
antes de `verificar_limite_export`, y por lo que hoy existe un barrido que lo verifica.

Recibe el token ya resuelto: la renovación vive en `services/_google_token.py`, compartida con la
lectura de candidatos.
"""
import base64
from email.message import EmailMessage
from typing import Optional

import httpx

from utils.errors import AppError
from utils.logger import logger

_GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def enviar(access_token: str, remitente: Optional[str], destinatario: str,
           asunto: str, cuerpo_html: str, cuerpo_texto: str) -> Optional[str]:
    """Manda un mail por la API de Gmail. Devuelve el id del mensaje, o None si Gmail no lo dio.

    Se manda MULTIPART (texto + HTML): el cliente elige. Sin la parte de texto, algunos filtros
    de spam penalizan el mensaje y los lectores en modo texto ven el markup crudo.

    Args:
        access_token: token vigente con el scope `gmail.send`.
        remitente: dirección de la casilla del sistema. None deja que Gmail use la de la cuenta.
        destinatario · asunto · cuerpo_html · cuerpo_texto: el mensaje.

    Raises:
        AppError: MAIL_SIN_PERMISO (403) si la cuenta no tiene el scope de envío.
        AppError: MAIL_ERROR_PROVEEDOR (502) para cualquier otro fallo de Gmail.
    """
    msg = EmailMessage()
    msg["To"] = destinatario
    msg["Subject"] = asunto
    if remitente:
        msg["From"] = remitente
    msg.set_content(cuerpo_texto)
    msg.add_alternative(cuerpo_html, subtype="html")
    crudo = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(_GMAIL_SEND,
                               headers={"Authorization": f"Bearer {access_token}"},
                               json={"raw": crudo})
    except Exception as exc:  # noqa: BLE001 — red caída, DNS, timeout
        logger.error("Error de red al enviar por Gmail", extra={"error": str(exc)})
        raise AppError("No se pudo enviar el mail", "MAIL_ERROR_PROVEEDOR", 502)

    if resp.status_code == 403:
        # 🔴 EL ERROR QUE MÁS VECES VA A PASAR EN LAS PRIMERAS SEMANAS, y merece su propio código.
        # No es un token vencido (eso sería 401): el token es válido y le falta el permiso de
        # envío, porque esa cuenta se conectó antes de que se pidiera `gmail.send`. Google no
        # amplía un grant retroactivamente. Sin este `if`, caería en el 502 genérico con el
        # mensaje "no se pudo enviar", que no dice qué hacer.
        logger.error("Gmail rechazó el envío por falta de scope", extra={"destinatario": destinatario})
        raise AppError(
            "La cuenta de Gmail conectada no tiene permiso para enviar. Reconectala desde "
            "Configuración para autorizar el envío.",
            "MAIL_SIN_PERMISO", 403)
    if not resp.is_success:
        logger.error("Gmail rechazó el envío", extra={"status": resp.status_code,
                                                      "cuerpo": resp.text[:200]})
        raise AppError("No se pudo enviar el mail", "MAIL_ERROR_PROVEEDOR", 502)
    return (resp.json() or {}).get("id")
