"""
Router de asignaciones de inventario. Montado en /api/inventario/asignaciones.
empresa_id para lecturas: X-Empresa-Id. Para asignar: heredado del ítem en el service.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.inventario import (
    AsignacionCreate, AsignacionListResponse, AsignacionResponse, DevolucionRequest,
)
from services.inventario_asignaciones_service import InventarioAsignacionesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.INVENTARIO


def _svc() -> InventarioAsignacionesService:
    return InventarioAsignacionesService()


@router.get("", response_model=AsignacionListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_asignaciones(
    request: Request,
    empleado_id: Optional[str] = Query(None),
    area_id: Optional[UUID] = Query(None),
    service: InventarioAsignacionesService = Depends(_svc),
) -> AsignacionListResponse:
    return service.get_all(get_empresa_id(request), empleado_id, area_id)


@router.post("", response_model=AsignacionResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def asignar_item(
    request: Request, body: AsignacionCreate,
    service: InventarioAsignacionesService = Depends(_svc),
) -> AsignacionResponse:
    return service.asignar(body, request.state.user.get("id", "system"))


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_asignaciones(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    empleado_id: Optional[str] = Query(None),
    area_id: Optional[UUID] = Query(None),
    service: InventarioAsignacionesService = Depends(_svc),
) -> Response:
    d = service.exportar(get_empresa_id(request), formato, empleado_id, area_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.post("/{id}/devolver", response_model=AsignacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def devolver_item(
    id: UUID, body: DevolucionRequest, request: Request,
    service: InventarioAsignacionesService = Depends(_svc),
) -> AsignacionResponse:
    return service.devolver(id, body, get_empresa_id(request))
