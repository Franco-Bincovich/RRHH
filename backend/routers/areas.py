"""
Router de áreas — LECTURAS.
Rutas protegidas por AuthMiddleware (requieren JWT válido).

Las escrituras (POST/PUT/DELETE) viven en routers/areas_escrituras.py, montado en el MISMO
prefijo: las rutas no cambiaron. El porqué del corte está en el docstring de ese archivo.
"""
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.area import AreaResponse
from services.area_service import AreaService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

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


# ⚠️ ANTES de /{id}: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_areas(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), empresa_id: Optional[str] = Query(None, description="Filtrar por empresa"), service: AreaService = Depends(_service)) -> Response:
    d = service.exportar(empresa_id, formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=AreaResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_area(
    id: UUID,
    request: Request,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    return service.get_area(id, _empresa_str(request))
