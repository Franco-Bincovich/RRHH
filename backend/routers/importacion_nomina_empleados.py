"""Router del import de nómina de empleados (CSV 27 columnas, ';', latin1). Crea empleados
+ empresas + áreas desde el archivo. Protegido por AuthMiddleware + permiso IMPORTACION."""
from fastapi import APIRouter, Depends, File, Request, UploadFile

from schemas.importacion_nomina_empleados import ImportacionNominaEmpleadosResult
from services.nomina_empleados_service import NominaEmpleadosImportService
from utils.files import ALLOWED_TYPES_CSV, MAX_SIZE_CSV, validate_upload
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()


@router.post(
    "/nomina-empleados",
    response_model=ImportacionNominaEmpleadosResult,
    dependencies=[Depends(require_permission(Seccion.IMPORTACION, Accion.WRITE))],
)
@limiter.shared_limit("10/hour", scope="import")  # franja "import", ver utils/rate_limit.py
async def importar_nomina_empleados(
    request: Request,
    file: UploadFile = File(...),
) -> ImportacionNominaEmpleadosResult:
    """Sube el CSV de nómina, crea empleados/empresas/áreas y devuelve el reporte fila por fila.
    Decodifica latin1 (fallback si no es UTF-8). El nombre del archivo se audita."""
    content = await file.read()
    validate_upload(content, file.content_type, ALLOWED_TYPES_CSV, MAX_SIZE_CSV, "archivo CSV de nómina")
    try:
        texto = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = content.decode("latin-1")
    usuario_id = request.state.user.get("id", "system")
    service = NominaEmpleadosImportService(usuario_id)
    return service.importar(texto, file.filename or "nomina.csv")
