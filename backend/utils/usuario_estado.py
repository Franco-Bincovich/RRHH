"""
Caché por proceso del ESTADO de autorización de cada usuario, para no pegarle a la base en
cada request autenticado.

Molde: `utils/empresas_cache.py`. Es el mismo problema —un dato chico, que cambia poquísimo, y
que hay que consultar en CADA request— y por eso repite sus cuatro decisiones: singleton por
proceso · **el constructor no toca la base** (carga perezosa, en el primer uso, para no
penalizar el cold start en serverless) · TTL, nunca una query por request · fallar sin colgar
el request.

Difiere en dos cosas, y las dos son a propósito.

🔴 1. ACÁ ES FAIL-CLOSED, AL REVÉS QUE `empresas_cache`.
Allá, descartar el header **ENSANCHA**: `empresa_id=None` significa "todas las empresas" (vista
consolidada), así que ante un blip de base la opción conservadora es ACEPTAR. Acá no hay nada
que ensanchar en la dirección segura: el rol **es** la autorización. Un estado que no se puede
resolver no se puede asumir, así que **se niega**.
**Y eso ya es el comportamiento de hoy, no uno nuevo:** el middleware envuelve la query en un
`try/except` que deja `rol=None`, y `utils/permisos.py` es fail-closed ante un rol desconocido
→ 403. Este módulo **conserva la política; no la cambia.**

2. Se cachea POR USUARIO, no un conjunto entero. En `empresas_cache` la pregunta es "¿este
UUID está en el set?" y el set entero entra en una query; acá la pregunta es por una fila
puntual y traerlas todas escalaría con la tabla de usuarios sin ninguna necesidad. El
diccionario está acotado por la cantidad de usuarios REALES que pasan el JWT: el `sub` ya viene
de un token con firma verificada, así que nadie puede sembrarlo con ids inventados.

🚨 NI EL FALLO SE CACHEA, NI UNA ENTRADA VENCIDA SE SIGUE SIRVIENDO. Son la misma decisión que
la de arriba, vista desde los dos lados:
· Servir una entrada vencida porque el refresco falló sería fail-open con otro nombre — a quien
  le acaban de bajar el rol seguiría entrando mientras dure el incidente.
· Cachear el fallo convertiría un blip de un segundo en 60 segundos de gente afuera.
El costo de no cachear el fallo es que, con la base caída, se reintenta por request. Es
exactamente lo que pasa hoy, y con la base caída no hay nada que servir igual.

Sin lock: dos requests concurrentes del mismo usuario pueden refrescar a la vez. Es una lectura
idempotente, así que el peor caso es una query de más — barato comparado con meter un
`threading.Lock` en el camino async del middleware.
"""
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Optional

from repositories.usuario_repo import UsuarioRepo
from utils._sesion_inactividad import THROTTLE_ESCRITURA, parsear_fecha
from utils.logger import logger

# 60s: el rol de alguien cambia pocas veces en la vida del sistema, pero cuando cambia es
# porque alguien decidió que esa persona deje de poder hacer algo. Un minuto es la ventana
# máxima que ese cambio tarda en regir sola.
_TTL_SEGUNDOS = 60


@dataclass(frozen=True)
class EstadoUsuario:
    """Lo que el middleware necesita saber del usuario para autorizar el request.

    `resuelto` distingue los DOS motivos por los que un estado puede no servir, que aguas
    arriba merecen respuestas distintas: "la fila dice activo=false" (el usuario fue dado de
    baja → 403 con un código propio, que el front usa para mandarlo al login) y "no se pudo
    leer la fila" (la base no respondió → rol=None y decide `permisos.py`, que es lo que ya
    pasaba antes de que este caché existiera). Sin este campo los dos casos colapsarían en uno
    y un blip de base le diría al usuario que su cuenta fue desactivada.
    """

    rol: Optional[str]
    activo: bool
    resuelto: bool = True
    ultimo_acceso: Optional[datetime] = None


# Lo que se devuelve cuando el estado no se puede resolver. `rol=None` hace que
# `utils/permisos.puede` niegue todo (fail-closed) sin ningún caso especial aguas abajo.
DENEGADO = EstadoUsuario(rol=None, activo=False, resuelto=False)


