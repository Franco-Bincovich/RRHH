"""
Cliente PostgreSQL sobre asyncpg — fundación de datos de la migración a RDS.

REEMPLAZA A `integrations/supabase_client.py`, que en la migración desaparece entero
(con él se van el _RootProxy/_NodeProxy/_MethodProxy de replay ante RemoteProtocolError
y el monkeypatch HTTP/1.1 de supabase-py 2.9.1 — ambos existían solo para pelear con el
SDK y no tienen equivalente acá).

⚠️ ASUME UN PROCESO PERSISTENTE (ECS/EC2). NO ES SERVERLESS-SAFE.
Un pool de asyncpg mantiene conexiones TCP vivas entre requests. Eso no sobrevive al
modelo de Vercel: cada lambda warm reutiliza el proceso con conexiones que pueden estar
muertas, y cada lambda fría abre su propio pool — con min_size=2 y N lambdas concurrentes
se agota `max_connections` de RDS sin que ninguna lo sepa. Por eso RRHH deja Vercel para
el backend al migrar; no es una preferencia de infraestructura, es un requisito de este
archivo.

**NO IMPORTAR ESTE MÓDULO MIENTRAS EL BACKEND SIGA EN VERCEL.** Hoy vive aislado en
`migracionAWS/` justamente para eso: no lo importa nadie. Al migrar, se mueve a
`backend/integrations/postgres_client.py` y recién ahí se cablea.

Uso previsto (colgado del lifespan de FastAPI, que hoy NO existe en main.py — hay que
crearlo: la app se construye declarativamente, sin startup/shutdown donde enganchar esto):

    from contextlib import asynccontextmanager
    from integrations.postgres_client import init_pool, close_pool

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_pool()
        yield
        await close_pool()

    app = FastAPI(lifespan=lifespan, ...)

Los helpers (execute/fetch/fetchone/fetchval) son la interfaz que consumen los
repositories. Reciben SQL parametrizado con placeholders posicionales de asyncpg
($1, $2, ...) — nunca interpolar valores en el string de la query.
"""
from typing import Any, Optional

import asyncpg

from config.settings import settings

# Pool global del proceso. None hasta que init_pool() corra en el startup.
_pool: Optional[asyncpg.Pool] = None

# min_size=2: dos conexiones calientes desde el arranque, sin latencia de handshake en el
#   primer request.
# max_size=10: techo por proceso. Al dimensionar el servicio, multiplicar por la cantidad
#   de tasks de ECS y contrastar contra `max_connections` de la instancia RDS — el límite
#   se agota entre todos los procesos, no por proceso.
# command_timeout=30: espeja el supabase_timeout actual (settings.supabase_timeout = 30).
#   Una query que pasa de 30s se aborta en vez de colgar el request.
_MIN_SIZE = 2
_MAX_SIZE = 10
_COMMAND_TIMEOUT = 30

# RDS exige SSL (rechaza la conexión en claro con `no pg_hba.conf entry ... no encryption`).
# OJO con la semántica de asyncpg: ssl="require" CIFRA el tráfico pero NO verifica el
# certificado del servidor contra una CA — protege de sniffing pasivo, no de MITM activo.
# Endurecer a "verify-full" exige distribuir el bundle de CA de RDS y setear
# ssl.create_default_context(cafile=...). Se deja "require" porque es lo validado en el
# proyecto hermano; revisar antes de producción si el tráfico sale de la VPC.
_SSL_MODE = "require"


async def init_pool() -> asyncpg.Pool:
    """Crea el pool global de conexiones a Postgres. Idempotente.

    Pensada para el startup del lifespan de FastAPI. Si el pool ya existe lo devuelve tal
    cual en vez de crear un segundo (dos pools duplicarían las conexiones contra RDS sin
    que nadie cierre el primero).

    La DSN se lee de settings en tiempo de llamada, no de import: así el módulo se puede
    importar en un entorno sin `database_url` configurada (tests, tooling) sin explotar.

    Returns:
        El pool listo para usar.

    Raises:
        asyncpg.PostgresError: si las credenciales o la DSN son inválidas.
        OSError: si el host de RDS no es alcanzable (security group, VPC, DNS).
    """
    global _pool
    if _pool is not None:
        return _pool

    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=_MIN_SIZE,
        max_size=_MAX_SIZE,
        command_timeout=_COMMAND_TIMEOUT,
        ssl=_SSL_MODE,
    )
    return _pool


