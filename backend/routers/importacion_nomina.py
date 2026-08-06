"""Router de importación masiva de nómina via CSV. Rutas protegidas por AuthMiddleware.
Rate limit: franja "import", 10/hora compartida con el resto de los imports (ver
utils/rate_limit.py). Son operaciones humanas y deliberadas; nadie importa nómina 11 veces
por hora. `preview_nomina` no usa su `request: Request` —lo exige slowapi para poder decorar—;
`confirmar_nomina` sí lo usa, para sacar el `usuario_id` que va al evento de auditoría."""
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from schemas.importacion import (
    ImportacionNominaConfirmarRequest,
    ImportacionNominaConfirmarResponse,
    ImportacionNominaPreviewResponse,
)
from services.nomina_csv_service import parse_nomina_csv
from services.nomina_import_service import NominaImportService
from services._import_csv import decodificar
from utils.files import ALLOWED_TYPES_CSV, MAX_SIZE_CSV, validate_upload
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.IMPORTACION


def _service() -> NominaImportService:
    return NominaImportService()


@router.post("/nomina/preview", response_model=ImportacionNominaPreviewResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.shared_limit("10/hour", scope="import")
async def preview_nomina(
    request: Request,
    empresa_id: str = Form(...),
    file: UploadFile = File(...),
) -> ImportacionNominaPreviewResponse:
    """Parsea el CSV de nómina: resuelve DNI→empleado y marca duplicados (anio, mes)."""
    content = await file.read()
    validate_upload(content, file.content_type, ALLOWED_TYPES_CSV, MAX_SIZE_CSV, "archivo CSV de nómina")
    # El encoding lo resuelve el lector compartido (`services/_import_csv`), no el router:
    # tenerlo acá era lo que lo mantenía duplicado, con el bug de UTF-16 en las dos copias.
    text = decodificar(content)
    validas, errores = parse_nomina_csv(text, empresa_id)
    return ImportacionNominaPreviewResponse(filas_validas=validas, errores=errores)


@router.post("/nomina/confirmar", response_model=ImportacionNominaConfirmarResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.shared_limit("10/hour", scope="import")
async def confirmar_nomina(
    request: Request,
    body: ImportacionNominaConfirmarRequest,
    service: NominaImportService = Depends(_service),
) -> ImportacionNominaConfirmarResponse:
    """UPSERT en batch por (empleado_id, anio, mes) + UN evento de auditoría por lote.

    El `usuario_id` sale de `request.state.user` (mismo patrón que el import de nómina de
    empleados): sin él el evento no diría quién importó los sueldos."""
    usuario_id = request.state.user.get("id", "system")
    return service.confirmar(body, usuario_id)
