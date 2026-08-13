"""
Router de la vista interna "Horas por cliente". SOLO RRHH — nada de esto es público.

🔴 GATEA CON `Seccion.PROYECTOS`, no con una nueva ni con `Seccion.CLIENTES`. El dato son filas
de `horas_proyecto`, cuyo gate publicado ya es PROYECTOS. CLIENTES gatea el CATÁLOGO, que es otra
cosa; y una sección nueva haría que las MISMAS filas tengan dos gates según por qué pantalla se
entre. Mismo criterio con el que `/comunicacion` reusó `configuracion`.

Acá viven las LECTURAS. La baja está en `horas_cliente_escrituras.py`, montado en el MISMO
prefijo: las rutas no cambian. El corte es el molde de `clientes.py` / `clientes_escrituras.py`,
y se hizo cuando el archivo llegó a 80/80 — antes de necesitarlo, no cuando reventara.

POR QUÉ SALE LA ESCRITURA Y NO LAS LECTURAS: el export, que es el que más crece, es una lectura;
dejarlo de este lado evita volver a partir el archivo en la próxima tanda. Mismo criterio,
textual, que `areas_escrituras.py`.
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.horas_cliente import DetalleEmpleadoResponse, HorasPorClienteResponse
from services.horas_cliente_service import HorasClienteService
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.PROYECTOS


def _svc() -> HorasClienteService:
    return HorasClienteService()


@router.get("", response_model=HorasPorClienteResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def vista(
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    service: HorasClienteService = Depends(_svc),
) -> HorasPorClienteResponse:
    # Sin `X-Empresa-Id`: el total de un cliente es de TODAS las sociedades del grupo (L8).
    return service.get_vista(mes, anio)


# ⚠️ ANTES de cualquier ruta con parámetro: FastAPI resuelve por ORDEN DE DECLARACIÓN y con
# `/{algo}` arriba, "exportar" matchearía como el parámetro. Ídem areas.py.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar(
    request: Request,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    service: HorasClienteService = Depends(_svc),
) -> Response:
    d = service.exportar(mes, anio, formato)
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/detalle", response_model=DetalleEmpleadoResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def detalle(
    empleado_id: UUID = Query(...),
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    service: HorasClienteService = Depends(_svc),
) -> DetalleEmpleadoResponse:
    return service.get_detalle(empleado_id, mes, anio)
