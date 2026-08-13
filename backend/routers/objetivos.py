"""
Router de objetivos — LECTURAS. Sección: "objetivos".
empresa_id para lecturas: X-Empresa-Id (get_empresa_id).

Las escrituras (POST/PUT/DELETE) viven en routers/objetivos_escrituras.py, montado en el
MISMO prefijo: las rutas no cambiaron. El porqué del corte está en el docstring de ese archivo.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.objetivo import ObjetivoListResponse
from services.objetivo_service import ObjetivoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.OBJETIVOS


def _svc() -> ObjetivoService:
    return ObjetivoService()


@router.get("", response_model=ObjetivoListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_objetivos(
    request: Request,
    estado:         Optional[str] = Query(None),
    responsable_id: Optional[str] = Query(None),
    prioridad:      Optional[str] = Query(None),
    service: ObjetivoService = Depends(_svc),
) -> ObjetivoListResponse:
    return service.get_all(get_empresa_id(request), estado, responsable_id, prioridad)


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_objetivos(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    estado: Optional[str] = Query(None), responsable_id: Optional[str] = Query(None), prioridad: Optional[str] = Query(None),
    service: ObjetivoService = Depends(_svc),
) -> Response:
    d = service.exportar(get_empresa_id(request), formato, estado, responsable_id, prioridad)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
