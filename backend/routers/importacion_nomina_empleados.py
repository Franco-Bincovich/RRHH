"""Router del import de nómina de empleados (CSV 27 columnas, ';', latin1). Crea empleados
+ empresas + áreas desde el archivo. Protegido por AuthMiddleware + permiso IMPORTACION.

Los dos endpoints de superiores pendientes viven acá y no en un router propio porque son la
COLA del mismo flujo: el import deja pendientes, estos los listan y los reintentan. Misma
sección de permisos (IMPORTACION), mismo dueño funcional."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile

from schemas.importacion_nomina_empleados import ImportacionNominaEmpleadosResult
from schemas.superiores_pendientes import (
    ResolucionPendientesResult, SuperioresPendientesListResponse,
)
from services.nomina_empleados_service import NominaEmpleadosImportService
from services.superiores_pendientes_service import SuperioresPendientesService
from utils.empresa import get_empresa_id
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


@router.get(
    "/superiores-pendientes",
    response_model=SuperioresPendientesListResponse,
    dependencies=[Depends(require_permission(Seccion.IMPORTACION, Accion.READ))],
)
async def listar_superiores_pendientes(request: Request) -> SuperioresPendientesListResponse:
    """Cuántos superiores quedaron sin resolver y de qué empleados. Respeta el selector de
    empresa del sidebar (es una VISTA: filtra lo que se mira, no gobierna la acción)."""
    return SuperioresPendientesService().listar(get_empresa_id(request))


@router.post(
    "/superiores-pendientes/resolver",
    response_model=ResolucionPendientesResult,
    dependencies=[Depends(require_permission(Seccion.IMPORTACION, Accion.WRITE))],
)
@limiter.shared_limit("10/hour", scope="import")  # misma franja que el import: escribe lo mismo
async def resolver_superiores_pendientes(request: Request) -> ResolucionPendientesResult:
    """Reintenta los pendientes contra el estado ACTUAL de empleados y limpia los que resuelve.

    ⚠️ El `empresa_id` acota QUÉ pendientes se reintentan, NO dónde se busca al superior: un
    superior puede ser de otra empresa del grupo. Ver `SuperioresPendientesService.resolver`."""
    empresa_id: Optional[UUID] = get_empresa_id(request)
    return SuperioresPendientesService().resolver(empresa_id)
