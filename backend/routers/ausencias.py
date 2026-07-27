"""Router de ausencias. Sección: "ausencias". empresa_id en lecturas: X-Empresa-Id; en escrituras: heredado del empleado. Tipos: catálogo global."""
from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.ausencias import (
    AusenciaCreate, AusenciaListResponse, AusenciaResponse, AusenciaUpdate,
)
from services.ausencias_service import AusenciasService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.AUSENCIAS


def _svc() -> AusenciasService: return AusenciasService()


# ── Ausencias ──────────────────────────────────────────────────────────────────

@router.get("", response_model=AusenciaListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_ausencias(
    request: Request,
    area_id: Optional[UUID] = Query(None),
    empleado_id: Optional[UUID] = Query(None),
    tipo_id: Optional[UUID] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: AusenciasService = Depends(_svc),
) -> AusenciaListResponse:
    return service.get_all(request.state.user.get("id"), request.state.user.get("rol"), get_empresa_id(request), area_id, empleado_id, tipo_id, page, page_size)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def exportar_ausencias(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), area_id: Optional[UUID] = Query(None), empleado_id: Optional[UUID] = Query(None), tipo_id: Optional[UUID] = Query(None), service: AusenciasService = Depends(_svc)) -> Response:
    d = service.exportar(request.state.user.get("id"), request.state.user.get("rol"), get_empresa_id(request), formato, area_id, empleado_id, tipo_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=AusenciaResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_ausencia(id: UUID, request: Request, service: AusenciasService = Depends(_svc)) -> AusenciaResponse:
    u = request.state.user
    return service.get_by_id(id, get_empresa_id(request), u.get("id"), u.get("rol"))


@router.post("", response_model=AusenciaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_ausencia(request: Request, body: AusenciaCreate, service: AusenciasService = Depends(_svc)) -> AusenciaResponse:
    return service.create(body, request.state.user.get("id", "system"), request.state.user.get("rol"))


@router.put("/{id}", response_model=AusenciaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_ausencia(
    id: UUID,
    request: Request,
    body: AusenciaUpdate,
    service: AusenciasService = Depends(_svc),
) -> AusenciaResponse:
    return service.update(id, body, get_empresa_id(request), request.state.user.get("id", "system"), request.state.user.get("rol"))


@router.delete("/{id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_ausencia(id: UUID, request: Request, service: AusenciasService = Depends(_svc)) -> dict:
    service.delete(id, get_empresa_id(request), request.state.user.get("id", "system"), request.state.user.get("rol"))
    return {"ok": True}
