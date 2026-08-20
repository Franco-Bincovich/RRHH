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
from typing import Any, Callable, List, Tuple

from httpx import RemoteProtocolError
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from config.settings import settings
from integrations._cliente_real_en_tests import abortar as _abortar_si_es_test
# Workaround temporal de supabase 2.9.1, en archivo propio porque se BORRA entero al
# actualizar la librería. Su condición de salida está escrita allá.
from integrations._http1_workaround import _force_http1
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
        """Ejecuta la llamada; si la conexión está muerta recrea el cliente y reintenta.

        🔴 ACÁ VA EL GUARD DE TESTS, Y NO EN `__getattr__` DE LA RAÍZ. Leer un atributo del proxy
        NO es usar la base: `monkeypatch.setattr(supabase_admin, "auth", fake)` hace un `getattr`
        para guardarse el valor original ANTES de reemplazarlo, así que un guard allá rojeaba a
        21 tests de `test_usuarios.py` que estaban falseando el cliente correctamente. Medido, no
        supuesto. Invocar sí es usar: `.execute()`, `.sign_in_with_password()` y `.upload()` son
        todas llamadas, y todas pasan por acá. El porqué completo, en `_cliente_real_en_tests.py`.

        Se le pasa la cadena de atributos acumulada (`table.insert.execute`) porque dice de un
        vistazo qué se estaba haciendo — un `execute` pelado no distingue una consulta de una
        subida a Storage.
        """
        _abortar_si_es_test(".".join(o[1] for o in self._ops if o[0] == "attr"))
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


# anon key: respeta RLS · service key: bypasea RLS — usar con criterio.
supabase_client: Any = _RootProxy(lambda: _force_http1(create_client(settings.supabase_url, settings.supabase_anon_key, options=_opts())))
supabase_admin: Any = _RootProxy(lambda: _force_http1(create_client(settings.supabase_url, settings.supabase_service_key, options=_opts())))
