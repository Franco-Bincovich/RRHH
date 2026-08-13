#!/usr/bin/env python3
"""Mide los endpoints de LISTADO y EXPORT del backend real contra la base local de escala.

QUE MIDE, Y POR QUE ESTO Y NO OTRA COSA
    Levanta la app FastAPI de verdad y le pega con TestClient. El request recorre el camino
    completo: router -> service -> repository -> PostgREST -> Postgres, y vuelve serializado.
    O sea que mide lo que el usuario espera, no lo que tarda una query aislada: incluye el
    N+1 (que en SQL puro no se ve, porque son N queries rapidas), la serializacion Pydantic,
    y el costo de PostgREST armando el JSON.

    Lo unico que NO recorre es la verificacion de firma del JWT, que se sustituye (ver abajo).

COMO SE APUNTA A LA BASE LOCAL — la pregunta del PASO 3
    La app no habla con Postgres: habla con PostgREST por HTTP. Asi que apuntarla a la base
    local NO se hace cambiando codigo, se hace levantando un PostgREST contra esa base y
    moviendo `SUPABASE_URL`, que ya es variable de entorno:

        docker run -d --name rrhh-pgrst -p 3001:3000 \
          -e PGRST_DB_URI="postgres://authenticator:CLAVE@host.docker.internal:5432/HR%20Karstec" \
          -e PGRST_DB_SCHEMAS=public -e PGRST_DB_ANON_ROLE=anon \
          -e PGRST_JWT_SECRET="<32+ caracteres>" postgrest/postgrest:v12.2.3

    Cero lineas de codigo tocadas. Es tambien la prueba de que la capa de datos no tiene
    nada de Supabase adentro mas alla del protocolo PostgREST.

LO UNICO QUE SE SUSTITUYE, Y POR QUE NO CONTAMINA LA MEDICION
    `middleware.auth._verificar_token` valida la firma ES256 contra el JWKS de Supabase, que
    en local no existe. Se reemplaza por una funcion que devuelve un user_id real de la base.
    Es una verificacion criptografica de microsegundos sobre una clave cacheada por proceso:
    sacarla no mueve ningun numero de los que esta sesion mira. Todo lo demas del middleware
    —estado del usuario, sesion, resolucion de X-Empresa-Id— corre igual.

USO
    python scripts/medir_escala.py            # una empresa y consolidado
    python scripts/medir_escala.py --json     # salida cruda
"""
import json
import os
import statistics
import sys
import time

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(RAIZ))

PGRST = os.environ.get("PGRST_URL", "http://localhost:3001")
SERVICE_KEY = os.environ["PGRST_SERVICE_KEY"]

os.environ.update({
    "SUPABASE_URL": PGRST,
    "SUPABASE_ANON_KEY": os.environ.get("PGRST_ANON_KEY", SERVICE_KEY),
    "SUPABASE_SERVICE_KEY": SERVICE_KEY,
    "JWT_SECRET": "clave-local-de-diagnostico-de-al-menos-32-chars",
    "ANTHROPIC_API_KEY": "sk-ant-local-no-se-usa",
    "ALLOWED_ORIGINS": "http://localhost:3000",
    "APP_ENV": "development",
})

import logging                                                   # noqa: E402
logging.disable(logging.WARNING)   # el log de negocio ensucia la tabla de tiempos

import middleware.auth as mw                                     # noqa: E402
from fastapi.testclient import TestClient                        # noqa: E402
from integrations.supabase_client import (                       # noqa: E402
    supabase_admin, supabase_client,
)

# supabase-py arma la base REST como f"{SUPABASE_URL}/rest/v1" — ese prefijo es de la
# plataforma Supabase, no de PostgREST, que sirve las tablas en la raiz. Se reapunta la
# sesion httpx a la raiz en vez de meter un nginx que reescriba el path: un proxy mas
# agregaria un salto de red a cada medicion, que es justo lo que esta sesion cuenta.
for _proxy in (supabase_admin, supabase_client):
    _proxy._client.postgrest.session.base_url = PGRST


