"""
POR QUÉ falló la renovación del token de Google, y qué se le dice a RRHH en cada caso.

Extraído de `services/_google_token.py`, que estaba en 140/150 y no admitía esto adentro. El
corte no es por líneas: aquel módulo responde *"¿tengo un access_token usable?"* y esto responde
*"¿de quién es el problema y qué tiene que hacer la persona que lo está viendo?"* — una es
mecánica de OAuth y la otra es producto.

## 🔴 UN TOKEN DE GOOGLE MUERTO NO ES UN 401. Es 502.

Hasta el 23/8/2026 esto salía **401 `GMAIL_TOKEN_EXPIRED`**, y el 401 era el bug: el interceptor
del front leía el status y solo el status, así que un usuario perfectamente autenticado que abría
**/vacantes** —que pide los mails pendientes al montar— quedaba deslogueado en cada carga de la
pantalla. Once días seguidos, porque el token de la casilla venció el 10/8 y no se renovó más.

El 401 significa *"vos no estás autenticado"*. Acá el usuario SÍ lo está: quien no puede
autenticarse es **nuestro backend contra Google**, con una credencial que no es del usuario y que
él no puede arreglar reintentando el login. Eso es exactamente un fallo de upstream.

**502 y no 503**, por dos motivos:
  · **502** dice "el servicio de arriba me contestó algo que no sirve" y **503** dice "YO estoy
    caído, probá más tarde". El sistema está perfectamente sano: lo que está roto es una
    integración, y el resto de la app funciona.
  · Es el status que este repo YA usa para lo mismo: `GMAIL_ERROR` cuando la API de Gmail falla
    (`services/gmail_service.py:93`) y `ZERNIO_ERROR` / `ZERNIO_CONNECTION_ERROR`
    (`services/zernio_service.py:86,92`). Elegir 503 acá abriría una segunda convención para la
    misma clase de cosa.

> ⚠️ **NO CONFUNDIR CON EL BUG 2 QUE DOCUMENTA `_google_token.py`.** Aquel dice que devolver el
> token viejo hacía que Gmail contestara 401 y el caller lo envolviera en un `GMAIL_ERROR` **502**
> que decía *"error al consultar Gmail"* cuando lo que pasaba era que el token estaba muerto.
> **El problema ahí NUNCA fue el 502: era el DIAGNÓSTICO** — un code y un mensaje genéricos para
> una causa concreta. Acá el status vuelve a ser 502 pero el code sigue siendo específico y el
> mensaje dice qué hacer, que es justo lo que a aquel le faltaba. Un futuro que lea el bug 2 y
> "corrija" esto de vuelta a 401 reabre el bug de /vacantes.

## Las dos causas, que piden mensajes distintos

`_renovar` envolvía TODO en un `except Exception` y decía siempre lo mismo. Pero *"Google rechazó
la credencial"* y *"no pudimos hablar con Google"* piden acciones opuestas: en el primero
reintentar no sirve para nada y hay que reconectar la cuenta; en el segundo reconectar no arregla
nada y lo que corresponde es esperar. Decirle "reconectá la cuenta" a alguien que tuvo un blip de
red lo manda a rehacer una integración que estaba bien.
"""
from typing import Optional

from utils.errors import AppError

MSG_REVOCADO = (
    "La casilla del sistema perdió el acceso a Google. Reconectala desde Configuración → "
    "Integraciones para volver a leer postulaciones y enviar mails."
)
MSG_SIN_CONTACTO = (
    "No se pudo contactar a Google para renovar el acceso de la casilla del sistema. "
    "Reintentá en unos minutos."
)


def detalle_de_google(exc: Exception) -> Optional[str]:
    """Lo que Google dijo de verdad: `error` y `error_description` de su respuesta.

    🔴 ES EL DATO QUE FALTABA EN EL LOG, y por eso el token estuvo once días vencido sin que
    nadie pudiera decir por qué. `_renovar` logueaba `str(exc)`, que para el `HTTPStatusError` de
    `raise_for_status()` es *"Client error '400 Bad Request' for url ..."* — o sea el status y
    nada más. `invalid_grant` (el permiso fue revocado o el refresh token venció) e
    `invalid_client` (nuestro client_id/secret está mal) llegan los DOS como 400 y se arreglan de
    formas completamente distintas, y esa diferencia vive solo en el body.

    Args:
        exc: la excepción que levantó el POST al endpoint de token de Google.

    Returns:
        `"invalid_grant: Token has been expired or revoked."` o similar; None si la excepción no
        trae respuesta HTTP (timeout, DNS) o si el body no se puede leer.
    """
    respuesta = getattr(exc, "response", None)
    if respuesta is None:
        return None
    try:
        datos = respuesta.json() or {}
    except Exception:  # noqa: BLE001 — un body que no es JSON no aporta nada y no puede romper el log
        return None
    error = str(datos.get("error") or "").strip()
    descripcion = str(datos.get("error_description") or "").strip()
    return ": ".join(p for p in (error, descripcion) if p) or None


def error_de_renovacion(exc: Exception) -> AppError:
    """El `AppError` que corresponde a un fallo de renovación, ya clasificado.

    🔑 El criterio es **si Google llegó a contestar rechazando**, no qué dice el body: un 4xx del
    endpoint de token es Google diciendo "esta credencial no me sirve", y eso no lo arregla ningún
    reintento — se arregla reconectando la cuenta. Cualquier otra cosa (timeout, DNS, un 5xx de
    Google) es transitoria y reconectar no cambiaría nada.

    Args:
        exc: la excepción que levantó el POST al endpoint de token de Google.

    Returns:
        AppError 502 `GMAIL_TOKEN_EXPIRED` si Google rechazó la credencial;
        AppError 502 `GMAIL_RENOVACION_FALLIDA` si no se pudo hablar con Google.
        Nunca 401: ver el encabezado del módulo.
    """
    respuesta = getattr(exc, "response", None)
    rechazo = respuesta is not None and 400 <= getattr(respuesta, "status_code", 0) < 500
    if rechazo:
        return AppError(MSG_REVOCADO, "GMAIL_TOKEN_EXPIRED", 502)
    return AppError(MSG_SIN_CONTACTO, "GMAIL_RENOVACION_FALLIDA", 502)
