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
                                                      30/hora compartido (scope="export")
  costo externo      POST /api/reportes/generar                   20/hora
  /health            EXENTO (lo consultan los health checks de la plataforma)
  todo lo demás      BASELINE, abajo

⚠️ DOS exports quedan FUERA de la franja y corren bajo el baseline: `objetivos.py` e
`inventario_items.py` (79 líneas cada uno). Sumarles el decorador los pasaba del límite de 80
del router. **Cuando se dividan, agregarles `shared_limit("30/hour", scope="export")`.**
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

  2. **La key es la IP, y detrás de un proxy la IP depende de `TRUSTED_PROXY_HOPS`.** Si ese
     valor queda mal, el efecto no es "el límite no anda": es que todo el tráfico colapsa en
     un solo contador y el equipo entero se queda afuera. Ver `client_ip`.
"""
import time

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from config.settings import settings
from middleware.error_handler import global_error_handler
from utils.errors import AppError
from utils.logger import logger

# Baseline para todo endpoint sin decorador propio. Alto a propósito: el objetivo no es
# racionar a un equipo de 3 personas, es cortar un loop roto del front o un scraper con un
# token robado antes de que agote la base.
BASELINE = "300/minute"

_MENSAJE_429 = "Demasiadas solicitudes. Esperá un momento y volvé a intentar."


def client_ip(request: Request) -> str:
    """IP del cliente a usar como clave del contador, resistente a falsificación.

    `X-Forwarded-For` se construye de izquierda a derecha: cada proxy AGREGA la IP de quien le
    habló. Por eso las entradas de la DERECHA las escribió nuestra propia infraestructura y son
    confiables, y las de la IZQUIERDA las pudo inventar el cliente. Con N capas de proxy
    confiables adelante, la IP real del cliente es `hops[-N]`.

    Ejemplo con Vercel (N=1): si el cliente manda `X-Forwarded-For: 1.2.3.4` falsificado, el
    edge appendea la IP real de la conexión y al app le llega `"1.2.3.4, 200.0.0.9"`.
    `hops[-1]` = `200.0.0.9`: el valor inyectado se descarta solo, sin lógica extra.

    Si el header trae MENOS saltos de los declarados —mala configuración, o alguien pegándole
    directo al origin sin pasar por el proxy— no se adivina cuál sirve: se cae a la IP de la
    conexión, que es lo único que el cliente no puede falsificar. Con `trusted_proxy_hops=0`
    (local, sin proxy) el header se ignora por completo.

    NO usar `slowapi.util.get_ipaddr` para esto: busca el header `"X_FORWARDED_FOR"` con
    guiones bajos, que no es un nombre de header HTTP válido. La búsqueda de Starlette es
    case-insensitive pero no equipara `_` con `-`, así que esa rama nunca se ejecuta y la
    función termina devolviendo siempre `request.client.host`, en silencio.

    Args:
        request: Request entrante.

    Returns:
        La IP a usar como clave. "127.0.0.1" si no hay ninguna forma de determinarla.
    """
    hops_confiables = settings.trusted_proxy_hops
    if hops_confiables > 0:
        hops = [h.strip() for h in request.headers.get("X-Forwarded-For", "").split(",") if h.strip()]
        if len(hops) >= hops_confiables:
            return hops[-hops_confiables]
    return request.client.host if request.client else "127.0.0.1"


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
