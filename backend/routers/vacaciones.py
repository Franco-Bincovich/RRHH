"""Router de vacaciones: listado, export y escrituras. empresa_id: lecturas por X-Empresa-Id;
escrituras heredadas del empleado en el service. Las lecturas POR EMPLEADO (saldo e histórico)
viven en routers/vacaciones_empleado.py, que se monta ANTES por la colisión de rutas."""
from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.vacaciones import (
    SolicitudVacacionesCreate,
    SolicitudVacacionesListResponse,
    SolicitudVacacionesResponse,
    SolicitudVacacionesUpdate,
)
from services.vacaciones_service import VacacionesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()

SECCION = Seccion.VACACIONES


def _svc() -> VacacionesService:
    return VacacionesService()


@router.get("", response_model=SolicitudVacacionesListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_vacaciones(
    request: Request,
    area_id: Optional[UUID] = Query(None),
    empleado_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None, description="Inicio del rango; solapamiento, no contención"),
    fecha_hasta: Optional[date] = Query(None),
    proyecto_id: Optional[UUID] = Query(None, description="Empleados asignados a ese proyecto"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: VacacionesService = Depends(_svc),
) -> SolicitudVacacionesListResponse:
    u = request.state.user
    return service.get_all(u.get("id"), u.get("rol"), get_empresa_id(request), area_id, empleado_id, estado, page, page_size, fecha_desde, fecha_hasta, proyecto_id)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_vacaciones(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), area_id: Optional[UUID] = Query(None), empleado_id: Optional[UUID] = Query(None), estado: Optional[str] = Query(None), fecha_desde: Optional[date] = Query(None), fecha_hasta: Optional[date] = Query(None), proyecto_id: Optional[UUID] = Query(None), service: VacacionesService = Depends(_svc)) -> Response:
    u = request.state.user
    d = service.exportar(u.get("id"), u.get("rol"), get_empresa_id(request), formato, area_id, empleado_id, estado, fecha_desde, fecha_hasta, proyecto_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=SolicitudVacacionesResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_vacacion(id: UUID, request: Request, service: VacacionesService = Depends(_svc)) -> SolicitudVacacionesResponse:
    u = request.state.user
    return service.get_by_id(id, get_empresa_id(request), u.get("id"), u.get("rol"))


@router.post("", response_model=SolicitudVacacionesResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_vacacion(
    request: Request,
    body: SolicitudVacacionesCreate,
    service: VacacionesService = Depends(_svc),
) -> SolicitudVacacionesResponse:
    return service.create(body, request.state.user.get("id", "system"), request.state.user.get("rol"))


@router.put("/{id}", response_model=SolicitudVacacionesResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_vacacion(id: UUID, request: Request, body: SolicitudVacacionesUpdate, service: VacacionesService = Depends(_svc)) -> SolicitudVacacionesResponse:
    u = request.state.user
    return service.actualizar(id, body, get_empresa_id(request), u.get("id", "system"), u.get("rol"))


@router.put("/{id}/cancelar", response_model=SolicitudVacacionesResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def cancel_vacacion(id: UUID, request: Request, service: VacacionesService = Depends(_svc)) -> SolicitudVacacionesResponse:
    return service.cancel(id, get_empresa_id(request), request.state.user.get("id", "system"), request.state.user.get("rol"))
