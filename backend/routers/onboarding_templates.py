"""
Lecturas de templates de onboarding. Montado en /api/onboarding/templates.

Las escrituras viven en onboarding_templates_escrituras.py, sobre el MISMO prefijo — el corte
es por límite de líneas (80/80) y las rutas no cambian. Molde: costos.py / costos_escrituras.py.

empresa_id: header X-Empresa-Id (None = todas las empresas, vista consolidada).
user_id: sale del request y es el SUJETO DE LA VISIBILIDAD pública/privada. Sin él el service
no puede resolver qué plantillas alcanza este usuario, así que va en todos los endpoints.
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.onboarding import TemplateResponse
from services.onboarding_templates_service import OnboardingTemplatesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export
from utils.sujeto import sujeto

router = APIRouter()
SECCION = Seccion.ONBOARDING
_Svc = Depends(lambda: OnboardingTemplatesService())

# ⚠️ `sujeto` VIVÍA ACÁ y se mudó a `utils/sujeto.py` cuando la agenda de eventos (migración 113)
# pasó a ser el segundo módulo con filas públicas y privadas. Un router exportando un helper que
# otro router importa era tolerable con un solo caso; con dos, el que importa de un módulo
# hermano termina copiándolo, y las dos copias se separan. Se re-exporta al importarlo, así los
# call sites de acá abajo y los de `onboarding_templates_escrituras.py` no cambiaron.


@router.get("", response_model=list[TemplateResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_templates(request: Request, svc: OnboardingTemplatesService = _Svc) -> list[TemplateResponse]:
    return svc.get_templates(get_empresa_id(request), *sujeto(request))


# ⚠️ ANTES de /{template_id}: si fuera después, "exportar" matchearía como un id y daría 422.
# 🔴 Pasa `sujeto(request)` igual que el listado: sin eso el archivo traería las plantillas
# privadas de otros usuarios. Acá el universo lo acota quién sos, no un Query.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_templates(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), svc: OnboardingTemplatesService = _Svc) -> Response:
    d = svc.exportar(get_empresa_id(request), *sujeto(request), formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{template_id}", response_model=TemplateResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_template(template_id: UUID, request: Request, svc: OnboardingTemplatesService = _Svc) -> TemplateResponse:
    return svc.get_template(template_id, get_empresa_id(request), *sujeto(request))
