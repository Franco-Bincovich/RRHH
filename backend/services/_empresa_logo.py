"""
Subida del logo de una empresa a Supabase Storage.

Extraído de `empresa_service.py`, que estaba en 147/150 y no admitía el endpoint de export.
Molde: `_usuario_alta.py`, `_vacante_candidatos.py` — función libre que recibe sus
colaboradores (repo y audit), sin estado propio.

POR QUÉ SALIÓ ESTE MÉTODO Y NO OTRO: es el único bloque del service que trae colaboradores
propios —el cliente de Storage y su payload de auditoría— y se los lleva con él. Los otros
cinco métodos son CRUD sobre el mismo repo: partirlos dejaría dos archivos hablando de lo
mismo. Acá el corte cae en una costura que ya existía.

⚠️ Este archivo vive en `services/`, así que su límite es 150 líneas, como cualquier service.
No hereda un límite más alto por ser un satélite.
"""
import uuid
from typing import Optional

from integrations import storage
from schemas.empresa import EmpresaResponse
from services._audit_payloads_rrhh import payload_logo_empresa
from utils.errors import AppError
from utils.logger import logger



def subir_logo(
    repo, audit, id: str, content: bytes, filename: str, content_type: str,
    usuario_id: Optional[str] = None,
) -> EmpresaResponse:
    """
    Sube el logo al bucket 'avatars' de Supabase Storage y actualiza logo_url.
    Genera una ruta única con UUID para evitar colisiones. Audita el cambio.

    Args:
        repo: EmpresaRepo (o doble de test).
        audit: AuditService (o doble de test).
        id: UUID de la empresa.
        content: Bytes del archivo de imagen.
        filename: Nombre original del archivo (para extraer extensión).
        content_type: MIME type del archivo (debe empezar con 'image/').
        usuario_id: quién hizo el cambio (trazabilidad del evento de auditoría).

    Returns:
        EmpresaResponse con logo_url actualizado.

    Raises:
        AppError: 404 si la empresa no existe, 400 si el archivo no es imagen.
    """
    # El find_by_id ya existía como guarda del 404; ahora además se CONSERVA, porque el
    # logo anterior solo se puede leer antes del UPDATE. Cero queries nuevas.
    previa = repo.find_by_id(id)
    if not previa:
        raise AppError("Empresa no encontrada", "EMPRESA_NOT_FOUND", 404)
    if not content_type.startswith("image/"):
        raise AppError("El archivo debe ser una imagen", "INVALID_FILE_TYPE", 400)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    path = f"logos/{id}/{uuid.uuid4()}.{ext}"
    storage.subir(storage.AVATARS, path, content, content_type)
    # AVATARS es el ÚNICO bucket público del sistema: por eso acá la URL es permanente y no firmada.
    logo_url = storage.url_publica(storage.AVATARS, path)
    empresa = repo.set_logo_url(id, logo_url)
    if not empresa:
        raise AppError("Error al actualizar el logo", "LOGO_UPDATE_ERROR", 500)
    audit.registrar(**payload_logo_empresa(empresa, previa.logo_url, usuario_id))
    logger.info("Logo de empresa actualizado", extra={"empresa_id": id, "path": path})
    return empresa