class _UsuarioEstadoCache:
    def __init__(self, repo: Optional[UsuarioRepo] = None) -> None:
        # Nada de trabajo acá: instanciar NO toca la base (calca el __init__ de PyJWKClient).
        self._repo = repo
        self._entradas: dict[str, tuple[EstadoUsuario, float]] = {}

    def estado(self, user_id: str) -> EstadoUsuario:
        """Estado vigente del usuario. En el camino normal (hit) no hace ninguna query.

        Args:
            user_id: el `sub` del JWT, ya verificado contra el JWKS por el caller.

        Returns:
            El `EstadoUsuario` cacheado o recién leído; `DENEGADO` si la fila no existe o si la
            base no responde (fail-closed, ver el docstring del módulo).
        """
        ahora = time.monotonic()
        entrada = self._entradas.get(user_id)
        if entrada is not None and ahora - entrada[1] <= _TTL_SEGUNDOS:
            return entrada[0]

        try:
            self._repo = self._repo or UsuarioRepo()
            fila = self._repo.get_estado(user_id)
        except Exception as exc:
            logger.error(
                "No se pudo resolver el estado del usuario; se niega el request",
                extra={"user_id": user_id, "motivo": type(exc).__name__},
            )
            return DENEGADO

        # `bool(...)` y no `.get("activo", True)`: si la columna faltara en la respuesta, el
        # default seguro es negar, no dejar pasar.
        estado = EstadoUsuario(
            rol=(fila or {}).get("rol"),
            activo=bool((fila or {}).get("activo")),
            ultimo_acceso=parsear_fecha((fila or {}).get("ultimo_acceso")),
        )
        self._entradas[user_id] = (estado, ahora)
        return estado

    def registrar_actividad(self, user_id: str) -> None:
        """Sella `ultimo_acceso`, como mucho una vez cada `THROTTLE_ESCRITURA`.

        🔑 El throttle mira el VALOR (qué tan viejo es `ultimo_acceso`), no un contador aparte
        de "cuándo escribí yo". Es lo que hace que funcione con N procesos: si otra instancia
        selló hace un minuto, esta lee ese valor al vencer su TTL y no vuelve a escribir. Un
        marcador local haría que cada proceso escribiera su propia serie, multiplicando los
        UPDATE por la cantidad de instancias vivas.

        Un fallo de escritura NO tumba el request: la peor consecuencia es que la sesión venza
        antes de tiempo y el usuario vuelva a loguearse.
        """
        entrada = self._entradas.get(user_id)
        if entrada is None:
            return  # sin entrada no hay nada que sellar; el próximo request la crea
        ultimo = entrada[0].ultimo_acceso
        if ultimo is not None and datetime.now(timezone.utc) - ultimo < THROTTLE_ESCRITURA:
            return
        try:
            self._repo = self._repo or UsuarioRepo()
            sello = self._repo.tocar_ultimo_acceso(user_id)
        except Exception as exc:
            logger.warning(
                "No se pudo sellar ultimo_acceso",
                extra={"user_id": user_id, "motivo": type(exc).__name__},
            )
            return
        self._entradas[user_id] = (replace(entrada[0], ultimo_acceso=parsear_fecha(sello)), entrada[1])

    def invalidar(self, user_id: str) -> None:
        """Descarta la entrada del usuario para que el próximo request la vuelva a leer.

        La llama quien CAMBIA el estado (la baja), para que rija en el acto en vez de esperar
        hasta 60s. Es una optimización de latencia, no la garantía: en serverless hay N
        procesos y cada uno tiene su caché, así que el TTL sigue siendo el techo real de cuánto
        tarda una baja en regir en TODAS las instancias.
        """
        self._entradas.pop(user_id, None)


_cache = _UsuarioEstadoCache()


def estado_usuario(user_id: str) -> EstadoUsuario:
    """Wrapper sobre el singleton del proceso. Ver `_UsuarioEstadoCache.estado`."""
    return _cache.estado(user_id)


def invalidar_estado(user_id: str) -> None:
    """Wrapper sobre el singleton del proceso. Ver `_UsuarioEstadoCache.invalidar`."""
    _cache.invalidar(user_id)


def registrar_actividad(user_id: str) -> None:
    """Wrapper sobre el singleton del proceso. Ver `_UsuarioEstadoCache.registrar_actividad`."""
    _cache.registrar_actividad(user_id)
