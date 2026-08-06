"""
Router de ítems de inventario. Montado en /api/inventario/items.
Sección: "inventario" (identificador estable para la futura capa de permisos).
empresa_id para lecturas: X-Empresa-Id. Para crear: explícito en el body.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.inventario import ItemCreate, ItemListResponse, ItemResponse, ItemUpdate
from services.inventario_items_service import InventarioItemsService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.INVENTARIO


def _svc() -> InventarioItemsService:
    return InventarioItemsService()


@router.get("", response_model=ItemListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_items(
    request: Request,
    estado: Optional[str] = Query(None), area_id: Optional[UUID] = Query(None),
    service: InventarioItemsService = Depends(_svc),
) -> ItemListResponse:
    return service.get_all(get_empresa_id(request), estado, area_id)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def exportar_items(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), estado: Optional[str] = Query(None), area_id: Optional[UUID] = Query(None), service: InventarioItemsService = Depends(_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, estado, area_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=ItemResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_item(
    id: UUID, request: Request,
    service: InventarioItemsService = Depends(_svc),
) -> ItemResponse:
    return service.get_by_id(id, get_empresa_id(request))


@router.get("/{id}/historial", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_historial(
    id: UUID, request: Request,
    service: InventarioItemsService = Depends(_svc),
):
    from services.inventario_asignaciones_service import InventarioAsignacionesService
    return InventarioAsignacionesService().get_historial(id, get_empresa_id(request))


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
    return service.update(id, body, get_empresa_id(request))


@router.delete("/{id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_item(
    id: UUID, request: Request,
    service: InventarioItemsService = Depends(_svc),
) -> dict:
    service.delete(id, get_empresa_id(request))
    return {"ok": True}
