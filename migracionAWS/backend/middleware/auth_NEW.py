"""
Middleware de autenticación JWT con verificación propia — reemplaza el JWKS de Supabase.

DESTINO: backend/middleware/auth.py (reemplaza el actual, 143 líneas).

QUÉ CAMBIA vs. el middleware actual
-----------------------------------
Hoy (middleware/auth.py:35) verifica cada JWT contra el JWKS público del proyecto Supabase:

    _JWKS_URL = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    _jwks_client = jwt.PyJWKClient(_JWKS_URL, timeout=5)   # ES256, ellos firman

Acá se verifica con `verify_token` de auth_service_NEW: HS256 contra settings.jwt_secret —
nosotros firmamos y verificamos. Se va el PyJWKClient, se va el refetch del JWKS cada 5
min por proceso, y se va la dependencia de red en el camino de auth.

⚠️ ESTE ARCHIVO ES EL QUE LIBERA `settings.supabase_url`. Es su ÚLTIMO consumidor fuera de
la capa de datos: mientras el middleware siga acá, supabase_url sigue viva aunque los
repositories ya estén 100% en RDS. Recién al activar este middleware se puede deprecar del
todo (ver settings_ADD.md y README_AUTH.md).

MEJORA GRATIS: el middleware actual hace un `.table("users").select("rol")` contra Supabase
en CADA request autenticado para resolver el rol (línea 127). Acá el rol viaja en el token,
así que ese query desaparece — una llamada de red menos por request. Contrapartida: un
cambio de rol no impacta hasta que el access token expire (máx. 60 min) o el usuario haga
refresh (que sí re-lee el rol de la base). El actual lo veía al instante. Es el tradeoff
normal de los JWT; si no se acepta, hay que volver a leer el rol por request.
"""
import re
from typing import Optional
from uuid import UUID

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from services.auth_service_NEW import verify_token
from utils.errors import AppError

# Rutas sin auth. Se conservan las 4 del middleware actual + /docs.
# ⚠️ /api/integraciones/google/callback: pública porque Google redirige ahí sin el header.
# No la saques al portar.
PUBLIC_ROUTES = frozenset([
    "/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/integraciones/google/callback",
    "/docs",
    "/openapi.json",
])

# Los links públicos de assessment (token en la URL, sin login). Del middleware actual: si
# se pierden, se rompen los formularios que ya están circulando.
_ASSESSMENT_FE_RE = re.compile(r"^/assessment/[^/]+$")
_ASSESSMENT_API_RE = re.compile(r"^/api/assessment/evaluacion/[^/]+(/submit)?$")


def _is_public(path: str) -> bool:
    """True si la ruta no requiere autenticación."""
    return (
        path in PUBLIC_ROUTES
        or bool(_ASSESSMENT_FE_RE.match(path))
        or bool(_ASSESSMENT_API_RE.match(path))
    )


def _extract_token(request: Request) -> Optional[str]:
    """Saca el token del header Authorization o, si no está, de la cookie access_token.

    ⚠️ EL FALLBACK A COOKIE ES NUEVO Y NO ES GRATIS. RRHH hoy es header-only: el frontend
    manda `Authorization: Bearer` y NO hay una sola cookie en el backend (verificado: cero
    `set_cookie` en routers/ y middleware/). Aceptar la cookie abre CSRF, del que el
    esquema Bearer estaba inmune por construcción — el browser adjunta cookies solo, un
    header no. Si esta rama se activa hace falta, como mínimo, SameSite=Strict + un token
    CSRF en las mutaciones. Mientras el frontend no setee la cookie, esta rama es código
    muerto: se puede borrar y quedarse solo con el header.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token")


def _401(code: str) -> JSONResponse:
    """Respuesta 401 con el formato de error de RRHH ({error, message, code})."""
    return JSONResponse(
        status_code=401,
        content={"error": True, "message": "No autorizado", "code": code},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        """Valida el JWT y expone user/empresa_id en request.state.

        Deja pasar OPTIONS (preflight CORS) y las rutas públicas. Todo lo demás exige un
        access token válido. Fail-closed: cualquier fallo es 401 genérico.
        """
        if request.method == "OPTIONS":
            return await call_next(request)
        if _is_public(request.url.path):
            return await call_next(request)

        token = _extract_token(request)
        if not token:
            return _401("MISSING_TOKEN")

        # verify_token levanta AppError 401; acá se traduce a JSONResponse porque el
        # middleware corre FUERA del exception handler de FastAPI (que atiende AppError en
        # los routers). Si se deja propagar, sale un 500 sin headers CORS.
        try:
            payload = verify_token(token)
        except AppError:
            return _401("INVALID_TOKEN")

        # Un refresh token NO autoriza requests: sin este check, el refresh (30 días) valdría
        # como access (60 min) y el rate limit del login dejaría de importar.
        if payload.get("type") != "access":
            return _401("INVALID_TOKEN")

        user_id = payload.get("sub")
        if not user_id:
            return _401("INVALID_TOKEN")

        # El rol sale del TOKEN, no de la base: el middleware actual hacía un SELECT por
        # request (ver docstring del módulo). Misma forma de request.state.user —
        # {"id", "rol"} — que leen utils/permisos.py y los 142 endpoints gateados.
        request.state.user = {"id": user_id, "rol": payload.get("rol")}

        # Empresa activa: idéntico al actual (middleware/auth.py:133-142). Header ausente o
        # "todas" → None = vista consolidada. Se conserva la deuda conocida: no verifica que
        # el UUID exista en la tabla empresas (higiene de input, baja prioridad).
        empresa_header = request.headers.get("X-Empresa-Id", "").strip()
        request.state.empresa_id = None
        if empresa_header and empresa_header != "todas":
            try:
                UUID(empresa_header)
                request.state.empresa_id = empresa_header
            except ValueError:
                request.state.empresa_id = None

        return await call_next(request)
