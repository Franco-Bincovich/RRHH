"""
Servicio de publicación en LinkedIn via Zernio.
Flujo: publicar_en_vacante → get API key → build content → POST Zernio → save result
"""
from datetime import datetime, timezone

import httpx

from repositories.integracion_repo import IntegracionRepo
from repositories.vacante_repo import VacanteRepo
from schemas.vacante import PublicarLinkedinResponse
from utils.errors import AppError
from utils.logger import logger

_ZERNIO_URL = "https://zernio.com/api/v1/posts"


def _build_post_content(vacante_dict: dict, email_contacto: str) -> str:
    """Construye el texto del post de LinkedIn según el formato requerido por Zernio."""
    titulo = vacante_dict.get("titulo", "")
    area = vacante_dict.get("area_nombre") or ""
    descripcion = vacante_dict.get("descripcion") or ""
    requisitos = vacante_dict.get("requisitos") or ""
    lineas = [ln.strip() for ln in requisitos.splitlines() if ln.strip()]
    req_lista = "\n".join(f"• {ln}" for ln in lineas) if lineas else "• A definir"
    hashtag_area = area.replace(" ", "")
    return (
        f"🚀 {titulo} | {area}\n\n"
        f"{descripcion}\n\n"
        f"Requisitos:\n{req_lista}\n\n"
        f"📩 Interesado? Enviá tu CV a {email_contacto}\n\n"
        f"#hiring #trabajo #{hashtag_area}"
    )


class ZernioService:
    def __init__(self) -> None:
        self._integracion_repo = IntegracionRepo()
        self._vacante_repo = VacanteRepo()

    def publicar_en_vacante(
        self, vacante_id: str, email_contacto: str, user_id: str, empresa_id=None
    ) -> PublicarLinkedinResponse:
        """
        Publica la vacante en LinkedIn via Zernio y guarda el resultado en la DB.

        Args:
            vacante_id: UUID de la vacante a publicar.
            email_contacto: Email de contacto para incluir en el post.
            user_id: UUID del usuario que realiza la operación.

        Returns:
            PublicarLinkedinResponse con post_id, url y timestamp.

        Raises:
            AppError: ZERNIO_NOT_CONFIGURED (400) si no hay API key configurada.
            AppError: VACANTE_NOT_FOUND (404) si la vacante no existe o es de otra empresa
                (`empresa_id` acota a qué vacante se puede apuntar; None = consolidado).
            AppError: ZERNIO_ERROR (502) si Zernio devuelve un error HTTP.
            AppError: ZERNIO_CONNECTION_ERROR (502) si falla la conexión con Zernio.
        """
        integracion = self._integracion_repo.get_by_user_and_tipo(user_id, "zernio")
        if not integracion or not integracion.get("api_key"):
            raise AppError("Zernio no configurado", "ZERNIO_NOT_CONFIGURED", 400)

        vacante = self._vacante_repo.find_by_id(vacante_id, empresa_id)
        if not vacante:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)

        contenido = _build_post_content(vacante.model_dump(), email_contacto)

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    _ZERNIO_URL,
                    headers={"Authorization": f"Bearer {integracion['api_key']}"},
                    json={"content": contenido},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Zernio devolvió error HTTP",
                extra={"status": exc.response.status_code, "vacante_id": vacante_id},
            )
            raise AppError("Error al publicar en LinkedIn via Zernio", "ZERNIO_ERROR", 502)
        except Exception as exc:
            logger.error(
                "Error de conexión con Zernio",
                extra={"error": str(exc), "vacante_id": vacante_id},
            )
            raise AppError("Error al conectar con Zernio", "ZERNIO_CONNECTION_ERROR", 502)

        post_id = str(data.get("id", ""))
        url = str(data.get("url", ""))
        self._vacante_repo.save_linkedin_data(vacante_id, post_id, url, email_contacto)
        logger.info(
            "Vacante publicada en LinkedIn via Zernio",
            extra={"vacante_id": vacante_id, "post_id": post_id},
        )
        return PublicarLinkedinResponse(
            post_id=post_id,
            url=url,
            publicado_en=datetime.now(timezone.utc),
        )
