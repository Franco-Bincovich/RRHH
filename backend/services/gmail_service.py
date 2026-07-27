"""Servicio de recepción de emails de candidatos via Gmail API."""
from datetime import datetime, timezone

import httpx

from config.settings import settings
from repositories.integracion_repo import IntegracionRepo
from repositories.vacante_repo import VacanteRepo
from schemas.vacante import CandidatoCreate, CandidatoResponse, EmailCandidatoResponse
from utils.errors import AppError
from utils.logger import logger

_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CV_KEYWORDS = ("cv", "curriculum", "postulacion", "candidatura", "postulación")


def _parse_from_header(from_header: str) -> tuple[str, str, str]:
    """Extrae (email, nombre, apellido) del header From de un email."""
    if "<" in from_header and ">" in from_header:
        name_part = from_header[: from_header.index("<")].strip().strip('"')
        email_part = from_header[from_header.index("<") + 1 : from_header.index(">")].strip()
    else:
        name_part = ""
        email_part = from_header.strip()
    parts = name_part.split(maxsplit=1)
    nombre = parts[0] if parts else email_part.split("@")[0]
    apellido = parts[1] if len(parts) > 1 else ""
    return email_part, nombre, apellido


def _is_cv_email(subject: str, snippet: str) -> bool:
    """Retorna True si el email parece una postulación por palabras clave."""
    return any(kw in f"{subject} {snippet}".lower() for kw in _CV_KEYWORDS)


class GmailService:
    def __init__(self) -> None:
        self._integracion_repo = IntegracionRepo()
        self._vacante_repo = VacanteRepo()

    def _get_access_token(self, user_id: str) -> str:
        """Obtiene el access_token válido de Google, renovándolo si expiró."""
        integracion = self._integracion_repo.get_by_user_and_tipo(user_id, "google")
        if not integracion or not integracion.get("access_token"):
            raise AppError("Gmail no configurado", "GMAIL_NOT_CONFIGURED", 400)
        expiry_str = integracion.get("token_expiry")
        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                if expiry <= datetime.now(timezone.utc):
                    refresh = integracion.get("refresh_token")
                    if not refresh:
                        raise AppError("Gmail no configurado", "GMAIL_NOT_CONFIGURED", 400)
                    try:
                        with httpx.Client(timeout=10.0) as client:
                            resp = client.post(_GOOGLE_TOKEN_URL, data={
                                "client_id": settings.google_client_id,
                                "client_secret": settings.google_client_secret,
                                "refresh_token": refresh,
                                "grant_type": "refresh_token",
                            })
                            resp.raise_for_status()
                            return resp.json()["access_token"]
                    except Exception as exc:
                        logger.error("Error al renovar token de Google", extra={"error": str(exc)})
                        raise AppError("No se pudo renovar el token de Google", "GMAIL_TOKEN_EXPIRED", 401)
            except (ValueError, TypeError):
                pass
        return integracion["access_token"]

    def get_emails_candidatos(self, vacante_id: str, user_id: str, empresa_id=None) -> list[EmailCandidatoResponse]:
        """
        Obtiene emails de Gmail filtrados por palabras clave de postulación.
        `empresa_id` acota a qué vacante se puede apuntar (None = consolidado).

        Raises:
            AppError: GMAIL_NOT_CONFIGURED (400) | VACANTE_NOT_FOUND (404) | GMAIL_ERROR (502).
        """
        if not self._vacante_repo.find_by_id(vacante_id, empresa_id):
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        access_token = self._get_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{_GMAIL_BASE}/messages", headers=headers, params={"maxResults": 50})
                resp.raise_for_status()
                messages = resp.json().get("messages", [])
                result: list[EmailCandidatoResponse] = []
                for msg_ref in messages[:20]:
                    msg_resp = client.get(
                        f"{_GMAIL_BASE}/messages/{msg_ref['id']}",
                        headers=headers,
                        params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                    )
                    if not msg_resp.is_success:
                        continue
                    msg = msg_resp.json()
                    hmap = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                    subject = hmap.get("Subject", "")
                    snippet = msg.get("snippet", "")
                    if not _is_cv_email(subject, snippet):
                        continue
                    result.append(EmailCandidatoResponse(
                        email_id=msg_ref["id"],
                        remitente=hmap.get("From", "Desconocido"),
                        asunto=subject or "(sin asunto)",
                        fecha=hmap.get("Date", ""),
                        cuerpo_preview=snippet[:200],
                    ))
        except AppError:
            raise
        except Exception as exc:
            logger.error("Error al consultar Gmail", extra={"error": str(exc), "user_id": user_id})
            raise AppError("Error al consultar Gmail", "GMAIL_ERROR", 502)
        logger.info("Emails candidatos obtenidos", extra={"vacante_id": vacante_id, "count": len(result)})
        return result

    def crear_candidato_desde_email(self, vacante_id: str, email_id: str, user_id: str, empresa_id=None) -> CandidatoResponse:
        """
        Extrae datos de un email de Gmail y crea un candidato en la vacante.
        `empresa_id` acota a qué vacante se puede apuntar (None = consolidado).

        Raises:
            AppError: GMAIL_NOT_CONFIGURED (400) | VACANTE_NOT_FOUND (404) | GMAIL_ERROR (502).
        """
        access_token = self._get_access_token(user_id)
        if not self._vacante_repo.find_by_id(vacante_id, empresa_id):
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{_GMAIL_BASE}/messages/{email_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
                )
                resp.raise_for_status()
                msg = resp.json()
        except AppError:
            raise
        except Exception as exc:
            logger.error("Error al obtener email de Gmail", extra={"error": str(exc), "email_id": email_id})
            raise AppError("Error al obtener el email de Gmail", "GMAIL_ERROR", 502)
        hmap = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        email_addr, nombre, apellido = _parse_from_header(hmap.get("From", ""))
        candidato = self._vacante_repo.save_candidato(
            vacante_id, CandidatoCreate(nombre=nombre, apellido=apellido, email=email_addr)
        )
        logger.info("Candidato creado desde email", extra={"vacante_id": vacante_id, "email": email_addr})
        return candidato
