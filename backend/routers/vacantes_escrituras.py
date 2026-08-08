"""
Escrituras del módulo de vacantes: alta/edición/baja de vacante, alta de candidato,
publicación en LinkedIn y alta de candidato desde un email.

Separado de vacantes.py, que estaba en 80/80 —en el techo exacto— y no admitía el endpoint de
export. Se monta en el MISMO prefijo, así que las rutas no cambian. Molde: areas_escrituras.py,
usuarios_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS: el export que motiva el corte ES una lectura, y además tiene
que quedar declarado ANTES de `GET /{id}` para que "exportar" no matchee como un uuid — con las
dos en el mismo archivo ese orden es local y no depende del orden de include_router. En este
módulo ningún endpoint lleva decorador de rate limit, así que la regla de "no mover nada
decorado" (la clave del limiter es `routers.<módulo>.<función>`) no ata a ninguno acá.

`publicar_linkedin` y `candidato_desde_email` NO pasan por VacanteService: llaman directo a
ZernioService y GmailService, que resuelven la vacante y su empresa por su cuenta. Se movieron
igual porque son escrituras; su gate de permisos viaja con ellas.

El orden de registro respecto de vacantes.py no es load-bearing.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers._candidato_form import candidato_form
from schemas.vacante import (
    CandidatoDesdeEmailRequest, CandidatoResponse, PublicarLinkedinRequest,
    PublicarLinkedinResponse, VacanteCreate, VacanteResponse, VacanteUpdate,
)
from services.gmail_service import GmailService
from services.vacante_service import VacanteService
from services.zernio_service import ZernioService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.VACANTES


def _svc() -> VacanteService:
    return VacanteService()


@router.post("", response_model=VacanteResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_vacante(
    request: Request, body: VacanteCreate, service: VacanteService = Depends(_svc)
) -> VacanteResponse:
    return service.create_vacante(body, request.state.user.get("id", "system"))


@router.put("/{id}", response_model=VacanteResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_vacante(
    id: UUID, body: VacanteUpdate, request: Request, service: VacanteService = Depends(_svc)
) -> VacanteResponse:
    return service.update_vacante(id, body, get_empresa_id(request), request.state.user.get("id", "system"))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_vacante(id: UUID, request: Request, service: VacanteService = Depends(_svc)) -> None:
    u = request.state.user
    service.delete_vacante(id, get_empresa_id(request), u.get("rol"), u.get("id", "system"))


@router.post("/{id}/candidatos", response_model=CandidatoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def add_candidato(
    id: UUID, request: Request, form: tuple = Depends(candidato_form), service: VacanteService = Depends(_svc)
) -> CandidatoResponse:
    data, contenido, filename, content_type = form
    return service.add_candidato(id, data, get_empresa_id(request), contenido, filename, content_type, request.state.user.get("id", "system"))


@router.post("/{id}/publicar-linkedin", response_model=PublicarLinkedinResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def publicar_linkedin(id: UUID, body: PublicarLinkedinRequest, request: Request) -> PublicarLinkedinResponse:
    return ZernioService().publicar_en_vacante(str(id), body.email_contacto, request.state.user["id"], get_empresa_id(request))


@router.post("/{id}/candidatos-desde-email", response_model=CandidatoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def candidato_desde_email(id: UUID, body: CandidatoDesdeEmailRequest, request: Request) -> CandidatoResponse:
    return GmailService().crear_candidato_desde_email(str(id), body.email_id, request.state.user["id"], get_empresa_id(request))
