"""
Router de ítems de inventario — LECTURAS. Montado en /api/inventario/items.
Sección: "inventario" (identificador estable para la futura capa de permisos).
empresa_id para lecturas: X-Empresa-Id.

Las escrituras (POST/PUT/DELETE) viven en routers/inventario_items_escrituras.py, montado en
el MISMO prefijo: las rutas no cambiaron. El porqué del corte está en el docstring de ese archivo.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.inventario import ItemListResponse, ItemResponse
from services.inventario_items_service import InventarioItemsService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.INVENTARIO


def _svc() -> InventarioItemsService:
    return InventarioItemsService()


@router.get("", response_model=ItemListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_items(
    request: Request,
    estado: Optional[str] = Query(None), area_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: InventarioItemsService = Depends(_svc),
) -> ItemListResponse:
    return service.get_all(get_empresa_id(request), estado, area_id, page, page_size)


# ⚠️ ANTES de /{id}: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
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
