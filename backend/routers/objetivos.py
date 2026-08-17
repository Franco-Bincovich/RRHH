"""
Router de objetivos — LECTURAS. Sección: "objetivos".
empresa_id para lecturas: X-Empresa-Id (get_empresa_id).

Las escrituras (POST/PUT/DELETE) viven en routers/objetivos_escrituras.py, y el vocabulario
cerrado de `tipo` en routers/objetivos_catalogos.py. Los tres se montan en el MISMO prefijo: las
rutas no cambian. El porqué de cada corte está en el docstring de esos archivos.

🔴 LOS SEIS FILTROS SE DECLARAN DOS VECES —una en el listado y otra en el export— Y ESO ES A
PROPÓSITO, no una duplicación que quedó. La alternativa era una dependencia común
(`Depends(_filtros)`) que los declarara una sola vez, y **eso apagaría el barrido de paridad**:
`tests/test_paridad_list_export.py` lee `route.dependant.query_params`, que contiene los params
PROPIOS de la ruta y no los de sus sub-dependencias. Con un `Depends`, los dos endpoints
reportarían CERO filtros, la comparación entre listado y export se cumpliría por vacío y el
módulo saldría del barrido sin que ningún test se ponga en rojo. Se prefiere repetir la
declaración —que es lo que hace todo el resto del repo— antes que un verde vacuo.
Lo que NO está duplicado es la traducción: los dos arman el MISMO `ObjetivosFiltros`, y de ahí en
adelante hay un solo camino hasta la query.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.objetivo import ObjetivoListResponse, TipoObjetivo
from schemas.objetivo_filtros import ObjetivosFiltros
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
    estado: Optional[str] = Query(None), responsable_id: Optional[str] = Query(None), prioridad: Optional[str] = Query(None),
    # `tipo` va tipado con el Literal y los otros dos como `str` libre. La asimetría es la del
    # dato: `tipo` tiene vocabulario cerrado, así que un valor inventado es un 422 de FastAPI y no
    # una consulta que devuelve cero. `periodicidad` y `area` son texto que RRHH escribe.
    tipo: Optional[TipoObjetivo] = Query(None), periodicidad: Optional[str] = Query(None), area: Optional[str] = Query(None),
    service: ObjetivoService = Depends(_svc),
) -> ObjetivoListResponse:
    return service.get_all(get_empresa_id(request), ObjetivosFiltros(
        estado=estado, responsable_id=responsable_id, prioridad=prioridad,
        tipo=tipo, periodicidad=periodicidad, area=area))


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_objetivos(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    estado: Optional[str] = Query(None), responsable_id: Optional[str] = Query(None), prioridad: Optional[str] = Query(None),
    tipo: Optional[TipoObjetivo] = Query(None), periodicidad: Optional[str] = Query(None), area: Optional[str] = Query(None),
    service: ObjetivoService = Depends(_svc),
) -> Response:
    d = service.exportar(get_empresa_id(request), formato, ObjetivosFiltros(
        estado=estado, responsable_id=responsable_id, prioridad=prioridad,
        tipo=tipo, periodicidad=periodicidad, area=area))
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
