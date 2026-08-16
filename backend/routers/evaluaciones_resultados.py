"""Router de reportes de resultados de evaluaciones (lectura). El EXPORT vive en
evaluaciones_resultados_export.py. Gate EVALUACIONES + READ
(admin + gerencia leen; mandos sin acceso). Todo cuelga de un lote: la empresa sale del header
(VISTA) y el service la valida contra la del lote —ajeno da 404, igual que inexistente; None = todas."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.evaluacion_reportes import EvaluadoListadoResponse, FichaResponse, MetricasResponse
from schemas.evaluacion_resultados import LoteListResponse, LotesBulkDelete, LotesBulkResult
from services.evaluacion_reportes_service import EvaluacionReportesService
from services.evaluacion_service import EvaluacionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
_GATE = [Depends(require_permission(Seccion.EVALUACIONES, Accion.READ))]


def _svc() -> EvaluacionReportesService:
    return EvaluacionReportesService()


@router.get("/lotes", response_model=LoteListResponse, dependencies=_GATE)
async def listar_lotes(request: Request) -> LoteListResponse:
    """Lotes (ciclos) de la empresa activa — para el selector."""
    return EvaluacionService().listar_lotes(get_empresa_id(request))


@router.delete("/lotes/{lote_id}", status_code=204,
               dependencies=[Depends(require_permission(Seccion.EVALUACIONES, Accion.WRITE))])
async def eliminar_lote(lote_id: UUID, request: Request) -> None:
    """Elimina una importación completa (CASCADE a evaluados y resultados). El _GATE del archivo
    es READ, así que este endpoint lleva su propia dependency WRITE = solo admin_rrhh. La empresa
    del lote es la autoritativa: se borra cualquier lote sin importar la empresa activa del header."""
    EvaluacionService().delete_lote(lote_id, request.state.user.get("id", "system"))


@router.post("/lotes/eliminar", response_model=LotesBulkResult,
             dependencies=[Depends(require_permission(Seccion.EVALUACIONES, Accion.WRITE))])
async def eliminar_lotes_bulk(body: LotesBulkDelete, request: Request) -> LotesBulkResult:
    """Baja múltiple (multi-selección del historial): borra varios lotes con éxito parcial —no
    aborta si uno falla— y cada baja audita por separado. Gate WRITE = solo admin_rrhh."""
    return EvaluacionService().delete_lotes_bulk(body.lote_ids, request.state.user.get("id", "system"))


@router.get("/lotes/{lote_id}/metricas", response_model=MetricasResponse, dependencies=_GATE)
async def metricas(lote_id: UUID, empresa: Optional[UUID] = Depends(get_empresa_id),
                   svc: EvaluacionReportesService = Depends(_svc)) -> MetricasResponse:
    """Resumen + brecha + sectores + competencias del ciclo, en una pasada."""
    return svc.metricas(lote_id, empresa)


@router.get("/lotes/{lote_id}/evaluados", response_model=EvaluadoListadoResponse, dependencies=_GATE)
async def evaluados(lote_id: UUID, empresa: Optional[UUID] = Depends(get_empresa_id),
                    svc: EvaluacionReportesService = Depends(_svc),
                    sector: Optional[str] = Query(None), perfil: Optional[str] = Query(None),
                    con_nota: Optional[str] = Query(None),
                    proyecto_id: Optional[UUID] = Query(None),
                    page: int = Query(1, ge=1),
                    page_size: int = Query(20, ge=1, le=100)) -> EvaluadoListadoResponse:
    """Listado filtrable y paginado de evaluados del lote."""
    return svc.listado(lote_id, empresa, sector, perfil, con_nota, proyecto_id, page, page_size)


@router.get("/lotes/{lote_id}/evaluados/{evaluado_id}/ficha", response_model=FichaResponse, dependencies=_GATE)
async def ficha(lote_id: UUID, evaluado_id: UUID, empresa: Optional[UUID] = Depends(get_empresa_id),
                svc: EvaluacionReportesService = Depends(_svc)) -> FichaResponse:
    """Ficha individual: matriz competencia × tipo de evaluador + promedio de terceros."""
    return svc.ficha(lote_id, evaluado_id, empresa)
