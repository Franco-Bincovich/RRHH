"""Router de vacantes — LECTURAS (listado, detalle, candidatos, emails y export).

Las escrituras (alta/edición/baja de vacante, alta de candidato, publicación en LinkedIn y alta
desde email) viven en routers/vacantes_escrituras.py, montado en el MISMO prefijo: las rutas no
cambiaron. El porqué del corte está en el docstring de ese archivo.

empresa_id: lecturas por X-Empresa-Id; los candidatos heredan la empresa de su vacante.
"""
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.vacante import CandidatoResponse, EmailCandidatoResponse, VacanteResponse
from services.gmail_service import GmailService
from services.vacante_service import VacanteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.VACANTES


def _svc() -> VacanteService:
    return VacanteService()


@router.get("", response_model=List[VacanteResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_vacantes(
    request: Request, estado: Optional[str] = Query(None), service: VacanteService = Depends(_svc)
) -> List[VacanteResponse]:
    return service.get_vacantes(estado, get_empresa_id(request))


# ⚠️ ANTES de /{id}: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_vacantes(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), estado: Optional[str] = Query(None), service: VacanteService = Depends(_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, estado)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=VacanteResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_vacante(id: UUID, request: Request, service: VacanteService = Depends(_svc)) -> VacanteResponse:
    return service.get_vacante(id, get_empresa_id(request))


@router.get("/{id}/candidatos", response_model=List[CandidatoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_candidatos(id: UUID, request: Request, service: VacanteService = Depends(_svc)) -> List[CandidatoResponse]:
    return service.get_candidatos(id, get_empresa_id(request))


@router.get("/{id}/emails-candidatos", response_model=List[EmailCandidatoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_emails_candidatos(id: UUID, request: Request) -> List[EmailCandidatoResponse]:
    return GmailService().get_emails_candidatos(str(id), request.state.user["id"], get_empresa_id(request))
