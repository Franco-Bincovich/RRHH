"""Router de Reportes — generar, historial y exportar. empresa_id: header X-Empresa-Id (empresa activa atada al reporte; "Todas" → consolidado null)."""
from typing import List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.reporte import HistorialItem, ReporteGenerarRequest, ReporteResponse
from services.reporte_export_service import ReporteExportService
from services.reporte_service import ReporteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export, limiter

router = APIRouter()
SECCION = Seccion.REPORTES


def _service() -> ReporteService:
    return ReporteService()


def _export_service() -> ReporteExportService:
    return ReporteExportService()


@router.post("/generar", response_model=ReporteResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
@limiter.limit("20/hour")  # con tipo="adhoc" llama a Claude: cada request cuesta plata
async def generar_reporte(
    request: Request,
    body: ReporteGenerarRequest,
    service: ReporteService = Depends(_service),
) -> ReporteResponse:
    generado_por = getattr(request.state, "user", {}).get("email", "Sistema")
    # Armado manual: la empresa/área del reporte salen del BODY (form), NO del header del sidebar.
    return service.generar(
        tipo=body.tipo,
        mes=body.mes,
        anio=body.anio,
        prompt=body.prompt,
        generado_por=generado_por,
        empresa_id=body.empresa_id,
        area_id=body.area_id,
        vista=body.vista,
    )


@router.get("/historial", response_model=List[HistorialItem], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_historial(
    request: Request,
    service: ReporteService = Depends(_service),
) -> List[HistorialItem]:
    empresa_id = get_empresa_id(request)
    return service.get_historial(empresa_id)


@router.get("/{reporte_id}/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_reporte(
    reporte_id: UUID,
    request: Request,
    formato: Literal["pdf", "excel"] = Query(...),
    svc: ReporteExportService = Depends(_export_service),
) -> Response:
    export = svc.build_export(reporte_id, formato, get_empresa_id(request))
    headers = {"Content-Disposition": f'attachment; filename="{export.filename}"'}
    return Response(content=export.content, media_type=export.media_type, headers=headers)
