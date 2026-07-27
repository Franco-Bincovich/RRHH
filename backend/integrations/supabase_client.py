"""
Clientes de Supabase resilientes a conexiones muertas.

- supabase_client: anon key, respeta RLS. Para operaciones autenticadas del usuario.
- supabase_admin: service key, bypasea RLS. Solo para operaciones administrativas.

Se exportan como proxies transparentes. En Vercel serverless las lambdas warm reutilizan
el proceso y la conexión HTTP subyacente puede quedar muerta entre invocaciones, lanzando
httpx.RemoteProtocolError en la primera operación. El proxy detecta ese error, recrea el
cliente interno y reproduce la cadena de operaciones una sola vez; si el reintento también
falla, propaga el error original sin silenciarlo.
"""
from typing import Any, Callable, List, Optional, Tuple

from httpx import Client as HttpxClient, RemoteProtocolError
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from config.settings import settings
from utils.logger import logger

# Módulos del ecosistema Supabase cuyos objetos son parte de la cadena fluida (se envuelven).
_CHAINABLE_ROOTS = frozenset({"postgrest", "gotrue", "storage3", "supafunc", "supabase", "realtime"})

_Op = Tuple  # un paso de la cadena: ("attr", nombre) o ("call", args, kwargs)


def _replay(client: Client, ops: List[_Op]) -> Any:
    """Reproduce una cadena de operaciones registrada contra un cliente fresco."""
    obj: Any = client
    for op in ops:
        obj = getattr(obj, op[1]) if op[0] == "attr" else obj(*op[1], **op[2])
    return obj


def _wrap(root: "_RootProxy", ops: List[_Op], value: Any) -> Any:
    """Envuelve un valor de la cadena fluida; devuelve datos crudos en las hojas."""
    if callable(value):
        return _MethodProxy(root, ops, value)
    if (type(value).__module__ or "").split(".")[0] in _CHAINABLE_ROOTS:
        return _NodeProxy(root, ops, value)
    return value


class _NodeProxy:
    """Envoltura de un objeto intermedio (builder o sub-cliente) de Supabase."""

    def __init__(self, root: "_RootProxy", ops: List[_Op], value: Any) -> None:
        """Guarda el proxy raíz, la cadena de operaciones acumulada y el objeto real."""
        self._root, self._ops, self._value = root, ops, value

    def __getattr__(self, name: str) -> Any:
        """Resuelve el atributo en el objeto real y vuelve a envolver el resultado."""
        return _wrap(self._root, self._ops + [("attr", name)], getattr(self._value, name))


