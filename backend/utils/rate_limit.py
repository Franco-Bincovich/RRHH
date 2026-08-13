"""
Rate limiting: el limiter único de la app, su key_func y el handler del 429.

Antes el Limiter vivía en `routers/auth.py` y `main.py` lo importaba desde ahí — un router
configurando la app, al revés del flujo normal. Ahora vive acá y `routers/auth.py` lo importa
como cualquier otro consumidor.

Cómo se reparten las franjas:
  · El BASELINE global lo aplica `SlowAPIMiddleware` con los `default_limits` de este limiter.
    Cubre todos los endpoints sin decorador propio, sin tocar un solo router.
  · Las franjas específicas van con `@limiter.limit(...)` / `@limiter.shared_limit(...)` en cada
    endpoint. Un endpoint decorado IGNORA el baseline (`override_defaults=True` es el default de
    `limiter.limit`), así que el decorador reemplaza, no se suma.

slowapi no permite limitar un router entero: `limit()` es un decorador de función, no una
`Depends`, así que no entra por `include_router(dependencies=[...])`. Y un límite que dependa
del path tampoco se puede expresar en `default_limits` (el callable solo recibe la key ya
calculada, nunca el request). Por eso las franjas son endpoint por endpoint.

Además, `limit()` EXIGE que el endpoint tenga un parámetro llamado `request`. Si falta, no
falla en runtime: revienta al importar el módulo y la app no levanta. Por eso varios handlers
reciben `request: Request` sin usarlo.

FRANJAS (de más restrictiva a menos):

  público sin auth   GET  /api/assessment/evaluacion/{token}      10/min
                     POST /api/assessment/evaluacion/{token}/submit 5/min
                     GET  /api/integraciones/google/callback      10/min
  credenciales       POST /api/auth/login                          5/min   (ya existía)
                     POST /api/auth/refresh                       20/min
                     POST /api/usuarios/cambiar-password          10/hora
  import             los 5 endpoints de import        10/hora compartido (scope="import")
  export             los endpoints de export + reportes/generar-export
                                       100/hora compartido POR USUARIO (scope="export")
  costo externo      POST /api/reportes/generar                   20/hora
  /health            EXENTO (lo consultan los health checks de la plataforma)
  todo lo demás      BASELINE, abajo

⚠️ DOS exports quedan FUERA de la franja y corren bajo el baseline: `objetivos.py` e
`inventario_items.py` (79 líneas cada uno). Sumarles el decorador los pasaba del límite de 80
del router. **Cuando se dividan, agregarles el decorador `@limite_export` de este módulo.**
Eran TRES: `evaluaciones_resultados.py` se cerró al dividir su router — el export se mudó a
`routers/evaluaciones_resultados_export.py`, que sí lleva la franja. La lista de pendientes
la fija `tests/test_rate_limit.py::TestFranjaExport` / `test_los_dos_pendientes_siguen_sin_decorador`;
si movés uno de acá, movelo también allá (el test lo explica: borrarlo en vez de moverlo deja
la aserción vacua).

⚠️ DOS LÍMITES REALES DE ESTA IMPLEMENTACIÓN — leerlos antes de confiar en los números:

  1. **El store es por proceso.** El default `memory://` guarda los contadores en la memoria de
     la instancia. En serverless cada cold start arranca en cero, y con N instancias vivas el
     límite efectivo es N×. Para que los límites sean un control y no una mitigación parcial
     hace falta un store compartido: `RATE_LIMIT_STORAGE_URI=redis://...`. El enchufe está
     puesto; conectarlo es decisión de infraestructura.

  2. **La key por defecto es la IP, y detrás de un proxy la IP depende de `TRUSTED_PROXY_HOPS`.**
     Si ese valor queda mal, el efecto no es "el límite no anda": es que todo el tráfico
     colapsa en un solo contador y el equipo entero se queda afuera. Ver `client_ip`.
     La franja de export es la excepción: usa `usuario_o_ip` y no depende de ese valor.
"""
import time

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from config.settings import settings
from middleware.error_handler import global_error_handler
# Re-export: `client_ip` lo importan `routers/horas_publico.py` y los tests desde acá.
from utils._rate_limit_keys import client_ip, usuario_o_ip  # noqa: F401
from utils.errors import AppError
from utils.logger import logger

