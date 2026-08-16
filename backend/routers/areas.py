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

from schemas.area import AreaListResponse, AreaResponse
from services.area_service import AreaService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.AREAS


def _service() -> AreaService:
    return AreaService()


def _empresa_str(request: Request) -> Optional[str]:
    """Empresa activa como str — el repo de áreas filtra por str, no por UUID."""
    eid = get_empresa_id(request)
    return str(eid) if eid else None


@router.get("", response_model=AreaListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_areas(
    empresa_id: Optional[str] = Query(None, description="Filtrar por empresa"),
    search: Optional[str] = Query(None, description="Búsqueda parcial por nombre"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AreaService = Depends(_service),
) -> AreaListResponse:
    return service.get_pagina(empresa_id, search, page, page_size)


# ⚠️ ANTES de /{id}: si fuera después, "opciones" matchearía como un id y daría 422 de UUID.
# 🔴 EL CATÁLOGO COMPLETO, SIN PAGINAR — y es una ruta aparte a propósito. Los ~15 selectores de
# área del front necesitan todas; el listado de arriba pagina porque es la pantalla de gestión.
# Servir las dos cosas por el mismo endpoint obligaba a elegir cuál de los dos se rompe. Molde:
# `/api/empleados/seleccionables`, que resolvió exactamente esto para el selector de superior.
@router.get("/opciones", response_model=List[AreaResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def opciones_areas(
    empresa_id: Optional[str] = Query(None, description="Filtrar por empresa"),
    service: AreaService = Depends(_service),
) -> List[AreaResponse]:
    return service.get_areas(empresa_id)


# ⚠️ ANTES de /{id}: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_areas(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), empresa_id: Optional[str] = Query(None, description="Filtrar por empresa"), search: Optional[str] = Query(None, description="Búsqueda parcial por nombre"), service: AreaService = Depends(_service)) -> Response:
    d = service.exportar(empresa_id, formato, search)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=AreaResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_area(
    id: UUID,
    request: Request,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    return service.get_area(id, _empresa_str(request))