async def close_pool() -> None:
    """Cierra el pool y libera las conexiones. Idempotente.

    Pensada para el shutdown del lifespan. Espera a que las queries en vuelo terminen
    (asyncpg.Pool.close() drena; no corta a la mitad). Deja _pool en None para que un
    init_pool() posterior pueda recrearlo limpio.
    """
    global _pool
    if _pool is None:
        return
    await _pool.close()
    _pool = None


def get_pool() -> asyncpg.Pool:
    """Devuelve el pool global.

    Returns:
        El pool inicializado.

    Raises:
        RuntimeError: si init_pool() no corrió todavía. Fail-fast explícito: sin esto el
            fallo sería un AttributeError sobre None en el primer query, lejos de la causa
            real (el lifespan no está cableado en main.py).
    """
    if _pool is None:
        raise RuntimeError(
            "Pool de Postgres no inicializado — llamar a init_pool() en el startup "
            "del lifespan de FastAPI antes de operar contra la base."
        )
    return _pool


async def execute(query: str, *args: Any) -> None:
    """Ejecuta una sentencia que no devuelve filas (INSERT/UPDATE/DELETE/DDL).

    Descarta el status string de asyncpg (ej. "UPDATE 3"): si un caller necesita saber
    cuántas filas tocó, la query debe llevar RETURNING y usar fetch/fetchval.

    Args:
        query: SQL con placeholders posicionales de asyncpg ($1, $2, ...).
        *args: Valores para los placeholders, en orden.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(query, *args)


async def fetch(query: str, *args: Any) -> list[dict]:
    """Ejecuta un SELECT y devuelve todas las filas como dicts.

    Convierte cada asyncpg.Record a dict: el Record soporta acceso por clave pero no es
    un dict (no serializa a JSON ni acepta **unpacking), y los mappers de los repositories
    esperan dicts — es la misma forma que hoy devuelve el SDK de Supabase, así que los
    `_row()` / `_to_response()` existentes siguen funcionando sin tocarse.

    Args:
        query: SQL con placeholders posicionales de asyncpg ($1, $2, ...).
        *args: Valores para los placeholders, en orden.

    Returns:
        Lista de filas como dicts; lista vacía si no hubo resultados.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


async def fetchone(query: str, *args: Any) -> Optional[dict]:
    """Ejecuta un SELECT y devuelve la primera fila como dict, o None si no hay ninguna.

    Equivalente al `.maybe_single()` del SDK de Supabase (54 usos hoy): no levanta si no
    encuentra nada. El `.single()` de Supabase, que sí levanta, se modela dejando que el
    service haga el `if row is None: raise AppError(...)` — más explícito y con el mensaje
    de negocio correcto.

    Args:
        query: SQL con placeholders posicionales de asyncpg ($1, $2, ...).
        *args: Valores para los placeholders, en orden.

    Returns:
        La primera fila como dict, o None si el SELECT no devolvió filas.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
    return dict(row) if row is not None else None


async def fetchval(query: str, *args: Any) -> Any:
    """Ejecuta una query y devuelve un único valor escalar (primera columna de la primera fila).

    Para COUNT(*), EXISTS(...), o un INSERT ... RETURNING id.

    Ambigüedad a tener presente: devuelve None tanto si no hubo filas como si la fila
    existe y su primera columna es NULL. Donde esa diferencia importe, usar fetchone.

    Args:
        query: SQL con placeholders posicionales de asyncpg ($1, $2, ...).
        *args: Valores para los placeholders, en orden.

    Returns:
        El valor escalar, o None (sin filas, o valor NULL).
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