def _usuario_admin() -> str:
    """Devuelve el id de un usuario admin_rrhh real de la base local."""
    r = supabase_admin.table("users").select("id").eq("rol", "admin_rrhh").limit(1).execute()
    if not r.data:
        raise SystemExit("La base local no tiene ningun usuario admin_rrhh. Corriste el seed?")
    return r.data[0]["id"]


USER_ID = _usuario_admin()
mw._verificar_token = lambda token, path: USER_ID   # ver docstring: unico reemplazo

import main                                                       # noqa: E402
from utils.rate_limit import limiter                              # noqa: E402

# 🔴 Se apaga el rate limit PARA MEDIR: un barrido de 26 exports x 3 modos agota cualquier
# franja horaria y devuelve 429 en el resto, o sea que sin apagarlo NO SE PUEDEN MEDIR los
# exports, que son justo los endpoints mas pesados.
# 🟢 El hallazgo que salio de aca YA SE ARREGLO (migracion 115 / sesion del 13-8): la franja
# era `30/hora` keyed POR IP, asi que las 3 personas de RRHH detras de la IP de la oficina
# compartian 30 exports. Ahora es `100/hora POR USUARIO` (`utils/rate_limit.py::limite_export`).
# El apagado sigue haciendo falta igual: 78 requests de export no entran en ninguna franja sana.
limiter.enabled = False

cliente = TestClient(main.app)


def _empresas() -> list:
    """Devuelve (id, nombre, dotacion) de cada empresa, de mayor a menor."""
    emp = supabase_admin.table("empresas").select("id,nombre").execute().data
    out = []
    for e in emp:
        n = supabase_admin.table("empleados").select("id", count="exact") \
            .eq("empresa_id", e["id"]).limit(1).execute().count
        out.append((e["id"], e["nombre"], n))
    return sorted(out, key=lambda x: -x[2])


EMPRESAS = _empresas()
GRANDE = EMPRESAS[0]
CHICA = EMPRESAS[-1]


def medir(path: str, empresa_id, veces: int = 3) -> dict:
    """Pega `veces` al endpoint y devuelve mediana en ms, filas devueltas y status."""
    headers = {"Authorization": "Bearer x",
               "X-Empresa-Id": empresa_id if empresa_id else "todas"}
    tiempos, filas, status, cuerpo = [], None, None, None
    for i in range(veces):
        t0 = time.perf_counter()
        try:
            r = cliente.get(path, headers=headers)
            status = r.status_code
        except Exception as exc:
            # Un endpoint que revienta no puede abortar el barrido: la excepcion ES el dato.
            tiempos.append((time.perf_counter() - t0) * 1000)
            status = f"EXC:{type(exc).__name__}"
            continue
        tiempos.append((time.perf_counter() - t0) * 1000)
        if i == 0:
            try:
                cuerpo = r.json()
            except Exception:
                cuerpo = None
    if isinstance(cuerpo, dict):
        for k in ("data", "items", "resultados", "empleados"):
            if isinstance(cuerpo.get(k), list):
                filas = len(cuerpo[k])
                break
        if filas is None and "total" in cuerpo:
            filas = cuerpo.get("total")
    elif isinstance(cuerpo, list):
        filas = len(cuerpo)
    return {"path": path, "ms": round(statistics.median(tiempos), 1),
            "min": round(min(tiempos), 1), "max": round(max(tiempos), 1),
            "filas": filas, "status": status}


# ── Superficie a medir ────────────────────────────────────────────────────────
# Se descubre por introspeccion de app.routes, no con una lista escrita a mano: asi un
# endpoint nuevo entra solo. Se filtran los GET sin parametros de path (un {id} exigiria
# inventar un recurso, y no es lo que esta sesion mide).
def superficie() -> list:
    """Devuelve los paths GET sin parametros de ruta, montados en la app."""
    vistos = set()
    for r in main.app.routes:
        p = getattr(r, "path", "")
        metodos = getattr(r, "methods", set()) or set()
        if "GET" not in metodos or "{" in p or not p.startswith("/api"):
            continue
        vistos.add(p)
    return sorted(vistos)


