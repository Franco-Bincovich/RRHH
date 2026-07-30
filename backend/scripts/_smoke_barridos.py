"""
Los barridos del smoke test: auth, rutas públicas y todos los GET.

Separado de `smoke_test.py` (que quedó como CLI + reporte) por el límite de 200 líneas. Acá vive
todo lo que EMITE requests; el módulo de arriba solo orquesta y escribe.

🔴 CERO ESCRITURAS. La única función que emite algo distinto de GET es `barrer_auth`, y lo hace
SIN TOKEN a propósito: el AuthMiddleware responde 401 antes de enrutar, así que ningún handler
llega a ejecutarse y nada puede persistir. Está explicado en su docstring y no se relaja.
"""
import time
from typing import Dict, List, Optional

import httpx

from scripts import _smoke_reporte as rep
from scripts import _smoke_rutas as rt


def get(cli: httpx.Client, path: str, token: Optional[str], empresa: Optional[str]) -> tuple:
    """GET a un endpoint. Devuelve (status, segundos, payload | None)."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if empresa:
        headers["X-Empresa-Id"] = empresa
    t0 = time.monotonic()
    try:
        r = cli.get(path, headers=headers)
    except Exception as exc:  # noqa: BLE001 — un fallo de red es un dato, no un crash del script
        return None, time.monotonic() - t0, {"_error": str(exc)}
    seg = time.monotonic() - t0
    try:
        return r.status_code, seg, r.json()
    except Exception:  # noqa: BLE001 — los exports devuelven bytes, no JSON
        return r.status_code, seg, {"_bytes": len(r.content), "_tipo": r.headers.get("content-type", "")}


def _filas(payload) -> Optional[int]:
    """Cuántos elementos trae una respuesta de listado. None si no es una lista."""
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            return len(payload["items"])
        return None
    return len(payload) if isinstance(payload, list) else None


def verificar_token(cli: httpx.Client, token: str) -> None:
    """Falla RUIDOSO si el token no sirve. Sin esto, un token vencido reportaría 90 endpoints
    caídos y el reporte sería basura que además asusta."""
    status, _, _ = get(cli, "/api/empresas", token, None)
    if status in (401, 403):
        raise SystemExit(
            f"ABORTADO: el token no es válido (el backend respondió {status}).\n"
            "Conseguí uno nuevo — ver 'Cómo obtener el token' en docs/SMOKE-TEST.md."
        )
    if status is None or status >= 500:
        raise SystemExit(f"ABORTADO: el backend no responde correctamente (status {status}).")


def barrer_auth(cli: httpx.Client, rutas: List[rt.Ruta]) -> List[rep.Resultado]:
    """Cada endpoint SIN token → 401. Chequeo de RUNTIME, distinto del barrido estático de Fase 2.

    Incluye las rutas de escritura y es seguro: el 401 lo produce el AuthMiddleware antes de
    enrutar, así que ningún handler llega a ejecutarse. Se manda sin body por las dudas.
    """
    out: List[rep.Resultado] = []
    for r in rutas:
        if r.path in rt.PUBLICAS:
            continue
        if not rt.esta_publicada(r.path):
            out.append(rep.Resultado(r.metodo, r.path, "auth", rep.NO_PROBADO, None, None,
                                     "la plataforma no enruta este path (ver vercel.json)"))
            continue
        t0 = time.monotonic()
        try:
            resp = cli.request(r.metodo, rt.sustituir_param(r.path, "00000000-0000-0000-0000-000000000000"))
            status, seg = resp.status_code, time.monotonic() - t0
        except Exception as exc:  # noqa: BLE001
            out.append(rep.Resultado(r.metodo, r.path, "auth", rep.ROTO, None, None, f"red: {exc}"))
            continue
        if status == 401:
            out.append(rep.Resultado(r.metodo, r.path, "auth", rep.OK, status, seg, "401 sin token"))
        else:
            out.append(rep.Resultado(r.metodo, r.path, "auth", rep.ROTO, status, seg,
                                     f"sin token devolvió {status}, no 401 — endpoint DESPROTEGIDO"))
    return out


def barrer_publicas(cli: httpx.Client) -> List[rep.Resultado]:
    """Las rutas declaradas públicas tienen que seguir siendo alcanzables sin token."""
    out: List[rep.Resultado] = []
    for path in sorted(rt.PUBLICAS):
        status, seg, _ = get(cli, path, None, None)
        # Una pública alcanzable responde CUALQUIER COSA menos 401/403. `/api/auth/login` por GET
        # da 405 (solo acepta POST) y eso es correcto: prueba que el middleware la dejó pasar y
        # que el 405 lo puso el router. Lo que sí sería un hallazgo es un 401.
        ok = status is not None and status not in (401, 403)
        out.append(rep.Resultado("GET", path, "publicas", rep.OK if ok else rep.ROTO, status, seg,
                                 f"alcanzable sin token ({status})" if ok
                                 else f"declarada pública pero devolvió {status}"))
    return out


def barrer_gets(cli: httpx.Client, rutas: List[rt.Ruta], token: str, empresa: Optional[str],
                conteos: Optional[Dict[str, int]], tablas: Dict[str, str]) -> List[rep.Resultado]:
    """Todos los GET, con y sin X-Empresa-Id. Resuelve un id real para los de detalle."""
    out: List[rep.Resultado] = []
    cache_id: Dict[str, Optional[str]] = {}
    for r in [x for x in rutas if x.es_get]:
        if not rt.esta_publicada(r.path):
            out.append(rep.Resultado(r.metodo, r.path, r.modulo, rep.NO_PROBADO, None, None,
                                     "la plataforma no enruta este path (ver vercel.json)"))
            continue
        path = r.path
        if r.tiene_param:
            lista = rt.listado_de(r.path)
            if lista is None:
                out.append(rep.Resultado(r.metodo, r.path, r.modulo, rep.NO_PROBADO, None, None,
                                         "no se pudo deducir de qué listado sacar un id"))
                continue
            if lista not in cache_id:
                _, _, pay = get(cli, lista, token, empresa)
                cache_id[lista] = rt.extraer_id(pay)
            ident = cache_id[lista]
            if not ident:
                out.append(rep.Resultado(r.metodo, r.path, r.modulo, rep.NO_PROBADO, None, None,
                                         f"`{lista}` no tiene filas — sin id real que probar"))
                continue
            path = rt.sustituir_param(r.path, ident)

        for etiqueta, emp in (("empresa", empresa), ("consolidado", None)):
            if etiqueta == "empresa" and not empresa:
                continue
            status, seg, pay = get(cli, path, token, emp)
            if status is None:
                out.append(rep.Resultado(r.metodo, f"{r.path} [{etiqueta}]", r.modulo, rep.ROTO,
                                         None, seg, f"sin respuesta: {pay.get('_error', '')[:60]}"))
                continue
            filas = _filas(pay)
            veredicto, detalle = rep.clasificar_get(status, seg, filas, tablas.get(r.path), conteos, pay)
            if r.es_export and status == 200:
                veredicto, detalle = rep.OK, f"archivo de {pay.get('_bytes', 0)} bytes ({pay.get('_tipo','')[:40]})"
            out.append(rep.Resultado(r.metodo, f"{r.path} [{etiqueta}]", r.modulo,
                                     veredicto, status, seg, detalle))
    return out
