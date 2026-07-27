"""
Router de onboarding — instancias activas y completado de tareas.
Rutas protegidas por AuthMiddleware.
empresa_id para lecturas: header X-Empresa-Id (filtro de vista, None = todas).
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.onboarding import IniciarOnboardingRequest, InstanciaDetalleResponse, InstanciaResponse
from services.onboarding_service import OnboardingService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.ONBOARDING


def _service() -> OnboardingService:
    return OnboardingService()


@router.get("", response_model=list[InstanciaResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_onboardings(
    request: Request,
    service: OnboardingService = Depends(_service),
) -> list[InstanciaResponse]:
    empresa_id = get_empresa_id(request)
    return service.get_onboardings_activos(empresa_id)


@router.get("/{empleado_id}", response_model=InstanciaDetalleResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_onboarding_empleado(
    empleado_id: UUID,
    request: Request,
    service: OnboardingService = Depends(_service),
) -> InstanciaDetalleResponse:
    empresa_id = get_empresa_id(request)
    return service.get_onboarding_empleado(empleado_id, empresa_id)


@router.post("/{empleado_id}/iniciar", response_model=InstanciaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def iniciar_onboarding(
    empleado_id: UUID,
    request: Request,
    body: Optional[IniciarOnboardingRequest] = None,
    service: OnboardingService = Depends(_service),
) -> InstanciaResponse:
    template_id = body.template_id if body else None
    return service.iniciar_onboarding(empleado_id, template_id, get_empresa_id(request))


@router.put(
    "/{instancia_id}/tareas/{tarea_id}/completar",
    response_model=dict,
    dependencies=[Depends(require_permission(SECCION, Accion.WRITE))],
)
async def completar_tarea(
    instancia_id: UUID,
    tarea_id: UUID,
    service: OnboardingService = Depends(_service),
) -> dict:
    service.completar_tarea(instancia_id, tarea_id)
    return {"ok": True}
