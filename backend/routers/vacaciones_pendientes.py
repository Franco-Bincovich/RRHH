"""Router de días de vacaciones PENDIENTES (los que no se tomaron). CRUD completo.

Prefijo propio /api/vacaciones-pendientes y NO /api/vacaciones/pendientes: el router de
vacaciones tiene un GET /{id} que se comería la ruta estática. Es la misma colisión que main.py
ya resolvió montando vacaciones_empleado ANTES que vacaciones; un prefijo propio la evita sin
depender del orden de registro.

empresa_id de lectura: header X-Empresa-Id (filtro de vista). En las escrituras la empresa se
hereda del EMPLEADO en el service, no del header (principio Vista vs Acción).
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.vacaciones_pendientes import (
    VacacionPendienteCreate, VacacionPendienteListResponse,
    VacacionPendienteResponse, VacacionPendienteUpdate,
)
from services.vacaciones_pendientes_service import VacacionesPendientesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.VACACIONES


def _svc() -> VacacionesPendientesService:
    return VacacionesPendientesService()


@router.get("", response_model=VacacionPendienteListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_pendientes(
    request: Request,
    area_id: Optional[UUID] = Query(None),
    empleado_id: Optional[UUID] = Query(None),
    proyecto_id: Optional[UUID] = Query(None, description="Empleados asignados a ese proyecto"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: VacacionesPendientesService = Depends(_svc),
) -> VacacionPendienteListResponse:
    u = request.state.user
    return service.get_all(u.get("id"), u.get("rol"), get_empresa_id(request), area_id, empleado_id, page, page_size, proyecto_id)


# ⚠️ ANTES de cualquier ruta con parámetro: un GET /{id} arriba haría matchear "exportar" como id (422).
# 🔴 Pasa user_id y rol como el listado: acá el universo lo acota el OWNERSHIP, no solo la empresa.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_pendientes(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), area_id: Optional[UUID] = Query(None), empleado_id: Optional[UUID] = Query(None), proyecto_id: Optional[UUID] = Query(None, description="Empleados asignados a ese proyecto"), service: VacacionesPendientesService = Depends(_svc)) -> Response:
    u = request.state.user
    d = service.exportar(u.get("id"), u.get("rol"), get_empresa_id(request), formato, area_id, empleado_id, proyecto_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/empleado/{empleado_id}", response_model=VacacionPendienteListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_pendientes_empleado(empleado_id: UUID, request: Request, service: VacacionesPendientesService = Depends(_svc)) -> VacacionPendienteListResponse:
    u = request.state.user
    return service.get_by_empleado(empleado_id, u.get("id"), u.get("rol"), get_empresa_id(request))


@router.post("", response_model=VacacionPendienteResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_pendiente(request: Request, body: VacacionPendienteCreate, service: VacacionesPendientesService = Depends(_svc)) -> VacacionPendienteResponse:
    u = request.state.user
    return service.crear(body, u.get("id", "system"), u.get("rol"), get_empresa_id(request))


@router.put("/{id}", response_model=VacacionPendienteResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_pendiente(id: UUID, request: Request, body: VacacionPendienteUpdate, service: VacacionesPendientesService = Depends(_svc)) -> VacacionPendienteResponse:
    u = request.state.user
    return service.actualizar(id, body, get_empresa_id(request), u.get("id", "system"), u.get("rol"))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_pendiente(id: UUID, request: Request, service: VacacionesPendientesService = Depends(_svc)) -> None:
    u = request.state.user
    service.eliminar(id, get_empresa_id(request), u.get("id", "system"), u.get("rol"))
