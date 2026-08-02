"""Router de importación masiva de nómina via CSV. Rutas protegidas por AuthMiddleware.
Rate limit: franja "import", 10/hora compartida con el resto de los imports (ver
utils/rate_limit.py). Son operaciones humanas y deliberadas; nadie importa nómina 11 veces
por hora. `request: Request` no lo usan los handlers, lo exige slowapi para poder decorar."""
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from repositories.nomina_import_repo import NominaImportRepo
from schemas.importacion import (
    ImportacionNominaConfirmarRequest,
    ImportacionNominaConfirmarResponse,
    ImportacionNominaPreviewResponse,
)
from services.nomina_csv_service import parse_nomina_csv
from services._import_csv import decodificar
from utils.files import ALLOWED_TYPES_CSV, MAX_SIZE_CSV, validate_upload
from utils.logger import logger
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.IMPORTACION


def _repo() -> NominaImportRepo:
    return NominaImportRepo()


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
    repo: NominaImportRepo = Depends(_repo),
) -> ImportacionNominaConfirmarResponse:
    """UPSERT en batch por (empleado_id, anio, mes). empresa_id se toma del request (uniforme)."""
    filas = [
        {
            "empleado_id": f.empleado_id, "anio": f.anio, "mes": f.mes,
            "salario_bruto": f.salario_bruto,
            "cargas_sociales": max(0.0, f.salario_bruto - f.neto),
            "empresa_id": body.empresa_id,
        }
        for f in body.filas
    ]
    repo.batch_upsert_nomina(filas)

    importados = sum(1 for f in body.filas if not f.es_actualizacion)
    actualizados = sum(1 for f in body.filas if f.es_actualizacion)
    logger.info(
        "Importación nómina confirmada",
        extra={"importados": importados, "actualizados": actualizados, "errores": 0},
    )
    return ImportacionNominaConfirmarResponse(importados=importados, actualizados=actualizados, errores=[])
