"""Router del import de objetivos por Excel (preview + confirmar). Sección IMPORTACION.

Rate limit: franja "import", 10/hora compartida con el resto de los imports. `preview_objetivos`
no usa su `request: Request` —lo exige slowapi para poder decorar—; `confirmar_objetivos` sí lo
usa, para el `usuario_id` que va al evento de auditoría.

⚠️ El router NO lee el Excel: pasa los BYTES. El formato es una decisión del lector
(`services/_import_excel`), no de la capa HTTP — mismo criterio que los otros dos imports.
"""
from fastapi import APIRouter, Depends, File, Request, UploadFile

from schemas.importacion_objetivos import (
    ImportacionObjetivosConfirmarRequest,
    ImportacionObjetivosConfirmarResponse,
    ImportacionObjetivosPreviewResponse,
)
from services.objetivos_import_service import ObjetivosImportService
from utils.files import ALLOWED_TYPES_EXCEL, MAX_SIZE_CSV, validate_upload
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.IMPORTACION


def _service() -> ObjetivosImportService:
    return ObjetivosImportService()


@router.post("/objetivos/preview", response_model=ImportacionObjetivosPreviewResponse,
             dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.shared_limit("10/hour", scope="import")
async def preview_objetivos(
    request: Request,
    file: UploadFile = File(...),
    service: ObjetivosImportService = Depends(_service),
) -> ImportacionObjetivosPreviewResponse:
    """Lee el Excel, resuelve responsables contra `users` y clasifica cada fila. No persiste."""
    content = await file.read()
    validate_upload(content, file.content_type, ALLOWED_TYPES_EXCEL, MAX_SIZE_CSV,
                    "archivo Excel de objetivos")
    return service.preview(content)


@router.post("/objetivos/confirmar", response_model=ImportacionObjetivosConfirmarResponse,
             dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.shared_limit("10/hour", scope="import")
async def confirmar_objetivos(
    request: Request,
    body: ImportacionObjetivosConfirmarRequest,
    service: ObjetivosImportService = Depends(_service),
) -> ImportacionObjetivosConfirmarResponse:
    """Crea los objetivos revisados + UN evento de auditoría por lote.

    La empresa sale del BODY, no del header: confirmar un import es una ACCIÓN."""
    usuario_id = request.state.user.get("id", "system")
    return service.confirmar(body, usuario_id)
