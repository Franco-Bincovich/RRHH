"""Router de empleados — CRUD; lecturas por header X-Empresa-Id, CREATE por body.empresa_id."""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.empleado import (
    EmpleadoCreate, EmpleadoListResponse, EmpleadoResponse, EmpleadoUpdate,
)
from services.empleado_service import EmpleadoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.EMPLEADOS


def _service() -> EmpleadoService:
    return EmpleadoService()


@router.get("", response_model=EmpleadoListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_empleados(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), area_id: Optional[str] = Query(None), estado: Optional[str] = Query(None), search: Optional[str] = Query(None), es_lider: Optional[bool] = Query(None), proyecto_id: Optional[UUID] = Query(None), sin_manager: Optional[bool] = Query(None), service: EmpleadoService = Depends(_service)) -> EmpleadoListResponse:
    empresa_id = get_empresa_id(request)
    return service.get_empleados(page, page_size, empresa_id, area_id, estado, search, es_lider, proyecto_id, sin_manager)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_empleados(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), area_id: Optional[str] = Query(None), estado: Optional[str] = Query(None), search: Optional[str] = Query(None), es_lider: Optional[bool] = Query(None), proyecto_id: Optional[UUID] = Query(None), sin_manager: Optional[bool] = Query(None), service: EmpleadoService = Depends(_service)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, area_id, estado, search, es_lider, proyecto_id, sin_manager)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=EmpleadoResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_empleado(
    id: UUID, request: Request, service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    empresa_id = get_empresa_id(request)
    return service.get_empleado(id, empresa_id)


@router.post("", response_model=EmpleadoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_empleado(
    request: Request,
    body: EmpleadoCreate,
    service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    created_by = request.state.user.get("id", "system")
    # empresa_id viene del body (dato del empleado), no del header X-Empresa-Id
    return service.create_empleado(body, created_by, body.empresa_id)


@router.put("/{id}", response_model=EmpleadoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_empleado(
    id: UUID,
    request: Request,
    body: EmpleadoUpdate,
    service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    empresa_id = get_empresa_id(request)
    return service.update_empleado(id, body, empresa_id, request.state.user.get("id", "system"))