PATHS = superficie()

# Endpoints que necesitan parametros obligatorios para no dar 422.
PARAMS = {
    "/api/horas-cliente": "?anio=2026&mes=7",
    "/api/horas-cliente/exportar": "?anio=2026&mes=7&formato=excel",
    "/api/costos/nomina": "?anio=2026&mes=7",
    "/api/costos/nomina/exportar": "?anio=2026&mes=7&formato=excel",
    "/api/costos/presupuesto": "?anio=2026",
}


# ── Contador de queries: el detector de N+1 ───────────────────────────────────
# Un N+1 NO se ve en el tiempo total de una query aislada (son N queries rapidas), y tampoco
# se ve mirando el codigo cuando el loop esta a tres capas del repo. Se ve contando: si el
# numero de requests a PostgREST CRECE con la cantidad de filas, hay un N+1. Por eso cada
# endpoint se mide dos veces —empresa grande y chica— y lo que importa es la DIFERENCIA.
_QUERIES = []


def _instrumentar() -> None:
    """Envuelve la sesion httpx de PostgREST para contar y registrar cada request."""
    ses = supabase_admin._client.postgrest.session
    original = ses.send

    def contando(request, **kw):
        _QUERIES.append(f"{request.method} {request.url.path}?{request.url.query.decode()[:110]}")
        return original(request, **kw)

    ses.send = contando


def contar(path: str, empresa_id) -> dict:
    """Cuenta cuantos requests a PostgREST dispara UN request al endpoint."""
    _QUERIES.clear()
    headers = {"Authorization": "Bearer x",
               "X-Empresa-Id": empresa_id if empresa_id else "todas"}
    try:
        r = cliente.get(path, headers=headers)
        st = r.status_code
    except Exception as exc:
        st = f"EXC:{type(exc).__name__}"
    return {"path": path, "queries": len(_QUERIES), "status": st,
            "detalle": list(_QUERIES)}


def modo_queries() -> None:
    """Compara el numero de queries por endpoint entre la empresa grande y la chica."""
    sys.stdout.reconfigure(encoding="utf-8")
    _instrumentar()
    filas = []
    for p in PATHS:
        q = PARAMS.get(p, "?formato=excel" if p.endswith("exportar") else "")
        g = contar(p + q, GRANDE[0])
        c = contar(p + q, CHICA[0])
        s = contar(p + q, None)
        filas.append((g["queries"], c["queries"], s["queries"], g["status"], p, g["detalle"]))
    filas.sort(key=lambda x: -x[0])
    print(f"{'q400':>5} {'q15':>5} {'qCons':>6} {'st':>4}  path")
    for g, c, s, st, p, _d in filas:
        # Crece con las filas => N+1. Igual en las dos => costo fijo (tambien puede sobrar).
        marca = " N+1" if g > c + 2 else "    "
        print(f"{g:>5} {c:>5} {s:>6} {str(st):>4}{marca}  {p}")
    print("\n# Detalle de los 6 peores:")
    for g, c, s, st, p, d in filas[:6]:
        print(f"\n## {p}  ({g} queries con 400 empleados)")
        vistos = {}
        for linea in d:
            clave = linea.split("?")[0] + "?" + linea.split("?")[1][:60]
            vistos[clave] = vistos.get(clave, 0) + 1
        for clave, n in sorted(vistos.items(), key=lambda x: -x[1])[:8]:
            print(f"   x{n:<5} {clave}")


