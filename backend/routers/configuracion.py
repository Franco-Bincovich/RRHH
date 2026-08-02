"""
Router de configuración de reglas de negocio (migración 085).

Router PROPIO y no un par de endpoints colgados de integraciones: aquel está en 77/80 y, más
de fondo, no es lo mismo — integraciones son credenciales POR USUARIO y esto son reglas POR
EMPRESA, con otra sección de permisos y otro dueño.

🔒 Gate: Seccion.CONFIGURACION, que NO es VACACIONES ni AUSENCIAS. mandos_medios tiene WRITE
en esas dos, y cargar una licencia no es lo mismo que cambiar la regla con la que se calculan
todas: reusar aquellas secciones le daría a mandos_medios la escala entera.

No hay barrera de empresa que aplicar: ningún endpoint recibe un id de recurso de afuera. El
recurso ES la empresa del request, y en las escrituras viene de require_empresa_id.
"""
from fastapi import APIRouter, Depends, Request

from schemas.configuracion import (
    ConfiguracionResponse, EscalaResponse, EscalaUpdate,
    ParametrosResponse, ParametrosUpdate,
)
from services.configuracion_service import ConfiguracionService
from utils.empresa import get_empresa_id, require_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.CONFIGURACION

_READ = Depends(require_permission(SECCION, Accion.READ))
_WRITE = Depends(require_permission(SECCION, Accion.WRITE))


def _service() -> ConfiguracionService: return ConfiguracionService()


@router.get("", response_model=ConfiguracionResponse, dependencies=[_READ])
async def get_configuracion(
    request: Request, service: ConfiguracionService = Depends(_service),
) -> ConfiguracionResponse:
    return service.get_configuracion(get_empresa_id(request))


@router.put("/parametros", response_model=ParametrosResponse, dependencies=[_WRITE])
async def set_parametros(
    body: ParametrosUpdate, request: Request,
    service: ConfiguracionService = Depends(_service),
) -> ParametrosResponse:
    return service.set_parametros(require_empresa_id(request), body)


@router.put("/escala", response_model=EscalaResponse, dependencies=[_WRITE])
async def set_escala(
    body: EscalaUpdate, request: Request,
    service: ConfiguracionService = Depends(_service),
) -> EscalaResponse:
    return service.set_escala(require_empresa_id(request), body)
