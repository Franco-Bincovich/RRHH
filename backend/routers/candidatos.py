"""
Router de candidatos — LECTURAS (listado paginado, export y la URL del CV).

Las escrituras (baja, cambio de etapa, asignación de vacante) viven en
`candidatos_escrituras.py`, montado en el MISMO prefijo: las rutas no cambiaron. El porqué del
corte está en el docstring de ese archivo.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.candidato import CandidatosPaginaResponse
from services.candidato_service import CandidatoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.CANDIDATOS

# 🔴 El MISMO tipo en listado y export (Bloque B): dos declaraciones divergen y el archivo sale
# con filas que la pantalla no muestra. `sin_clasificar` es un VALOR, no la ausencia de filtro.
Clasificacion = Literal["relevante", "dudoso", "no_relevante", "sin_clasificar"]


def _candidato_svc() -> CandidatoService:
    return CandidatoService()


@router.get("", response_model=CandidatosPaginaResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def listar_candidatos(
    request: Request, sin_vacante: bool = Query(False),
    clasificacion: Optional[Clasificacion] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: CandidatoService = Depends(_candidato_svc)
) -> CandidatosPaginaResponse:
    return service.listar_todos_candidatos(get_empresa_id(request), sin_vacante, clasificacion,
                                           page, page_size)


# ⚠️ ANTES de /{id}/…: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_candidatos(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), sin_vacante: bool = Query(False), clasificacion: Optional[Clasificacion] = Query(None), service: CandidatoService = Depends(_candidato_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, sin_vacante, clasificacion)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}/cv-url", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def candidato_cv_url(
    id: UUID, request: Request, service: CandidatoService = Depends(_candidato_svc)
) -> dict:
    return {"url": service.cv_signed_url(str(id), get_empresa_id(request))}
