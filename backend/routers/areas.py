"""
Router de áreas — CRUD completo.
Rutas protegidas por AuthMiddleware (requieren JWT válido).
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.area import AreaCreate, AreaResponse, AreaUpdate
from services.area_service import AreaService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.AREAS


def _service() -> AreaService:
    return AreaService()


def _empresa_str(request: Request) -> Optional[str]:
    """Empresa activa como str — el repo de áreas filtra por str, no por UUID."""
    eid = get_empresa_id(request)
    return str(eid) if eid else None


@router.get("", response_model=List[AreaResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_areas(
    empresa_id: Optional[str] = Query(None, description="Filtrar por empresa"),
    service: AreaService = Depends(_service),
) -> List[AreaResponse]:
    return service.get_areas(empresa_id)


@router.get("/{id}", response_model=AreaResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_area(
    id: UUID,
    request: Request,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    return service.get_area(id, _empresa_str(request))


@router.post("", response_model=AreaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_area(
    request: Request,
    body: AreaCreate,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    created_by = request.state.user.get("id", "system")
    return service.create_area(body, created_by)


@router.put("/{id}", response_model=AreaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_area(
    id: UUID,
    body: AreaUpdate,
    request: Request,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    return service.update_area(id, body, _empresa_str(request))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_area(
    id: UUID,
    request: Request,
    service: AreaService = Depends(_service),
) -> None:
    service.delete_area(id, _empresa_str(request))