# Baseline para todo endpoint sin decorador propio. Alto a propósito: el objetivo no es
# racionar a un equipo de 3 personas, es cortar un loop roto del front o un scraper con un
# token robado antes de que agote la base.
BASELINE = "300/minute"

_MENSAJE_429 = "Demasiadas solicitudes. Esperá un momento y volvé a intentar."


# ⚠️ headers_enabled se deja en False (el default) A PROPÓSITO, y no es un olvido.
# Con headers_enabled=True, slowapi 0.1.9 rompe el camino de ÉXITO de todo endpoint decorado:
# tras un request OK intenta inyectar los headers en `kwargs.get("response")`, que es None
# salvo que el endpoint declare un parámetro `response: Response`. Con None levanta
# "parameter `response` must be an instance of starlette.responses.Response", que el handler
# global convierte en 500. O sea: cada endpoint limitado devolvería 500 al responder bien.
# Evitarlo exigiría agregar `response: Response` a las 19 firmas decoradas. En vez de eso, el
# único header que importa —Retry-After— lo calcula rate_limit_handler.
limiter = Limiter(
    key_func=client_ip,
    default_limits=[BASELINE],
    storage_uri=settings.rate_limit_storage_uri,
)


# La franja de export, EN UN SOLO LUGAR: los 26 endpoints aplican este decorador en vez de
# repetir la cadena `shared_limit(...)`, que es la forma en que dos exports terminan con límites
# distintos sin que nadie lo decida. Reusar UN objeto decorador entre 26 funciones es seguro:
# slowapi resuelve el nombre de registro (`f"{func.__module__}.{func.__name__}"`) y el key_func
# DENTRO del decorador, una vez por aplicación (slowapi/extension.py:663-664).
# 100/hora POR USUARIO reemplaza a 30/hora por IP: con 10 empresas, 26 exports y el modo
# consolidado, un cierre de mes normal agotaba los 30 en minutos.
limite_export = limiter.shared_limit("100/hour", scope="export", key_func=usuario_o_ip)


def _retry_after(request: Request) -> int | None:
    """Segundos hasta que la ventana se libere, o None si no se puede determinar.

    Sale de `request.state.view_rate_limit`, que slowapi deja seteado con el límite incumplido
    justo antes de levantar la excepción: `(RateLimitItem, [partes de la key])`.
    """
    try:
        limite, partes = request.state.view_rate_limit
        reset_en, _restantes = limiter.limiter.get_window_stats(limite, *partes)
        return max(0, int(1 + reset_en - time.time()))
    except Exception:
        return None


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Devuelve el 429 con el formato de error del repo, no con el default de slowapi.

    El handler que trae slowapi responde `{"error": "Rate limit exceeded: ..."}`: `error` como
    string en vez de bool, y sin `message` ni `code`. El front espera el contrato de `AppError`
    en TODA respuesta de error, así que una excepción a ese contrato es un bug esperando a que
    alguien parsee un 429. El body lo arma `global_error_handler`, el mismo que produce todos
    los demás errores de la app — así no puede divergir del resto aunque el formato cambie.

    Agrega `Retry-After` (segundos), que es lo que le dice al cliente cuándo reintentar. Si no
    se puede calcular, el 429 sale igual sin el header: perder un header es aceptable,
    convertir el 429 en un 500 no.

    Args:
        request: Request que superó el límite.
        exc: La excepción de slowapi, que trae el límite incumplido en `detail`.

    Returns:
        Response 429 con `{error, message, code}` y, si se pudo calcular, `Retry-After`.
    """
    logger.warning(
        "Rate limit excedido",
        extra={"path": request.url.path, "limite": str(exc.detail), "ip": client_ip(request)},
    )
    response = await global_error_handler(
        request, AppError(_MENSAJE_429, "RATE_LIMIT_EXCEEDED", 429)
    )
    segundos = _retry_after(request)
    if segundos is not None:
        response.headers["Retry-After"] = str(segundos)
    return response