class _MethodProxy:
    """Envoltura de un método; reintenta una sola vez ante RemoteProtocolError."""

    def __init__(self, root: "_RootProxy", ops: List[_Op], func: Callable) -> None:
        """Guarda el proxy raíz, la cadena acumulada y la función real a invocar."""
        self._root, self._ops, self._func = root, ops, func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Ejecuta la llamada; si la conexión está muerta recrea el cliente y reintenta."""
        ops = self._ops + [("call", args, kwargs)]
        try:
            result = self._func(*args, **kwargs)
        except RemoteProtocolError:
            self._root._recreate()
            result = _replay(self._root._client, ops)
        return _wrap(self._root, ops, result)


class _RootProxy:
    """Proxy raíz que mantiene el cliente Supabase interno y permite recrearlo."""

    def __init__(self, factory: Callable[[], Client]) -> None:
        """Crea el cliente interno a partir de la fábrica y la conserva para recrearlo."""
        self._factory = factory
        self._client = factory()

    def _recreate(self) -> None:
        """Recrea el cliente interno tras una conexión muerta (loguea en WARNING)."""
        logger.warning("Recreando cliente Supabase tras RemoteProtocolError")
        self._client = self._factory()

    def __getattr__(self, name: str) -> Any:
        """Delega el acceso de atributos al cliente real, envuelto por el proxy."""
        return _wrap(self, [("attr", name)], getattr(self._client, name))


def _opts() -> SyncClientOptions:
    """Opciones con timeout httpx explícito (postgrest/storage/functions) desde settings.

    Instancia fresca por cliente: create_client muta options.headers con las auth headers,
    así que anon y admin no pueden compartir el mismo objeto. No configura keep-alive:
    supabase 2.9.1 no expone httpx.Limits vía ClientOptions; el retry de _MethodProxy
    sigue cubriendo la conexión muerta reutilizada.
    """
    t = settings.supabase_timeout
    return SyncClientOptions(
        postgrest_client_timeout=t, storage_client_timeout=t, function_client_timeout=t,
    )


# ── Workaround HTTP/1.1 (supabase 2.9.1) ──────────────────────────────────────
# El entorno (Windows schannel + Cloudflare frente a Supabase) fuerza renegociación
# TLS, que HTTP/2 no tolera → httpx.RemoteProtocolError constante. postgrest/gotrue/
# storage/supafunc de supabase 2.9.1 hardcodean http2=True en su httpx.Client y NO
# exponen forma pública de desactivarlo (ClientOptions no admite httpx). Workaround:
# tras create_client, reemplazar cada sesión httpx por una gemela con http2=False.
# Ref: https://github.com/supabase/supabase-py/issues/1064
# Se retira al actualizar supabase-py a una versión con httpx_client público
# (postgrest 2.31+ acepta http_client vía ClientOptions).
def _to_http1(old: HttpxClient) -> HttpxClient:
    """Crea una sesión httpx gemela de `old` forzada a HTTP/1.1 (NO cierra la vieja).

    Preserva base_url, headers (incluidas las auth), timeout (los 30s de _opts) y
    follow_redirects. verify=True: coincide con el default de supabase (que no lo
    expone para leer) y RRHH nunca desactiva TLS. **No** cierra la vieja: el caller
    la cierra recién tras reasignar TODAS las referencias que la comparten.
    """
    return type(old)(
        base_url=old.base_url, headers=old.headers, timeout=old.timeout,
        follow_redirects=old.follow_redirects, verify=True, http2=False,
    )


def _iter_httpx(root: Any, seen: Optional[set] = None, depth: int = 0):
    """Descubre (owner, attr, httpx.Client) recorriendo el árbol de instancias.

    Recorre solo __dict__ (atributos reales → siempre setables; ignora properties de
    solo lectura como `http_client`, que envuelven `_http_client`). Trata httpx.Client
    como hoja (no recorre su transport). Descubrir en vez de hardcodear evita puntos
    ciegos: cualquier sesión nueva que gotrue/postgrest/storage/supafunc agregue en el
    árbol la ven tanto el patch como el guard.
    """
    if seen is None:
        seen = set()
    if depth > 6 or id(root) in seen:
        return
    seen.add(id(root))
    for name, val in list(getattr(root, "__dict__", {}).items()):
        if isinstance(val, HttpxClient):
            yield root, name, val
        elif hasattr(val, "__dict__") and not isinstance(val, (str, bytes, int, float, bool)):
            yield from _iter_httpx(val, seen, depth + 1)


def _force_http1(client: Client) -> Client:
    """Fuerza HTTP/1.1 en TODAS las sesiones httpx del cliente y verifica (guard obligatorio).

    Workaround de supabase 2.9.1 (ver comentario arriba). Flujo seguro y genérico:
    1) fuerza el init de los sub-clientes lazy (postgrest/storage/functions; auth es
       eager) para que sus sesiones existan y se recorran;
    2) descubre TODAS las refs httpx del árbol y las agrupa por identidad de sesión —
       las que compartían un objeto (storage .session/._client; auth ._http_client y
       admin._http_client) reciben la MISMA gemela; las independientes, la suya;
    3) reasigna TODAS las referencias ANTES de cerrar nada (cerrar una sesión que otra
       ref todavía usa da "Cannot send a request, as the client has been closed");
    4) guard: re-recorre el árbol ya parcheado y exige http2=False AND is_closed=False
       en cada sesión — si una versión futura agrega otra ref sin cubrir, falla acá;
    5) recién entonces cierra las viejas (dedup por id, una vez c/u).

    Vive en el factory: _recreate() reconstruye el cliente y vuelve a pasar por acá,
    así el reintento también nace en HTTP/1.1. El refresh de token muta session.headers
    sobre el objeto nuevo (se reasignó el atributo, verificado).
    """
    _ = client.postgrest, client.storage, client.functions, client.auth  # init lazy

    groups: dict = {}  # id(old) -> (old_session, [(owner, attr), ...])
    for owner, attr, sess in _iter_httpx(client):
        groups.setdefault(id(sess), (sess, []))[1].append((owner, attr))

    for old, holders in groups.values():
        new = _to_http1(old)
        for owner, attr in holders:
            setattr(owner, attr, new)

    for owner, attr, sess in _iter_httpx(client):  # guard sobre el árbol ya parcheado
        if sess._transport._pool._http2 is not False or sess.is_closed:
            raise RuntimeError(
                f"Monkeypatch HTTP/1.1 falló en {type(owner).__name__}.{attr} (http2 "
                "activo o sesión cerrada) — revisar tras actualización de supabase-py/gotrue"
            )

    for old, _holders in groups.values():
        old.close()
    return client


# anon key: respeta RLS · service key: bypasea RLS — usar con criterio.
supabase_client: Any = _RootProxy(lambda: _force_http1(create_client(settings.supabase_url, settings.supabase_anon_key, options=_opts())))
supabase_admin: Any = _RootProxy(lambda: _force_http1(create_client(settings.supabase_url, settings.supabase_service_key, options=_opts())))
