"""
Router de horas de proyecto. Comparte prefix /api/proyectos con proyectos.py.
cargado_por se obtiene de request.state.user (AuthMiddleware).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.horas import HoraCreate, HoraListResponse, HoraResponse
from services.horas_service import HorasService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.PROYECTOS


def _svc() -> HorasService:
    return HorasService()


@router.get("/{proyecto_id}/horas", response_model=HoraListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_horas(
    proyecto_id: UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: HorasService = Depends(_svc),
) -> HoraListResponse:
    return service.get_by_proyecto(proyecto_id, page, page_size, get_empresa_id(request))


@router.post("/{proyecto_id}/horas", response_model=HoraResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def cargar_horas(
    proyecto_id: UUID, request: Request, body: HoraCreate,
    service: HorasService = Depends(_svc),
) -> HoraResponse:
    cargado_por = getattr(request.state, "user", {}).get("id")
    return service.cargar(proyecto_id, body, cargado_por, get_empresa_id(request))


@router.delete("/{proyecto_id}/horas/{hora_id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_hora(
    proyecto_id: UUID, hora_id: UUID, request: Request,
    service: HorasService = Depends(_svc),
) -> dict:
    service.delete(hora_id, get_empresa_id(request))
    return {"ok": True}
