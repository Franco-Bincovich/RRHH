"""
Servicio de CVs de candidatos: valida y sube el archivo al bucket privado 'cvs'.
Solo almacena; la descarga se resuelve por signed URL en otra pieza.
Patrón de subida reusado de adjunto_service (supabase_admin.storage.upload).
"""
import uuid as _uuid
from typing import Optional

from integrations.supabase_client import supabase_admin
from utils.errors import AppError
from utils.files import MAX_SIZE_CV, mensaje_supera_tamano
from utils.logger import logger

_BUCKET = "cvs"
_EXT = {"pdf", "doc", "docx"}
_MIME = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _ext(filename: str) -> str:
    """Extensión en minúsculas de un filename, o '' si no tiene."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


class CvService:
    def validar(self, content: bytes, filename: str, content_type: Optional[str]) -> None:
        """Valida formato (pdf/doc/docx) y tamaño del CV.

        Gate principal por extensión; el MIME se acepta si está en la lista o es genérico
        (octet-stream/None), porque algunos navegadores no lo informan bien para .doc.

        El límite y el texto del error salen de `utils/files.py`, no de acá: tener el número en
        dos lugares es cómo se desincronizan — este archivo decía 5 MB cuando el techo de la
        plataforma ya era 4,5. NO usa `validate_upload` entero porque conserva su propio
        code/status (`CV_TOO_LARGE`, 413) y cambiarlos sería alterar el contrato HTTP sin motivo.

        Raises: INVALID_CV_FORMAT (400), CV_TOO_LARGE (413).
        """
        mime_ok = content_type in _MIME or content_type in (None, "application/octet-stream")
        if _ext(filename) not in _EXT or not mime_ok:
            raise AppError("Formato de CV no permitido. Usá PDF o Word", "INVALID_CV_FORMAT", 400)
        if len(content) > MAX_SIZE_CV:
            raise AppError(mensaje_supera_tamano("CV", MAX_SIZE_CV), "CV_TOO_LARGE", 413)

    def subir(
        self, empresa_id: Optional[str], candidato_id: str, content: bytes,
        filename: str, content_type: Optional[str],
    ) -> str:
        """Sube el CV al bucket privado 'cvs' y devuelve el storage_path guardado en la fila.

        Path: cvs/{empresa_id}/{candidato_id}/{uuid}.{ext} (aísla por empresa, multiempresa).
        """
        emp = empresa_id or "sin_empresa"
        path = f"{emp}/{candidato_id}/{_uuid.uuid4()}.{_ext(filename) or 'bin'}"
        supabase_admin.storage.from_(_BUCKET).upload(
            path=path, file=content,
            file_options={"content-type": content_type or "application/octet-stream"},
        )
        logger.info("CV subido", extra={"candidato_id": candidato_id})
        return path
