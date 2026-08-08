"""
Router de candidatos — operaciones del pipeline.
Rutas protegidas por AuthMiddleware (requieren JWT válido).
"""
from typing import List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.vacante import CandidatoGrupoResponse, CandidatoResponse, EtapaUpdate
from services.candidato_service import CandidatoService
from services.vacante_service import VacanteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.CANDIDATOS


def _svc() -> VacanteService:
    return VacanteService()


def _candidato_svc() -> CandidatoService:
    return CandidatoService()


@router.get("", response_model=List[CandidatoGrupoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def listar_candidatos(
    request: Request, service: CandidatoService = Depends(_candidato_svc)
) -> List[CandidatoGrupoResponse]:
    return service.listar_todos_candidatos(get_empresa_id(request))


# ⚠️ ANTES de /{id}/…: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_candidatos(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: CandidatoService = Depends(_candidato_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}/cv-url", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def candidato_cv_url(
    id: UUID, request: Request, service: CandidatoService = Depends(_candidato_svc)
) -> dict:
    return {"url": service.cv_signed_url(str(id), get_empresa_id(request))}


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_candidato(
    id: UUID, request: Request, service: CandidatoService = Depends(_candidato_svc)
) -> None:
    service.delete_candidato(str(id), get_empresa_id(request), request.state.user.get("id", "system"))


@router.put("/{id}/etapa", response_model=CandidatoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def mover_candidato(
    id: UUID, body: EtapaUpdate, request: Request, service: VacanteService = Depends(_svc)
) -> CandidatoResponse:
    return service.mover_candidato(id, body.etapa, get_empresa_id(request), request.state.user.get("id", "system"))
