"""
El certificado de una asignación de formación: subirlo y generar la URL firmada para bajarlo.

Salió de `asignacion_service.py`, que al sumarle los cuatro eventos de auditoría de la tanda del
25/8/2026 quedaba en 167 contra un tope de 150. Molde: `_areas_write.py` — funciones libres que
reciben el repo y el AuditService, sin estado ni `self`.

🔴 POR QUÉ SE CORTÓ POR ACÁ Y NO POR "LAS ESCRITURAS".
Es el único par de funciones del módulo que habla con STORAGE, y ese es un seam que ya existe en
el repo: `integrations/storage.py` es el punto de contacto ÚNICO con el proveedor y el día del
pase a S3 se toca ese archivo y nada más. Dejar juntas las dos funciones que lo usan —la que
sube y la que firma— es lo que hace evidente que comparten bucket y convención de ruta. Cortar
"por escrituras" habría separado `upload_certificado` de `get_certificado_signed_url`, que solo se
entienden leyéndolas juntas: la segunda depende de que la primera guarde un PATH y no una URL.

⚠️ LO QUE SE GUARDA EN `certificado_url` ES UNA RUTA, NO UNA URL. El bucket es privado, así que
una URL pública no existiría; la descarga se resuelve firmando en el momento. El nombre de la
columna miente y no se cambia acá (es la que hay en la base).

🔴 Y ESA RUTA VIVE SÓLO EN ESA FILA. No hay índice inverso desde el bucket: si la asignación se
borra, el objeto queda huérfano y no se puede volver a encontrar. Por eso el evento de baja de
`_audit_payloads_capacitaciones` lleva `certificado_url` — es lo único que permite rescatarlo.
"""
import uuid as _uuid
from typing import Optional
from uuid import UUID

from integrations import storage
from schemas.capacitacion import AsignacionResponse
from services._audit_payloads_capacitaciones import payload_update_asignacion_capacitacion
from utils.errors import AppError
from utils.logger import logger

_ALLOWED_TYPES = ("application/pdf", "image/jpeg", "image/png", "image/webp")
_NO_ENCONTRADA = ("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)


def subir(repo, audit, id: str, empresa_id: Optional[UUID], content: bytes, filename: str,
          content_type: str, usuario_id: Optional[str] = None) -> AsignacionResponse:
    """Sube el certificado al bucket privado 'documentos' y guarda su RUTA en `certificado_url`.

    Para descargarlo se usa `url_firmada` (abajo), no la ruta directa.

    Args:
        repo: AsignacionRepo (o doble).
        audit: AuditService (o doble).
        id: Asignación a la que se le adjunta el comprobante.
        empresa_id: Empresa del request — barrera sobre la asignación. None = consolidado.
        content · filename · content_type: el archivo tal como llegó.
        usuario_id: Operador, para la trazabilidad del evento.

    Raises:
        AppError: ASIGNACION_NOT_FOUND (404), INVALID_FILE_TYPE (400).
    """
    prior = repo.find_by_id(id, empresa_id)   # el "antes" del diff, y la barrera de empresa
    if not prior:
        raise AppError(*_NO_ENCONTRADA)
    if content_type not in _ALLOWED_TYPES:
        raise AppError("Solo se permiten PDF o imágenes (JPG, PNG, WEBP)", "INVALID_FILE_TYPE", 400)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    path = f"certificados/{id}/{_uuid.uuid4()}.{ext}"
    storage.subir(storage.DOCUMENTOS, path, content, content_type)
    updated = repo.update(id, empresa_id, {"certificado_url": path})
    # Evento PROPIO y no `update_asignacion_capacitacion`: adjuntar el comprobante de una
    # formación se filtra distinto que moverle el estado. Ver el payload.
    audit.registrar(**payload_update_asignacion_capacitacion(
        prior, updated, usuario_id, "carga_certificado_capacitacion"))
    logger.info("Certificado subido", extra={"asignacion_id": id, "path": path})
    return updated


def url_firmada(repo, id: str, empresa_id: Optional[UUID] = None) -> str:
    """URL firmada (3600 s) para descargar el certificado.

    Raises:
        AppError: ASIGNACION_NOT_FOUND (404), SIN_CERTIFICADO (404).
    """
    row = repo.find_by_id(id, empresa_id)
    if not row:
        raise AppError(*_NO_ENCONTRADA)
    if not row.certificado_url:
        raise AppError("Esta asignación no tiene certificado", "SIN_CERTIFICADO", 404)
    return storage.url_firmada(storage.DOCUMENTOS, row.certificado_url)
