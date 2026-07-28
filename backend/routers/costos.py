"""
Router de costos de personal.
Rutas protegidas por AuthMiddleware (requieren JWT válido).
empresa_id para lecturas: header X-Empresa-Id (get_empresa_id).
empresa_id para escrituras: heredado del empleado/área — NO se pide explícito.
"""
from typing import List, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.costo import (
    DashboardCostosResponse, NominaCreate, NominaResponse,
    PresupuestoCreate, PresupuestoResponse,
)
from services.costo_service import CostoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

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
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
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


@router.post("/nomina", response_model=NominaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def post_nomina(
    request: Request,
    body: NominaCreate,
    service: CostoService = Depends(_service),
) -> NominaResponse:
    u = request.state.user
    return service.cargar_nomina(body, get_empresa_id(request), u.get("id", "system"), u.get("rol"))


@router.post("/presupuesto", response_model=PresupuestoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def post_presupuesto(
    request: Request,
    body: PresupuestoCreate,
    service: CostoService = Depends(_service),
) -> PresupuestoResponse:
    return service.set_presupuesto_area(body, get_empresa_id(request), request.state.user.get("id", "system"))
