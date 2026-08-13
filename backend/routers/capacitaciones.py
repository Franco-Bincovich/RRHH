"""Router de catálogo de capacitaciones. Sección: 'capacitaciones'.
empresa_id en lecturas: X-Empresa-Id. En escrituras: viene explícito en el body.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.capacitacion import (
    CapacitacionCreate, CapacitacionListResponse, CapacitacionResponse, CapacitacionUpdate,
)
from services.capacitacion_service import CapacitacionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.CAPACITACIONES


def _svc() -> CapacitacionService:
    return CapacitacionService()


@router.get("", response_model=CapacitacionListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_capacitaciones(
    request: Request,
    solo_activos: bool = Query(True),
    service: CapacitacionService = Depends(_svc),
) -> CapacitacionListResponse:
    return service.get_all(get_empresa_id(request), solo_activos)


# ⚠️ ANTES de /{id}: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_capacitaciones(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), solo_activos: bool = Query(True), service: CapacitacionService = Depends(_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, solo_activos)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=CapacitacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_capacitacion(
    id: UUID,
    request: Request,
    service: CapacitacionService = Depends(_svc),
) -> CapacitacionResponse:
    return service.get_by_id(id, get_empresa_id(request))


@router.post("", response_model=CapacitacionResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_capacitacion(
    request: Request,
    body: CapacitacionCreate,
    service: CapacitacionService = Depends(_svc),
) -> CapacitacionResponse:
    return service.create(body, request.state.user.get("id", "system"))


@router.put("/{id}", response_model=CapacitacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_capacitacion(
    id: UUID,
    request: Request,
    body: CapacitacionUpdate,
    service: CapacitacionService = Depends(_svc),
) -> CapacitacionResponse:
    return service.update(id, body, get_empresa_id(request))


@router.delete("/{id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_capacitacion(
    id: UUID,
    request: Request,
    service: CapacitacionService = Depends(_svc),
) -> dict:
    service.delete(id, get_empresa_id(request))
    return {"ok": True}
