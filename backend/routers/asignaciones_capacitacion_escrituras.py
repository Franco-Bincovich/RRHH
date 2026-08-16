"""
Escrituras de asignaciones de capacitación: alta, cambio de estado, baja y carga del certificado.

Separado de `asignaciones_capacitacion.py`, que estaba en 79/80 y no admitía los dos `Query` de
paginación que el listado necesitaba. Se monta en el MISMO prefijo, así que las rutas no cambian.
Molde: `areas_escrituras.py`.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS: el listado y su export son los que CRECEN —
cada filtro nuevo les suma un `Query` en dos lugares— así que tienen que quedar juntos y con
lugar. Las escrituras son estables: son las mismas cuatro desde que existe el módulo.

⚠️ `GET /{id}/certificado` se queda del lado de las LECTURAS aunque su hermano `POST` venga acá:
el criterio del corte es el método, no el recurso. Devuelve una URL firmada y está gateado con
READ, así que moverlo abriría la pregunta de por qué una lectura vive en el archivo de escrituras.

El orden de registro respecto de `asignaciones_capacitacion.py` no es load-bearing: no hay
colisión posible entre `GET /exportar` y estas rutas (ningún método coincide sobre el mismo path).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile

from schemas.capacitacion import AsignacionCreate, AsignacionResponse, AsignacionUpdate
from services.asignacion_service import AsignacionService
from utils.empresa import get_empresa_id
from utils.files import ALLOWED_TYPES_CERTIFICADO, MAX_SIZE_CERTIFICADO, validate_upload
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.CAPACITACIONES


def _svc() -> AsignacionService:
    return AsignacionService()


@router.post("", response_model=AsignacionResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_asignacion(request: Request, body: AsignacionCreate, service: AsignacionService = Depends(_svc)) -> AsignacionResponse:
    return service.create(body, request.state.user.get("id", "system"))


@router.put("/{id}", response_model=AsignacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_asignacion(
    id: UUID,
    request: Request,
    body: AsignacionUpdate,
    service: AsignacionService = Depends(_svc),
) -> AsignacionResponse:
    return service.update_estado(id, body, get_empresa_id(request))


@router.delete("/{id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_asignacion(id: UUID, request: Request, service: AsignacionService = Depends(_svc)) -> dict:
    service.delete(id, get_empresa_id(request))
    return {"ok": True}


@router.post("/{id}/certificado", response_model=AsignacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def upload_certificado(
    id: UUID,
    request: Request,
    file: UploadFile = File(...),
    service: AsignacionService = Depends(_svc),
) -> AsignacionResponse:
    content = await file.read()
    validate_upload(content, file.content_type, ALLOWED_TYPES_CERTIFICADO, MAX_SIZE_CERTIFICADO, "certificado")
    return service.upload_certificado(
        str(id), get_empresa_id(request),
        content, file.filename or "certificado", file.content_type or "application/pdf",
    )
