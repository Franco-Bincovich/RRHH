"""
Las dos funciones que deciden CONTRA QUÉ CLAVE cuenta el rate limit.

Salieron de `utils/rate_limit.py` cuando ese archivo pasó su límite de 200 líneas al sumarse la
franja de export por usuario. El corte no es arbitrario: acá vive una sola pregunta —"¿quién es
el que está pidiendo?"— y allá quedan el limiter, las franjas y el handler del 429.

🔴 ES LA PIEZA DONDE UN ERROR NO SE VE COMO UN TEST ROJO. Una clave mal calculada no rompe
nada visible: junta en un mismo contador a gente que no lo comparte, y el síntoma es "el
sistema me devuelve 429 y no hice nada". Por eso las dos funciones tienen tests propios sobre
Requests fabricados (`tests/test_rate_limit.py`), no solo cobertura indirecta.

`rate_limit.py` las RE-EXPORTA, así que los callers de afuera (`routers/horas_publico.py`, los
tests) siguen importándolas de donde siempre. Molde: `middleware/auth.py`, que re-exporta
`PUBLIC_ROUTES` por la misma razón.
"""
from fastapi import Request

from config.settings import settings


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


def usuario_o_ip(request: Request) -> str:
    """Clave del contador para franjas de usuarios AUTENTICADOS: el user_id, no la IP.

    🔴 POR QUÉ NO ALCANZA LA IP. El equipo de RRHH son 3 personas detrás de UNA sola IP de
    oficina: con `client_ip` comparten un contador y la primera que exporta se lleva la cuota de
    las tres. No es hipotético — el barrido de la sesión de escala se quedó sin cuota a mitad de
    camino y devolvió 429 en la mitad de los exports. Con el user_id cada operador tiene la suya,
    y el límite además queda INDEPENDIENTE de `TRUSTED_PROXY_HOPS`, la variable que más fácil
    queda mal en el cutover a AWS.

    🔑 SIRVE ACÁ Y NO EN EL BASELINE, y la razón es el ORDEN DE EJECUCIÓN: `SlowAPIMiddleware`
    corre POR FUERA de `AuthMiddleware` (ver `main.py`), así que cuando el baseline calcula su
    clave todavía no existe `request.state.user`. El decorador envuelve a la función del
    endpoint y se evalúa DESPUÉS de todo el middleware, con el usuario ya seteado. Por eso este
    key_func va por decorador y NUNCA como key_func global del `Limiter`.

    FALLBACK A LA IP a propósito: sin usuario en el request el contador no puede quedar sin
    clave (una clave constante mete a todo el mundo en el mismo bucket), así que cae a
    `client_ip`. Fail-safe, no fail-open: el límite se sigue aplicando. Los prefijos `u:`/`ip:`
    evitan que un user_id y una IP compartan bucket.

    Args:
        request: Request entrante.

    Returns:
        `"u:<user_id>"` si el request está autenticado; `"ip:<ip>"` si no.
    """
    usuario = getattr(request.state, "user", None)
    user_id = usuario.get("id") if isinstance(usuario, dict) else None
    return f"u:{user_id}" if user_id else f"ip:{client_ip(request)}"
