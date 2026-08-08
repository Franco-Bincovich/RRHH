"""
Escrituras del módulo de objetivos: alta, cambio de estado, edición y baja.

Separado de objetivos.py, que estaba en 79/80 y no admitía el decorador de la franja de rate
limit sobre su export (`shared_limit` + su import miden +2 líneas). Se monta en el MISMO
prefijo, así que las rutas no cambian. Molde: areas_escrituras.py, costos_escrituras.py y
onboarding_templates_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS: el export que motiva el corte ES una
lectura. Además de quedar del lado correcto para no volver a partir el archivo en la próxima
tanda, hay una razón dura: la clave del limiter es `routers.<módulo>.<función>`, así que mudar
el export de archivo cambiaría la clave — y el test que lo verifica pasaría a mirar una clave
inexistente y quedaría vacuo, en verde. El export se queda donde estaba.

empresa_id para crear: explícito en el body (el service lo toma de ahí).
Las tres ediciones resuelven la empresa igual, por get_empresa_id — son un bloque coherente.

El orden de registro respecto de objetivos.py no es load-bearing: no hay colisión posible
entre un POST/PUT/DELETE y los dos GET del otro módulo.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.objetivo import CambiarEstadoRequest, ObjetivoCreate, ObjetivoResponse, ObjetivoUpdate
from services.objetivo_service import ObjetivoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.OBJETIVOS


def _svc() -> ObjetivoService:
    return ObjetivoService()


@router.post("", response_model=ObjetivoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_objetivo(
    request: Request, body: ObjetivoCreate,
    service: ObjetivoService = Depends(_svc),
) -> ObjetivoResponse:
    return service.create(body, request.state.user.get("id", "system"))


@router.put("/{id}/estado", response_model=ObjetivoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def cambiar_estado(
    id: UUID, request: Request, body: CambiarEstadoRequest,
    service: ObjetivoService = Depends(_svc),
) -> ObjetivoResponse:
    return service.cambiar_estado(id, body, get_empresa_id(request))


@router.put("/{id}", response_model=ObjetivoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_objetivo(
    id: UUID, request: Request, body: ObjetivoUpdate,
    service: ObjetivoService = Depends(_svc),
) -> ObjetivoResponse:
    return service.update(id, body, get_empresa_id(request))


@router.delete("/{id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_objetivo(
    id: UUID, request: Request,
    service: ObjetivoService = Depends(_svc),
) -> dict:
    service.delete(id, get_empresa_id(request))
    return {"ok": True}
