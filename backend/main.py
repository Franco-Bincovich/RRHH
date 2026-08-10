"""
HR Karstec — RRHH
Punto de entrada de la aplicación FastAPI.
Solo configuración de la app — sin lógica de negocio.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import settings
from middleware.auth import AuthMiddleware
from middleware.error_handler import global_error_handler
from middleware.security_headers import SecurityHeadersMiddleware
from utils.errors import AppError
from registro_routers import registrar
from utils.rate_limit import limiter, rate_limit_handler
app = FastAPI(
    title="HR Karstec API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
# SlowAPIMiddleware aplica el baseline (default_limits del limiter) a todo endpoint SIN
# decorador propio; los decorados los saltea y los resuelve su decorador. Las franjas
# específicas viven en cada router. Ver utils/rate_limit.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Middlewares — orden de ejecución al recibir un request:
#   CORS (más externo) → SecurityHeaders → SlowAPI → Auth (más interno).
# add_middleware hace prepend, así que el último agregado es el más externo.
# SlowAPI va DENTRO de CORS para que el 429 salga con headers CORS (si no, el front lo ve como
# error de red y no puede leer el código), y FUERA de Auth para que el límite proteja también
# la verificación del JWT: el fetch del JWKS y el lookup en `users` corren ahí adentro.
app.add_middleware(AuthMiddleware)             # se ejecuta ÚLTIMO (más interno)
app.add_middleware(SlowAPIMiddleware)          # 3°
app.add_middleware(SecurityHeadersMiddleware)  # 2°
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Empresa-Id"],
)  # se ejecuta PRIMERO (más externo)
# AppError registrado por TIPO específico → lo atiende el ExceptionMiddleware interno (dentro
# de CORS), así la respuesta de error reatraviesa el CORSMiddleware y sale con headers CORS.
app.add_exception_handler(AppError, global_error_handler)
# Catch-all de 500 inesperados: queda sobre Exception (ServerErrorMiddleware, fuera de CORS).
app.add_exception_handler(Exception, global_error_handler)

# ── Health check (ruta pública) ────────────────────────────────────────────────
# EXENTO del rate limiting a propósito: lo consultan los health checks de la plataforma (hoy
# Vercel, mañana el target group del ALB), todos desde la misma IP y con alta frecuencia.
# Limitarlo haría que el balanceador marque la instancia como caída y la saque de rotación.
@app.get("/health")
@limiter.exempt
async def health_check():
    return {"status": "ok", "env": settings.app_env}

# ── Routers ───────────────────────────────────────────────────────────────────
# El inventario vive en `registro_routers.py` (ver su encabezado). Acá queda la llamada.
registrar(app)
