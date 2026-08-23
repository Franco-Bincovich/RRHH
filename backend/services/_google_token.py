"""
El access_token de Google: obtenerlo, y renovarlo con el refresh token si venció.

Extraído de `gmail_service.py`, que estaba en 150/150 y no admitía una línea más.

🔴 EL CORTE ES POR LO QUE SE VA A COMPARTIR, no por líneas. Hasta hoy el token lo usaba un solo
caso de uso (leer postulaciones de candidatos). Con el envío de mails pasan a ser dos, y si el
envío se copiara su propia versión de esto, cualquier arreglo del refresh quedaría hecho en un
lado solo — que es exactamente el modo de falla que este repo ya pagó con los filtros duplicados
front/back: la misma regla escrita dos veces diverge, siempre.

Por eso NO se extrajo `_gmail_parseo.py`, que era el corte anotado en CLAUDE.md: ese se lleva el
parseo de headers (17 líneas ya independientes) y deja juntos los dos casos de uso. Corta por el
lado que no importa.

Función libre que recibe el repo por parámetro — molde `_vacaciones_write.crear(repo, ...)`.

## 🔴 LOS TRES BUGS QUE ESTE MÓDULO ARREGLA (estaban rotos para la LECTURA, ya en producción)

1. **El token renovado no se persistía.** El código viejo devolvía el `access_token` nuevo y no
   lo guardaba nunca. Consecuencia: `token_expiry` quedaba fijo en el pasado para siempre, así
   que la condición "¿venció?" daba SIEMPRE True y **cada request pagaba un round-trip extra a
   Google**. Invisible en la lectura de candidatos (una llamada esporádica); caro en el envío,
   donde el token se pide por cada mail de un lote.
2. **`token_expiry` NULL salteaba el refresh entero.** El viejo `if expiry_str:` era la única
   puerta al refresh: sin vencimiento guardado, se devolvía el token tal cual, Gmail respondía
   401 y el caller lo envolvía en `GMAIL_ERROR` **502** — "error al consultar Gmail" cuando lo
   que pasaba era "tu sesión venció". Diagnóstico equivocado para quien lo lee.
3. **`except (ValueError, TypeError): pass` devolvía el token viejo EN SILENCIO.** Un
   `token_expiry` que no parseara (o naive, que hace explotar la comparación con un aware)
   caía en ese `pass` y seguía como si nada.

**La regla que sale de los tres, y que ordena el módulo: cuando NO SE PUEDE SABER si el token
sirve, se asume que NO sirve y se renueva.** Renovar de más cuesta un round-trip; usar un token
muerto cuesta un error con el diagnóstico equivocado en el momento de mandar un mail. Por eso
`_vencido()` devuelve True en los tres casos dudosos —sin fecha, ilegible, o vencida— y ninguno
de los tres es un `pass`.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from config.settings import settings
from services._google_token_fallo import detalle_de_google, error_de_renovacion
from utils.errors import AppError
from utils.logger import logger

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Se renueva un minuto ANTES del vencimiento real. Un token con 20 segundos de vida pasa el
# chequeo y se muere a mitad del trabajo — y con el envío masivo el trabajo dura minutos, no
# milisegundos. El costo de renovar de más es un round-trip; el de quedarse corto, un lote
# cortado por la mitad con la mitad de los mails mandados.
_MARGEN = timedelta(seconds=60)


def access_token_valido(repo, user_id: str) -> str:
    """Obtiene un access_token de Google utilizable, renovándolo si hace falta.

    Args:
        repo: IntegracionRepo (o doble de test) con `get_by_user_and_tipo` y `actualizar_token`.
        user_id: UUID (str) del usuario dueño de la integración.

    Returns:
        Un access_token vigente contra las APIs de Google.

    Raises:
        AppError: GMAIL_NOT_CONFIGURED (400) si no hay integración o falta el refresh token.
        AppError: GMAIL_TOKEN_EXPIRED (502) si Google rechazó la credencial — el caso típico es
            que el permiso fue revocado o el refresh token venció.
        AppError: GMAIL_RENOVACION_FALLIDA (502) si no se pudo hablar con Google.
            🔴 Los dos son 502 y NINGUNO es 401: ver `services/_google_token_fallo.py`.
    """
    integracion = repo.get_by_user_and_tipo(user_id, "google")
    if not integracion or not integracion.get("access_token"):
        raise AppError("Gmail no configurado", "GMAIL_NOT_CONFIGURED", 400)
    if not _vencido(integracion.get("token_expiry")):
        return integracion["access_token"]
    return _renovar(repo, user_id, integracion)


def _vencido(expiry_str) -> bool:
    """¿Hay que renovar? True TAMBIÉN cuando no se puede saber (ver el encabezado del módulo).

    Los tres "no se puede saber" que antes devolvían el token viejo:
      · sin `token_expiry` guardado (bug 2);
      · con un valor que no parsea (bug 3);
      · naive, que hacía explotar la comparación con un datetime aware (bug 3, misma rama).
    El naive no se rechaza: se ASUME UTC, que es como lo escribe `_google_oauth.procesar_callback`.
    Rechazarlo forzaría un refresh eterno en una base que se llenara de valores naive.
    """
    if not expiry_str:
        return True
    try:
        expiry = datetime.fromisoformat(str(expiry_str).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.warning("token_expiry ilegible en la integración de Google; se renueva",
                       extra={"valor": str(expiry_str)[:40]})
        return True
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry <= datetime.now(timezone.utc) + _MARGEN


def _renovar(repo, user_id: str, integracion: dict) -> str:
    """Cambia el refresh token por un access_token nuevo, lo persiste y lo devuelve."""
    refresh = integracion.get("refresh_token")
    if not refresh:
        raise AppError("Gmail no configurado", "GMAIL_NOT_CONFIGURED", 400)
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(_GOOGLE_TOKEN_URL, data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            datos = resp.json()
        token: str = datos["access_token"]
    except Exception as exc:  # noqa: BLE001 — incluye el invalid_grant del token revocado
        # `detalle` trae lo que Google contestó de verdad; `str(exc)` solo, que es lo que se
        # logueaba antes, no distingue `invalid_grant` de `invalid_client`. Ver el sibling.
        logger.error("Error al renovar token de Google",
                     extra={"error": str(exc), "google": detalle_de_google(exc)})
        # 🔴 502, NO 401: el usuario está autenticado y quien no puede autenticarse es este
        # backend contra Google. El porqué —y por qué no es 503— está en `_google_token_fallo`.
        raise error_de_renovacion(exc)
    _persistir(repo, user_id, token, datos.get("expires_in"))
    return token


def _persistir(repo, user_id: str, token: str, expires_in) -> None:
    """Guarda el token renovado. BEST-EFFORT: un fallo acá no puede tumbar la operación.

    Quien llama ya tiene el token en la mano y la operación de negocio puede seguir. Lo único
    que se pierde si esto falla es el ahorro del round-trip en el PRÓXIMO request — degrada
    exactamente al comportamiento viejo, que es el peor caso aceptable.
    """
    try:
        vence: Optional[str] = None
        if expires_in:
            vence = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
        repo.actualizar_token(user_id, token, vence)
    except Exception as exc:  # noqa: BLE001 — ver docstring
        logger.warning("No se pudo persistir el token renovado de Google",
                       extra={"user_id": user_id, "error": str(exc)})
