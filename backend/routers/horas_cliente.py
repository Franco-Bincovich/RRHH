"""
Router de la vista interna "Horas por cliente". SOLO RRHH — nada de esto es público.

🔴 GATEA CON `Seccion.PROYECTOS`, no con una nueva ni con `Seccion.CLIENTES`. El dato son filas
de `horas_proyecto`, cuyo gate publicado ya es PROYECTOS. CLIENTES gatea el CATÁLOGO, que es otra
cosa; y una sección nueva haría que las MISMAS filas tengan dos gates según por qué pantalla se
entre. Mismo criterio con el que `/comunicacion` reusó `configuracion`.

Es una VISTA: la empresa sale del header, None = consolidado. Lo único que es ACCIÓN es el
DELETE, que audita con la empresa de la entidad.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.horas_cliente import DetalleEmpleadoResponse, HorasPorClienteResponse
from services.horas_cliente_service import HorasClienteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.PROYECTOS


def _svc() -> HorasClienteService:
    return HorasClienteService()


def _usuario_id(request: Request) -> Optional[str]:
    """Autor del evento de auditoría de la baja."""
    return (getattr(request.state, "user", None) or {}).get("id")


@router.get("", response_model=HorasPorClienteResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def vista(
    request: Request,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    service: HorasClienteService = Depends(_svc),
) -> HorasPorClienteResponse:
    return service.get_vista(mes, anio, get_empresa_id(request))


# ⚠️ ANTES de cualquier ruta con parámetro: FastAPI resuelve por ORDEN DE DECLARACIÓN y con
# `/{algo}` arriba, "exportar" matchearía como el parámetro. Ídem areas.py.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar(
    request: Request,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    service: HorasClienteService = Depends(_svc),
) -> Response:
    d = service.exportar(mes, anio, get_empresa_id(request), formato)
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/detalle", response_model=DetalleEmpleadoResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def detalle(
    request: Request,
    empleado_id: UUID = Query(...),
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    service: HorasClienteService = Depends(_svc),
) -> DetalleEmpleadoResponse:
    return service.get_detalle(empleado_id, mes, anio, get_empresa_id(request))


@router.delete("/{hora_id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def eliminar(
    hora_id: UUID,
    request: Request,
    service: HorasClienteService = Depends(_svc),
) -> None:
    service.eliminar(hora_id, get_empresa_id(request), _usuario_id(request))
