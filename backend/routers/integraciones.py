"""
Router de integraciones por usuario.
Gestiona Google OAuth y API keys (Anthropic).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from config.settings import settings
from schemas.integracion import ApiKeyUpdate, IntegracionResponse
from services.integracion_service import IntegracionService
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.INTEGRACIONES


def _service() -> IntegracionService:
    return IntegracionService()


@router.get("", response_model=list[IntegracionResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_integraciones(request: Request) -> list[IntegracionResponse]:
    user_id: str = request.state.user["id"]
    return _service().get_integraciones(user_id)


@router.get("/google/auth", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def google_auth_url(request: Request) -> dict[str, str]:
    user_id: str = request.state.user["id"]
    auth_url = _service().init_google_oauth(user_id)
    return {"auth_url": auth_url}


# Público (sin auth, ver middleware/auth.py::PUBLIC_ROUTES): lo invoca Google, no el front.
# Cada llamada dispara un intercambio de token contra Google con `state` = user_id crudo.
# `request` no lo usa el handler; lo exige slowapi para poder decorar.
@router.get("/google/callback")
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    state: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    if error or not code:
        return RedirectResponse(url=f"{settings.frontend_url}/configuracion?oauth=error")
    try:
        _service().handle_google_callback(user_id=state, code=code)
    except Exception:
        return RedirectResponse(url=f"{settings.frontend_url}/configuracion?oauth=error")
    return RedirectResponse(url=f"{settings.frontend_url}/configuracion?oauth=google")


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


@router.delete("/{tipo}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def disconnect(tipo: str, request: Request) -> None:
    user_id: str = request.state.user["id"]
    _service().disconnect(user_id, tipo)
