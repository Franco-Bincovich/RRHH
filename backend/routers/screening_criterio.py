"""
El criterio configurable del clasificador de CVs (migración 100).

Separado de `routers/screening.py` cuando entró la corrección manual: aquel estaba en 75/80 y el
endpoint nuevo no entraba. **Las URLs no cambiaron** — este router se monta en
`/api/screening/criterio`, así que `GET ""` sigue siendo `GET /api/screening/criterio`.

El corte quedó por naturaleza y no por tamaño: allá viven las ACCIONES sobre candidatos
(`Seccion.CANDIDATOS`), acá la CONFIGURACIÓN por empresa (`Seccion.CONFIGURACION`, la misma que
la escala de vacaciones). mandos_medios no toca ninguna de las dos.

🔴 Sin barrera de empresa que aplicar: ningún endpoint recibe un id de recurso de afuera. El
recurso ES la empresa del request, y en las escrituras viene de `require_empresa_id`.
"""
from fastapi import APIRouter, Depends, Request

from schemas.screening import ScreeningCriterioResponse, ScreeningCriterioUpdate
from services.screening_config_service import ScreeningConfigService
from utils.empresa import get_empresa_id, require_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()

_CFG_READ = Depends(require_permission(Seccion.CONFIGURACION, Accion.READ))
_CFG_WRITE = Depends(require_permission(Seccion.CONFIGURACION, Accion.WRITE))


def _config() -> ScreeningConfigService: return ScreeningConfigService()


@router.get("", response_model=ScreeningCriterioResponse, dependencies=[_CFG_READ])
async def get_criterio(
    request: Request, service: ScreeningConfigService = Depends(_config),
) -> ScreeningCriterioResponse:
    return service.get_criterio(get_empresa_id(request))


@router.put("", response_model=ScreeningCriterioResponse, dependencies=[_CFG_WRITE])
async def set_criterio(
    body: ScreeningCriterioUpdate, request: Request,
    service: ScreeningConfigService = Depends(_config),
) -> ScreeningCriterioResponse:
    return service.set_criterio(require_empresa_id(request), body)


@router.post("/restaurar", response_model=ScreeningCriterioResponse,
             dependencies=[_CFG_WRITE])
async def restaurar_criterio(
    request: Request, service: ScreeningConfigService = Depends(_config),
) -> ScreeningCriterioResponse:
    """Vuelve a heredar el criterio global: borra la fila propia de la empresa."""
    return service.restaurar_defaults(require_empresa_id(request))
