"""Export del listado de evaluados de un lote. Separado de evaluaciones_resultados.py, que
estaba en 80/80 — el corte que quedó pendiente en A2, cuando el endpoint se quedó sin la franja
de rate limiting por falta de línea. Ahora la tiene.

Se monta en el mismo prefijo. El orden respecto del router principal no es load-bearing acá
(este path tiene 4 segmentos y /evaluados/{evaluado_id}/ficha tiene 5, así que no colisionan),
pero se registra antes por consistencia con ausencias_tipos / empleados_catalogos."""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from services.evaluacion_reportes_service import EvaluacionReportesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
_GATE = [Depends(require_permission(Seccion.EVALUACIONES, Accion.READ))]


def _svc() -> EvaluacionReportesService:
    return EvaluacionReportesService()


@router.get("/lotes/{lote_id}/evaluados/export", dependencies=_GATE)
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar(request: Request, lote_id: UUID, empresa: Optional[UUID] = Depends(get_empresa_id),
                   svc: EvaluacionReportesService = Depends(_svc),
                   formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
                   sector: Optional[str] = Query(None), perfil: Optional[str] = Query(None),
                   con_nota: Optional[str] = Query(None),
                   proyecto_id: Optional[UUID] = Query(None)) -> Response:
    """Export del listado — mismos Query que /evaluados. `request` lo exige slowapi."""
    d = svc.exportar(lote_id, empresa, formato, sector, perfil, con_nota, proyecto_id)
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
