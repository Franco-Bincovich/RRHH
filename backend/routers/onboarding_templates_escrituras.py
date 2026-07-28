"""
Escrituras de templates de onboarding: alta/edición/baja de plantillas y de sus tareas.

Separado de onboarding_templates.py, que estaba en 80/80 y no admitía el parámetro de usuario
que exige la visibilidad pública/privada. Se monta en el MISMO prefijo, así que las rutas no
cambian. Molde: costos_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS: las seis escrituras son un bloque coherente
—las seis pasan por `ensure_template_accesible` antes de tocar nada—, y ningún test las ancla
por módulo. Las dos lecturas, en cambio, son las que `tests/test_paridad_list_export.py`
recorrería si algún día el módulo suma un export.

Los seis endpoints reciben el SUJETO (user_id + rol): sin él el service no puede decidir si
quien escribe alcanza la plantilla, y una privada ajena sería editable.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers.onboarding_templates import sujeto
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
_GATE = [Depends(require_permission(SECCION, Accion.WRITE))]


@router.post("", response_model=TemplateResponse, status_code=201, dependencies=_GATE)
async def create_template(body: TemplateCreate, request: Request, svc: OnboardingTemplatesService = _Svc) -> TemplateResponse:
    # Sin el fallback "system" que usan empleados/areas/empresa: acá el valor va a una columna
    # con FK a users, y un literal que no es UUID rompería el insert entero. None es lo que la
    # columna ya significa (nullable).
    return svc.create_template(body, sujeto(request)[0])


@router.put("/{template_id}", response_model=TemplateResponse, dependencies=_GATE)
async def update_template(
    template_id: UUID, body: TemplateUpdate, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> TemplateResponse:
    return svc.update_template(template_id, body, get_empresa_id(request), *sujeto(request))


@router.delete("/{template_id}", response_model=dict, dependencies=_GATE)
async def delete_template(template_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc) -> dict:
    svc.delete_template(template_id, get_empresa_id(request), *sujeto(request))
    return {"ok": True}


@router.post("/{template_id}/tareas", response_model=TareaResponse, status_code=201, dependencies=_GATE)
async def add_tarea(
    template_id: UUID, body: TareaCreate, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> TareaResponse:
    return svc.add_tarea(template_id, body, get_empresa_id(request), *sujeto(request))


@router.put("/{template_id}/tareas/{tarea_id}", response_model=TareaResponse, dependencies=_GATE)
async def update_tarea(
    template_id: UUID, tarea_id: UUID, body: TareaUpdate, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> TareaResponse:
    return svc.update_tarea(template_id, tarea_id, body, get_empresa_id(request), *sujeto(request))


@router.delete("/{template_id}/tareas/{tarea_id}", response_model=dict, dependencies=_GATE)
async def delete_tarea(
    template_id: UUID, tarea_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc,
) -> dict:
    svc.delete_tarea(template_id, tarea_id, get_empresa_id(request), *sujeto(request))
    return {"ok": True}
