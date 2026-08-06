"""
Credenciales de terceros por usuario (API keys de Anthropic y Zernio).

Separado de `integraciones.py` por límite de líneas: aquel estaba en 77/80. Se movieron estos
dos —los endpoints más aislados del módulo: lo único que comparten con el resto es
`ApiKeyUpdate`— y NO los de Google: `google_callback` es la única ruta pública del módulo y su
nombre de módulo está fijado por `tests/test_rate_limit.py`, que lee
`limiter._route_limits["routers.integraciones.google_callback"]`.

Se monta desde `integraciones.py` con `router.include_router(...)`: así el prefijo
`/api/integraciones` sigue declarado en un solo lugar y `main.py` no se toca.
"""
from fastapi import APIRouter, Depends, Request

from schemas.integracion import ApiKeyUpdate, IntegracionResponse
from services.integracion_service import IntegracionService
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.INTEGRACIONES


def _service() -> IntegracionService:
    return IntegracionService()


@router.post("/anthropic", response_model=IntegracionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def save_anthropic_key(
    request: Request,
    body: ApiKeyUpdate,
) -> IntegracionResponse:
    user_id: str = request.state.user["id"]
    return _service().save_anthropic_key(user_id, body.api_key)


@router.post("/zernio", response_model=IntegracionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def save_zernio_key(request: Request, body: ApiKeyUpdate) -> IntegracionResponse:
    user_id: str = request.state.user["id"]
    return _service().save_zernio_key(user_id, body.api_key)
