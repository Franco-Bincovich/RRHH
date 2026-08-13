"""Router de períodos cerrados (bloqueo por período). Rutas protegidas por AuthMiddleware.
Cerrar/reabrir: admin_rrhh (Seccion.PERIODOS + WRITE). Listar: READ."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.periodo import PeriodoCreate, PeriodoListResponse, PeriodoResponse
from services.periodo_service import PeriodoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.PERIODOS


def _svc() -> PeriodoService:
    return PeriodoService()


@router.get("", response_model=PeriodoListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def listar_periodos(request: Request, service: PeriodoService = Depends(_svc)) -> PeriodoListResponse:
    return service.listar(get_empresa_id(request))


# ⚠️ ANTES de /{id}/reabrir: si fuera después, "exportar" podría matchear como un id.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_periodos(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: PeriodoService = Depends(_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.post("", response_model=PeriodoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def cerrar_periodo(request: Request, body: PeriodoCreate, service: PeriodoService = Depends(_svc)) -> PeriodoResponse:
    usuario_id = request.state.user.get("id", "system")
    return service.cerrar(body.empresa_id, body.modulo, body.desde, body.hasta, usuario_id)


@router.post("/{id}/reabrir", response_model=PeriodoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def reabrir_periodo(id: UUID, request: Request, service: PeriodoService = Depends(_svc)) -> PeriodoResponse:
    usuario_id = request.state.user.get("id", "system")
    return service.reabrir(str(id), get_empresa_id(request), usuario_id)
