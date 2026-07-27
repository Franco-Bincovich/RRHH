"""Router de asignaciones de capacitaciones. empresa_id en lecturas: X-Empresa-Id; en escrituras: heredado del empleado."""
from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from schemas.capacitacion import AsignacionCreate, AsignacionListResponse, AsignacionResponse, AsignacionUpdate
from services.asignacion_service import AsignacionService
from utils.empresa import get_empresa_id
from utils.files import ALLOWED_TYPES_CERTIFICADO, MAX_SIZE_CERTIFICADO, validate_upload
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.CAPACITACIONES
def _svc() -> AsignacionService: return AsignacionService()


@router.get("", response_model=AsignacionListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_asignaciones(
    request: Request,
    empleado_id: Optional[UUID] = Query(None),
    capacitacion_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None),
    area_id: Optional[UUID] = Query(None),
    service: AsignacionService = Depends(_svc),
) -> AsignacionListResponse:
    return service.get_all(get_empresa_id(request), empleado_id, capacitacion_id, estado, area_id)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_asignaciones(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), empleado_id: Optional[UUID] = Query(None), capacitacion_id: Optional[UUID] = Query(None), estado: Optional[str] = Query(None), area_id: Optional[UUID] = Query(None), service: AsignacionService = Depends(_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, empleado_id, capacitacion_id, estado, area_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


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


@router.get("/{id}/certificado", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_certificado_url(
    id: UUID,
    request: Request,
    service: AsignacionService = Depends(_svc),
) -> dict:
    return {"url": service.get_certificado_signed_url(str(id), get_empresa_id(request))}
