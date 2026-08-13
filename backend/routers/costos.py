"""
Router de costos de personal — LECTURAS.
Rutas protegidas por AuthMiddleware (requieren JWT válido).
empresa_id: header X-Empresa-Id (get_empresa_id). None = consolidado.
Las escrituras (POST de nómina y presupuesto) viven en costos_escrituras.py, separadas por
límite de líneas; el porqué de ese corte y no otro está en el docstring de aquel módulo.
"""
from typing import List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.costo import DashboardCostosResponse, HistorialSalarialItem, NominaResponse
from services.costo_service import CostoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.COSTOS


def _service() -> CostoService:
    return CostoService()


@router.get("/dashboard", response_model=DashboardCostosResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_dashboard(
    request: Request,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    service: CostoService = Depends(_service),
) -> DashboardCostosResponse:
    return service.get_dashboard_costos(mes, anio, get_empresa_id(request))


@router.get("/nomina", response_model=List[NominaResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_nomina(
    request: Request,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    service: CostoService = Depends(_service),
) -> List[NominaResponse]:
    return service.get_nomina_mes(mes, anio, get_empresa_id(request))


@router.get("/nomina/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_nomina(
    request: Request,
    mes: int = Query(..., ge=1, le=12),
    anio: int = Query(..., ge=2000, le=2100),
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    service: CostoService = Depends(_service),
) -> Response:
    """Export de la nómina — mismos Query que el listado. `request` lo exige slowapi."""
    d = service.exportar(mes, anio, get_empresa_id(request), formato)
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/nomina/empleado/{empleado_id}", response_model=List[HistorialSalarialItem], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_historial_salarial(
    request: Request,
    empleado_id: UUID,
    service: CostoService = Depends(_service),
) -> List[HistorialSalarialItem]:
    """Serie salarial del empleado para su legajo, del período más reciente al más viejo.

    Gateado por Seccion.COSTOS aunque se consuma desde la ficha (que está bajo EMPLEADOS): el
    sueldo es un dato de costos, y hoy no existe un rol con acceso a una sección y no a la
    otra, pero los roles cambian y este endpoint no se va a volver a mirar. La barrera de
    empresa sobre el empleado la aplica el service.
    """
    return service.get_historial_salarial(empleado_id, get_empresa_id(request))
