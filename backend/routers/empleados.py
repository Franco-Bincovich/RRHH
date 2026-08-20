"""Router de empleados — CRUD; lecturas por header X-Empresa-Id, CREATE por body.empresa_id."""
from typing import Annotated, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.empleado import (
    EmpleadoCreate, EmpleadoListResponse, EmpleadoResponse, EmpleadoUpdate, OrdenEmpleados,
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
async def list_empleados(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), area_id: Optional[str] = Query(None), estado: Optional[str] = Query(None), search: Optional[str] = Query(None), es_lider: Optional[bool] = Query(None), proyecto_id: Optional[UUID] = Query(None), sin_manager: Optional[bool] = Query(None), orden: Annotated[Optional[OrdenEmpleados], Query(description="fecha_ingreso_asc | fecha_egreso_desc; ausente = apellido (ver schemas/_empleado_orden)")] = None, service: EmpleadoService = Depends(_service)) -> EmpleadoListResponse:
    empresa_id = get_empresa_id(request)
    return service.get_empleados(page, page_size, empresa_id, area_id, estado, search, es_lider, proyecto_id, sin_manager, orden)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_empleados(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), area_id: Optional[str] = Query(None), estado: Optional[str] = Query(None), search: Optional[str] = Query(None), es_lider: Optional[bool] = Query(None), proyecto_id: Optional[UUID] = Query(None), sin_manager: Optional[bool] = Query(None), orden: Annotated[Optional[OrdenEmpleados], Query(description="mismo vocabulario que el listado: el archivo sale en el orden que se ve")] = None, service: EmpleadoService = Depends(_service)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, area_id, estado, search, es_lider, proyecto_id, sin_manager, orden)
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


# Segundo tramo LITERAL (`/activar`). Bajo este prefijo hay otras dos rutas de dos tramos
# —`/{empleado_id}/cesiones` y `/{empleado_id}/recategorizaciones`, montadas después— pero las
# tres tienen el segundo tramo literal y distinto, así que ninguna puede capturar a otra y el
# orden de registro NO es load-bearing (verificado contra `app.routes` el 18/8/2026).
# ⚠️ Lo que sí lo volvería load-bearing es una ruta con PARÁMETRO en el segundo tramo
# (`/{id}/{algo}`): capturaría "activar" como valor y habría que registrar ésta ANTES.
# Es un ACTO, no una edición de campo: por eso endpoint propio y sin body. Ver _empleado_activar.
@router.post("/{id}/activar", response_model=EmpleadoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def activar_empleado(
    id: UUID,
    request: Request,
    service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    return service.activar_empleado(id, get_empresa_id(request), request.state.user.get("id", "system"))


@router.put("/{id}", response_model=EmpleadoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_empleado(
    id: UUID,
    request: Request,
    body: EmpleadoUpdate,
    service: EmpleadoService = Depends(_service),
) -> EmpleadoResponse:
    empresa_id = get_empresa_id(request)
    return service.update_empleado(id, body, empresa_id, request.state.user.get("id", "system"))
