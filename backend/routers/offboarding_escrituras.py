"""
Escrituras del módulo de offboarding: alta del proceso, devolución de activos y registro de la
entrevista de salida.

Separado de offboarding.py, que estaba en 78/80 y no admitía el endpoint de export. Se monta en
el MISMO prefijo, así que las rutas no cambian. Molde: areas_escrituras.py,
usuarios_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS: el export que motiva el corte ES una lectura, así que queda
del lado correcto para no volver a partir el archivo en la próxima tanda. Acá ningún endpoint
lleva decorador de rate limit, así que la regla de "no mover nada decorado" (la clave del
limiter es `routers.<módulo>.<función>`) no ata a ninguno.

empresa_id para CREATE: heredada del EMPLEADO, no del header — el service la resuelve
internamente (principio Vista vs Acción). El orden de registro no es load-bearing.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.offboarding import (
    ActivoUpdate, EntrevistaUpdate, OffboardingCreate, OffboardingResponse,
)
from services.offboarding_service import OffboardingService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.OFFBOARDING


def _service() -> OffboardingService:
    return OffboardingService()


@router.post("", response_model=OffboardingResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def crear_offboarding(
    body: OffboardingCreate,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> OffboardingResponse:
    return service.iniciar_offboarding(body, get_empresa_id(request), request.state.user.get("id", "system"))


@router.put(
    "/{instancia_id}/activos/{activo_id}",
    response_model=dict,
    dependencies=[Depends(require_permission(SECCION, Accion.WRITE))],
)
async def actualizar_activo(
    instancia_id: UUID,
    activo_id: UUID,
    body: ActivoUpdate,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> dict:
    service.marcar_activo_devuelto(
        instancia_id, activo_id, body.devuelto,
        request.state.user.get("id", "system"), get_empresa_id(request),
    )
    return {"ok": True}


@router.put(
    "/{instancia_id}/entrevista",
    response_model=dict,
    dependencies=[Depends(require_permission(SECCION, Accion.WRITE))],
)
async def registrar_entrevista(
    instancia_id: UUID,
    body: EntrevistaUpdate,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> dict:
    service.registrar_entrevista(
        instancia_id, body.entrevista_salida, body.notas_entrevista,
        request.state.user.get("id", "system"), get_empresa_id(request),
    )
    return {"ok": True}
