"""Router de vacantes y pipeline de candidatos. empresa_id: lecturas por X-Empresa-Id, CREATE vacante por body.empresa_id, candidatos heredan de la vacante."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.vacante import CandidatoResponse, CandidatoDesdeEmailRequest, EmailCandidatoResponse, PublicarLinkedinRequest, PublicarLinkedinResponse, VacanteCreate, VacanteResponse, VacanteUpdate
from routers._candidato_form import candidato_form
from services.gmail_service import GmailService
from services.vacante_service import VacanteService
from services.zernio_service import ZernioService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.VACANTES


def _svc() -> VacanteService:
    return VacanteService()


@router.get("", response_model=List[VacanteResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_vacantes(
    request: Request, estado: Optional[str] = Query(None), service: VacanteService = Depends(_svc)
) -> List[VacanteResponse]:
    return service.get_vacantes(estado, get_empresa_id(request))


@router.get("/{id}", response_model=VacanteResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_vacante(id: UUID, request: Request, service: VacanteService = Depends(_svc)) -> VacanteResponse:
    return service.get_vacante(id, get_empresa_id(request))


@router.post("", response_model=VacanteResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_vacante(
    request: Request, body: VacanteCreate, service: VacanteService = Depends(_svc)
) -> VacanteResponse:
    return service.create_vacante(body, request.state.user.get("id", "system"))


@router.put("/{id}", response_model=VacanteResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_vacante(
    id: UUID, body: VacanteUpdate, request: Request, service: VacanteService = Depends(_svc)
) -> VacanteResponse:
    return service.update_vacante(id, body, get_empresa_id(request))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_vacante(id: UUID, request: Request, service: VacanteService = Depends(_svc)) -> None:
    u = request.state.user
    service.delete_vacante(id, get_empresa_id(request), u.get("rol"), u.get("id", "system"))


@router.get("/{id}/candidatos", response_model=List[CandidatoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_candidatos(id: UUID, request: Request, service: VacanteService = Depends(_svc)) -> List[CandidatoResponse]:
    return service.get_candidatos(id, get_empresa_id(request))


@router.post("/{id}/candidatos", response_model=CandidatoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def add_candidato(
    id: UUID, request: Request, form: tuple = Depends(candidato_form), service: VacanteService = Depends(_svc)
) -> CandidatoResponse:
    data, contenido, filename, content_type = form
    return service.add_candidato(id, data, get_empresa_id(request), contenido, filename, content_type)


@router.post("/{id}/publicar-linkedin", response_model=PublicarLinkedinResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def publicar_linkedin(id: UUID, body: PublicarLinkedinRequest, request: Request) -> PublicarLinkedinResponse:
    return ZernioService().publicar_en_vacante(str(id), body.email_contacto, request.state.user["id"], get_empresa_id(request))


@router.get("/{id}/emails-candidatos", response_model=List[EmailCandidatoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_emails_candidatos(id: UUID, request: Request) -> List[EmailCandidatoResponse]:
    return GmailService().get_emails_candidatos(str(id), request.state.user["id"], get_empresa_id(request))


@router.post("/{id}/candidatos-desde-email", response_model=CandidatoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def candidato_desde_email(id: UUID, body: CandidatoDesdeEmailRequest, request: Request) -> CandidatoResponse:
    return GmailService().crear_candidato_desde_email(str(id), body.email_id, request.state.user["id"], get_empresa_id(request))
