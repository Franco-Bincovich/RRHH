"""
Workaround de HTTP/1.1 para supabase 2.9.1. **Es temporal y tiene condición de salida escrita.**

Salió de `supabase_client.py` el 20/8/2026, que llegó a 205/200 al sumarle el guard que impide
usar el cliente real bajo tests. El corte no es por tamaño: **este archivo entero desaparece** el
día que se actualice `supabase-py` (ver la condición abajo), y aquel queda con lo que sí es
permanente — los proxies, el reintento ante conexión muerta y las dos instancias. Un workaround
con fecha de vencimiento en su propio archivo se borra de un saque; mezclado, hay que ir a
buscarle los pedazos.

`_force_http1` es lo único que se usa de afuera: lo llaman las dos fábricas de
`supabase_client.py`, así que el reintento de `_recreate()` también nace en HTTP/1.1.
"""
from typing import Any, Optional

from httpx import Client as HttpxClient
from supabase import Client


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
