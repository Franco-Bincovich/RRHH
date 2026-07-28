"""
Router de templates de onboarding — CRUD de templates y tareas configurables.
Montado en /api/onboarding/templates.
empresa_id para lecturas/scoping: header X-Empresa-Id (None = todas).
empresa_id para CREATE: viene en el body (root entity, dato explícito).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.onboarding import (
    TareaCreate, TareaResponse, TareaUpdate,
    TemplateCreate, TemplateResponse, TemplateUpdate,
)
from services.onboarding_templates_service import OnboardingTemplatesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.ONBOARDING
_Svc = Depends(lambda: OnboardingTemplatesService())


@router.get("", response_model=list[TemplateResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_templates(request: Request, svc: OnboardingTemplatesService = _Svc) -> list[TemplateResponse]:
    return svc.get_templates(get_empresa_id(request))


@router.post("", response_model=TemplateResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_template(body: TemplateCreate, request: Request, svc: OnboardingTemplatesService = _Svc) -> TemplateResponse:
    # Sin el fallback "system" que usan empleados/areas/empresa: acá el valor va a una columna
    # con FK a users, y un literal que no es UUID rompería el insert entero. None es lo que la
    # columna ya significa (nullable) y además es inalcanzable en la práctica — AuthMiddleware
    # es fail-closed, así que todo request que llega hasta acá trae usuario.
    return svc.create_template(body, request.state.user.get("id"))


@router.get("/{template_id}", response_model=TemplateResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_template(template_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc) -> TemplateResponse:
    return svc.get_template(template_id, get_empresa_id(request))


@router.put("/{template_id}", response_model=TemplateResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_template(
    template_id: UUID, body: TemplateUpdate, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> TemplateResponse:
    return svc.update_template(template_id, body, get_empresa_id(request))


@router.delete("/{template_id}", response_model=dict, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_template(template_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc) -> dict:
    svc.delete_template(template_id, get_empresa_id(request))
    return {"ok": True}


@router.post("/{template_id}/tareas", response_model=TareaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def add_tarea(
    template_id: UUID, body: TareaCreate, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> TareaResponse:
    return svc.add_tarea(template_id, body, get_empresa_id(request))


@router.put("/{template_id}/tareas/{tarea_id}", response_model=TareaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_tarea(
    template_id: UUID, tarea_id: UUID, body: TareaUpdate, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> TareaResponse:
    return svc.update_tarea(template_id, tarea_id, body, get_empresa_id(request))


@router.delete("/{template_id}/tareas/{tarea_id}", response_model=dict, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_tarea(
    template_id: UUID, tarea_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> dict:
    svc.delete_tarea(template_id, tarea_id, get_empresa_id(request))
    return {"ok": True}
