"""
Router de autenticación — login, logout, refresh.
Rate limiting: login 5/minuto y refresh 20/minuto por IP. Las dos son públicas (sin token),
así que son la superficie de fuerza bruta del sistema. El limiter vive en utils/rate_limit.py.
"""
from fastapi import APIRouter, Depends, Request

from schemas.auth import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
from services.auth_service import AuthService
from utils.errors import AppError
from utils.rate_limit import limiter

router = APIRouter()


def _get_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AppError("No autorizado", "MISSING_TOKEN", 401)
    return auth[7:]


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    service: AuthService = Depends(AuthService),
) -> LoginResponse:
    return service.login(body.username, body.password)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    service: AuthService = Depends(AuthService),
) -> None:
    token = _get_token(request)
    service.logout(request.state.user["id"], token)


# Pública igual que login: permitía reintentar refresh tokens sin costo. 20/min tolera varias
# pestañas refrescando a la vez (el front solo refresca al expirar el access token).
@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    service: AuthService = Depends(AuthService),
) -> RefreshResponse:
    return service.refresh_token(body.refresh_token)