# ── Largo de URL: el techo que no se ve hasta que revienta ────────────────────
# Los lookups del repo estan BATCHEADOS (`?id=in.(uuid,uuid,...)`), que es lo correcto contra
# el N+1. Pero mueve el costo a otro lado: la lista de ids viaja EN LA URL, y una URL tiene
# techo. Con 31 empleados son 1,1 KB y no se nota; con 1000 son 37 KB.
#
# Umbrales MEDIDOS en esta sesion (no estimados):
#   · PostgREST/warp pelado ....... ~50.900 bytes -> 400 "Bad Request" (cuerpo en texto plano)
#   · nginx con config default ..... ~3.950 bytes -> 502, y arriba de 8 KB -> 414
# Produccion tiene un gateway delante de PostgREST, asi que el techo que manda es el segundo.
_LIMITES = [("nginx-default", 3950), ("nginx-8k", 8192), ("postgrest", 50900)]


def modo_urls() -> None:
    """Reporta el largo de URL MAXIMO que cada endpoint le manda a PostgREST."""
    sys.stdout.reconfigure(encoding="utf-8")
    urls = []
    ses = supabase_admin._client.postgrest.session
    original = ses.send

    def cap(request, **kw):
        urls.append((len(str(request.url)), str(request.url).split("?")[0].split("/")[-1]))
        return original(request, **kw)

    ses.send = cap

    filas = []
    for p in PATHS:
        q = PARAMS.get(p, "?formato=excel" if p.endswith("exportar") else "")
        for etiqueta, eid in (("grande", GRANDE[0]), ("consolidado", None)):
            urls.clear()
            try:
                st = cliente.get(p + q, headers={"Authorization": "Bearer x",
                                                 "X-Empresa-Id": eid or "todas"}).status_code
            except Exception as exc:
                st = f"EXC:{type(exc).__name__}"
            if urls:
                mx = max(urls)
                filas.append((mx[0], mx[1], st, etiqueta, p))
    filas.sort(key=lambda x: -x[0])
    print(f"{'maxURL':>8} {'st':>10}  {'modo':<12} {'tabla':<26} endpoint")
    for n, tabla, st, modo, p in filas:
        if n < 3950:
            continue
        rotos = [e for e, lim in _LIMITES if n > lim]
        print(f"{n:>8} {str(st):>10}  {modo:<12} {tabla:<26} {p}")
        print(f"{'':>8} {'':>10}  pasa el techo de: {', '.join(rotos) if rotos else '-'}")


def corrida(etiqueta: str, empresa_id) -> list:
    """Mide toda la superficie bajo una empresa (o consolidado si empresa_id es None)."""
    res = []
    for p in PATHS:
        q = PARAMS.get(p, "?formato=excel" if p.endswith("exportar") else "")
        m = medir(p + q, empresa_id)
        m["modo"] = etiqueta
        res.append(m)
    return res


def main_() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    """Corre las tres mediciones y las imprime ordenadas de peor a mejor."""
    print(f"# Base local · {len(EMPRESAS)} empresas · "
          f"{sum(e[2] for e in EMPRESAS)} colaboradores", file=sys.stderr)
    print(f"# grande={GRANDE[1]} ({GRANDE[2]}) · chica={CHICA[1]} ({CHICA[2]})", file=sys.stderr)

    todo = []
    todo += corrida(f"empresa_grande({GRANDE[2]})", GRANDE[0])
    todo += corrida(f"empresa_chica({CHICA[2]})", CHICA[0])
    todo += corrida("consolidado(10)", None)

    if "--json" in sys.argv:
        print(json.dumps(todo, indent=1))
        return

    todo.sort(key=lambda x: -x["ms"])
    print(f"{'ms':>8} {'filas':>7} {'st':>4}  {'modo':<22} path")
    for m in todo:
        marca = " !!" if m["ms"] >= 1000 else ("  ." if m["ms"] >= 300 else "   ")
        print(f"{m['ms']:>8} {str(m['filas']):>7} {m['status']:>4}{marca} "
              f"{m['modo']:<22} {m['path']}")


if __name__ == "__main__":
    if "--queries" in sys.argv:
        modo_queries()
    elif "--urls" in sys.argv:
        modo_urls()
    else:
        main_()
