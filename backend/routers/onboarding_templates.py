"""
Lecturas de templates de onboarding. Montado en /api/onboarding/templates.

Las escrituras viven en onboarding_templates_escrituras.py, sobre el MISMO prefijo — el corte
es por límite de líneas (80/80) y las rutas no cambian. Molde: costos.py / costos_escrituras.py.

empresa_id: header X-Empresa-Id (None = todas las empresas, vista consolidada).
user_id: sale del request y es el SUJETO DE LA VISIBILIDAD pública/privada. Sin él el service
no puede resolver qué plantillas alcanza este usuario, así que va en todos los endpoints.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.onboarding import TemplateResponse
from services.onboarding_templates_service import OnboardingTemplatesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.ONBOARDING
_Svc = Depends(lambda: OnboardingTemplatesService())


def sujeto(request: Request) -> tuple[str | None, str | None]:
    """(user_id, rol) del request — el sujeto de la visibilidad de las plantillas.

    Los dos van juntos siempre: `user_id` decide de quién es una privada y `rol` si hay que
    filtrar (gerencia_lectura ve todo). Devolverlos por separado invitaba a pasar uno y
    olvidarse del otro. None solo en un estado imposible: AuthMiddleware es fail-closed.
    """
    u = request.state.user
    return u.get("id"), u.get("rol")


@router.get("", response_model=list[TemplateResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_templates(request: Request, svc: OnboardingTemplatesService = _Svc) -> list[TemplateResponse]:
    return svc.get_templates(get_empresa_id(request), *sujeto(request))


@router.get("/{template_id}", response_model=TemplateResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_template(template_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc) -> TemplateResponse:
    return svc.get_template(template_id, get_empresa_id(request), *sujeto(request))
