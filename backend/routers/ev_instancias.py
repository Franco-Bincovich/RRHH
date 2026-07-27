"""Router de instancias y resultados de evaluación de desempeño."""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.evaluaciones import (
    InstanciaCreate, InstanciaDetalleResponse, InstanciaListResponse, ResultadoUpdate,
)
from services.ev_instancias_service import EvInstanciasService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.EVALUACIONES


def _svc() -> EvInstanciasService:
    return EvInstanciasService()


@router.get("", response_model=InstanciaListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_instancias(
    request: Request,
    ciclo_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None),
    service: EvInstanciasService = Depends(_svc),
) -> InstanciaListResponse:
    return service.get_all(get_empresa_id(request), ciclo_id, estado)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_instancias(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    ciclo_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None),
    service: EvInstanciasService = Depends(_svc),
) -> Response:
    d = service.exportar(get_empresa_id(request), formato, ciclo_id, estado)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=InstanciaDetalleResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_instancia(
    id: UUID, request: Request,
    service: EvInstanciasService = Depends(_svc),
) -> InstanciaDetalleResponse:
    return service.get_by_id(id, get_empresa_id(request))


@router.post("", response_model=InstanciaDetalleResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_instancia(
    body: InstanciaCreate,
    service: EvInstanciasService = Depends(_svc),
) -> InstanciaDetalleResponse:
    return service.create(body)


@router.put("/{id}/resultados/{criterio_id}", response_model=InstanciaDetalleResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_resultado(
    id: UUID, criterio_id: UUID, body: ResultadoUpdate, request: Request,
    service: EvInstanciasService = Depends(_svc),
) -> InstanciaDetalleResponse:
    return service.update_resultado(id, criterio_id, body, get_empresa_id(request), request.state.user.get("id"))


@router.post("/{id}/finalizar", response_model=InstanciaDetalleResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def finalizar_instancia(
    id: UUID, request: Request,
    service: EvInstanciasService = Depends(_svc),
) -> InstanciaDetalleResponse:
    return service.finalizar(id, get_empresa_id(request), request.state.user.get("id"))
