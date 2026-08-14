"""
Router de recategorizaciones — LECTURAS de la planilla.

Las escrituras viven en `recategorizaciones_escrituras.py` y el historial de la ficha en
`recategorizaciones_empleado.py` (otra ruta, bajo `/api/empleados/{id}/...`). Se parte DESDE EL
PRINCIPIO, igual que en `clientes.py` y `perfiles_puesto.py`.

🔴 EL LISTADO NACE PAGINADO, con `page_size` topeado en 100. Un `page_size` sin techo convierte
el listado en un export encubierto que esquiva `verificar_limite_export`.

⚠️ El rango filtra por `fecha_efectiva` —cuándo RIGIÓ— y no por `created_at` —cuándo se cargó—.
Con fecha retroactiva las dos difieren, y la pregunta de RRHH es siempre la primera.

⚠️ `impacto_salarial` sale en `None` sin `COSTOS + READ` (ver `_recategorizaciones_costos.py`).
NO se gatea la ruta: el historial de rol y seniority le sirve a cualquiera que vea el legajo.
"""
from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from routers._recategorizaciones_costos import puede_ver_costos
from schemas.recategorizacion import RecategorizacionListResponse, RecategorizacionResponse
from services.recategorizacion_service import RecategorizacionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.RECATEGORIZACIONES


def _service() -> RecategorizacionService:
    return RecategorizacionService()


@router.get("", response_model=RecategorizacionListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_recategorizaciones(
    request: Request,
    empleado_id: Optional[UUID] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: RecategorizacionService = Depends(_service),
) -> RecategorizacionListResponse:
    return service.listar(page, page_size, get_empresa_id(request), empleado_id,
                          fecha_desde, fecha_hasta,
                          puede_ver_costos=puede_ver_costos(request))


# 🔴 `/exportar` va ANTES de `/{id}`: si fuera después, FastAPI resuelve por ORDEN DE
# DECLARACIÓN y "exportar" matchearía como el path param `id: UUID` → 422 en vez del archivo.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_recategorizaciones(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    empleado_id: Optional[UUID] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    service: RecategorizacionService = Depends(_service),
) -> Response:
    """Export — MISMOS Query que el listado, sin `page`. `request` lo exige slowapi."""
    d = service.exportar(get_empresa_id(request), empleado_id, fecha_desde, fecha_hasta, formato,
                         puede_ver_costos=puede_ver_costos(request))
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=RecategorizacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_recategorizacion(
    id: UUID,
    request: Request,
    service: RecategorizacionService = Depends(_service),
) -> RecategorizacionResponse:
    return service.obtener(id, get_empresa_id(request),
                           puede_ver_costos=puede_ver_costos(request))
