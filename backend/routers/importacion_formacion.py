"""Router del import de Formación por Excel (preview + confirmar). Sección IMPORTACION.

Molde: `importacion_objetivos.py` — misma franja de rate limit ("import", 10/hora compartida) y
mismo reparto: el router NO lee el Excel, pasa los BYTES al lector compartido.

🔴 Vive en archivo propio y no en `capacitaciones.py` porque ese router está en 78/80, y porque
la sección es otra: importar está gateado por IMPORTACION (solo admin_rrhh), no por
CAPACITACIONES.

⚠️ La empresa viaja como Form en el preview y en el body del confirmar, NUNCA por header:
importar es una ACCIÓN (Vista vs Acción). El Excel no menciona sociedades — decisión 1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from schemas.importacion_formacion import (
    ImportacionFormacionConfirmarRequest,
    ImportacionFormacionConfirmarResponse,
    ImportacionFormacionPreviewResponse,
)
from services.formacion_import_service import FormacionImportService
from utils.files import ALLOWED_TYPES_EXCEL, MAX_SIZE_CSV, validate_upload
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.IMPORTACION


def _service() -> FormacionImportService:
    return FormacionImportService()


@router.post("/formacion/preview", response_model=ImportacionFormacionPreviewResponse,
             dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.shared_limit("10/hour", scope="import")
async def preview_formacion(
    request: Request,
    empresa_id: UUID = Form(...),
    file: UploadFile = File(...),
    service: FormacionImportService = Depends(_service),
) -> ImportacionFormacionPreviewResponse:
    """Lee el Excel, matchea colaboradores contra el padrón de la empresa y clasifica. No persiste."""
    content = await file.read()
    validate_upload(content, file.content_type, ALLOWED_TYPES_EXCEL, MAX_SIZE_CSV,
                    "archivo Excel de formación")
    return service.preview(content, empresa_id)


@router.post("/formacion/confirmar", response_model=ImportacionFormacionConfirmarResponse,
             dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.shared_limit("10/hour", scope="import")
async def confirmar_formacion(
    request: Request,
    body: ImportacionFormacionConfirmarRequest,
    service: FormacionImportService = Depends(_service),
) -> ImportacionFormacionConfirmarResponse:
    """Escribe el lote revisado (catálogo + asignaciones) + UN evento de auditoría."""
    usuario_id = request.state.user.get("id", "system")
    return service.confirmar(body, usuario_id)
