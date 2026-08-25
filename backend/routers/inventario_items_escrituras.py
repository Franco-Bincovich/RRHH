"""
Escrituras del módulo de ítems de inventario: alta, edición y baja.

Separado de inventario_items.py, que estaba en 79/80 y no admitía el decorador de la franja de
rate limit sobre su export (`shared_limit` + su import miden +2 líneas). Se monta en el MISMO
prefijo, así que las rutas no cambian. Molde: areas_escrituras.py, costos_escrituras.py y
onboarding_templates_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS: el export que motiva el corte ES una
lectura, y además de las cuatro lecturas dos son `/{id}` y `/{id}/historial`, que dependen de
quedar DESPUÉS de `/exportar` en el mismo router para que "exportar" no matchee como un uuid.
Mudar cualquiera de esas tres de archivo pone ese orden en manos del orden de include_router
en main.py. Hay una razón más: la clave del limiter es `routers.<módulo>.<función>`, así que
mover el export cambiaría la clave y dejaría su test mirando una clave inexistente, en verde.

empresa_id para crear: explícito en el body (el service lo toma de ahí).

El orden de registro respecto de inventario_items.py no es load-bearing: no hay colisión
posible entre un POST/PUT/DELETE y los GET del otro módulo.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.inventario import ItemCreate, ItemResponse, ItemUpdate
from services.inventario_items_service import InventarioItemsService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.INVENTARIO


def _svc() -> InventarioItemsService:
    return InventarioItemsService()


@router.post("", response_model=ItemResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_item(
    request: Request, body: ItemCreate,
    service: InventarioItemsService = Depends(_svc),
) -> ItemResponse:
    return service.create(body, request.state.user.get("id", "system"))


@router.put("/{id}", response_model=ItemResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_item(
    id: UUID, request: Request, body: ItemUpdate,
    service: InventarioItemsService = Depends(_svc),
) -> ItemResponse:
    return service.update(id, body, get_empresa_id(request), request.state.user.get("id"))


@router.delete("/{id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_item(
    id: UUID, request: Request,
    service: InventarioItemsService = Depends(_svc),
) -> dict:
    service.delete(id, get_empresa_id(request), request.state.user.get("id"))
    return {"ok": True}
