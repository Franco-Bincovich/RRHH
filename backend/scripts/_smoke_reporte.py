"""
Clasificación de resultados y salida del smoke test.

🔴 LA DISTINCIÓN QUE HACE HONESTO AL REPORTE ES `NO_PROBADO` vs `OK`. Un endpoint de detalle al
que no se le pudo resolver un id NO está OK: está sin ejercitar. Marcarlo verde es exactamente
cómo un reporte de humo se vuelve un papel que nadie puede usar.

Y la segunda: un 200 con lista vacía puede ser "no hay datos" o "está roto". Se resuelve
cruzando contra el conteo real de la tabla (--conteos); sin ese dato el veredicto es SOSPECHOSO,
nunca OK.
"""
from typing import Dict, List, NamedTuple, Optional

ROTO, SOSPECHOSO, NO_PROBADO, OK = "ROTO", "SOSPECHOSO", "NO_PROBADO", "OK"
ICONO = {ROTO: "🔴", SOSPECHOSO: "⚠️", NO_PROBADO: "⬜", OK: "✅"}

# Un GET que tarda más que esto se marca SOSPECHOSO aunque devuelva 200. No es el timeout de
# nadie: es el umbral a partir del cual conviene mirarlo antes de que RRHH lo sufra.
UMBRAL_LENTO_S = 3.0


class Resultado(NamedTuple):
    metodo: str
    path: str
    modulo: str
    veredicto: str
    status: Optional[int]
    segundos: Optional[float]
    detalle: str          # por qué este veredicto, en una línea

    @property
    def icono(self) -> str:
        return ICONO[self.veredicto]


def params_faltantes(payload) -> str:
    """Nombres de los query params requeridos que el endpoint reclama en un 422 de FastAPI."""
    detalle = payload.get("detail") if isinstance(payload, dict) else None
    if not isinstance(detalle, list):
        return ""
    return ", ".join(
        str(d.get("loc", ["?"])[-1]) for d in detalle
        if isinstance(d, dict) and d.get("type") == "missing")


def clasificar_get(status: int, segundos: float, filas: Optional[int],
                   tabla: Optional[str], conteos: Optional[Dict[str, int]],
                   payload=None) -> tuple:
    """Veredicto de un GET. Devuelve (veredicto, detalle).

    `filas` es la cantidad de elementos que devolvió (None si la respuesta no es una lista).
    `tabla`/`conteos` permiten distinguir "vacío legítimo" de "vacío roto".
    """
    if status == 422:
        # 🔴 NO es un endpoint roto: es un endpoint que el smoke NO SABE llamar. FastAPI devuelve
        # 422 cuando falta un query param REQUERIDO, y el script no los provee. Marcarlo ROTO
        # llenó la primera corrida de falsos positivos; marcarlo OK sería peor. Es NO PROBADO.
        faltan = params_faltantes(payload)
        return NO_PROBADO, f"requiere params que el smoke no provee: {faltan or '(ver detail)'}"

    if status >= 500:
        # Un 5xx CON el contrato de error de la app ({error, message, code}) y un code de negocio
        # es una condición manejada —"Google OAuth no está configurado"—, no un crash. Un
        # INTERNAL_ERROR (o un 5xx sin contrato) sí es una excepción no atrapada.
        code = payload.get("code") if isinstance(payload, dict) else None
        if code and code != "INTERNAL_ERROR":
            return SOSPECHOSO, f"{status} manejado: `{code}` — condición de negocio, no un crash"
        return ROTO, f"{status} del servidor — excepción no atrapada"
    if status == 429:
        # El propio barrido agota la franja de rate limit: los exports comparten 30/hora
        # (`scope="export"`) y el smoke pega a 12 × 2 modos = 24 por corrida. Dos corridas en la
        # misma hora lo pasan. NO es un endpoint roto: es el smoke chocando con su propio techo.
        return NO_PROBADO, "429: el barrido agotó la franja de rate limit (ver 'Limitaciones')"
    if status in (401, 403):
        return ROTO, f"{status} con token válido — el gate rechaza a un admin_rrhh"
    if status == 404:
        return ROTO, "404 sobre un id sacado del propio listado"
    if status >= 400:
        return ROTO, f"{status} inesperado"

    if filas == 0:
        n = (conteos or {}).get(tabla or "")
        if n:
            return ROTO, f"devolvió vacío con {n} filas en `{tabla}`"
        if n == 0:
            return OK, f"vacío coherente: `{tabla}` tiene 0 filas"
        return SOSPECHOSO, "vacío y no hay conteo para confirmar si es normal"

    if segundos > UMBRAL_LENTO_S:
        return SOSPECHOSO, f"responde en {segundos:.1f}s"
    return OK, f"{filas} elemento(s)" if filas is not None else "respuesta no-lista"


def resumen(resultados: List[Resultado]) -> Dict[str, int]:
    """Conteo por veredicto, para el encabezado del reporte."""
    return {v: sum(1 for r in resultados if r.veredicto == v) for v in (ROTO, SOSPECHOSO, NO_PROBADO, OK)}


def tabla_markdown(resultados: List[Resultado]) -> str:
    """Tabla de resultados agrupada por módulo."""
    lineas: List[str] = []
    for modulo in sorted({r.modulo for r in resultados}):
        delmod = [r for r in resultados if r.modulo == modulo]
        rotos = sum(1 for r in delmod if r.veredicto == ROTO)
        marca = " 🔴" if rotos else ""
        lineas.append(f"\n### `{modulo}` — {len(delmod)} endpoint(s){marca}\n")
        lineas.append("| | Método | Endpoint | Status | Tiempo | Detalle |")
        lineas.append("|---|---|---|---|---|---|")
        for r in sorted(delmod, key=lambda x: (x.veredicto != ROTO, x.path)):
            t = f"{r.segundos:.2f}s" if r.segundos is not None else "—"
            lineas.append(
                f"| {r.icono} | {r.metodo} | `{r.path}` | {r.status or '—'} | {t} | {r.detalle} |")
    return "\n".join(lineas)


def top_lentos(resultados: List[Resultado], n: int = 10) -> str:
    """Los N endpoints más lentos. Primera medición real de performance del repo."""
    con_tiempo = [r for r in resultados if r.segundos is not None]
    top = sorted(con_tiempo, key=lambda r: r.segundos or 0, reverse=True)[:n]
    lineas = ["| # | Endpoint | Tiempo | Veredicto |", "|---|---|---|---|"]
    for i, r in enumerate(top, 1):
        lineas.append(f"| {i} | `{r.metodo} {r.path}` | **{r.segundos:.2f}s** | {r.icono} |")
    return "\n".join(lineas)


def hallazgos(resultados: List[Resultado]) -> str:
    """Los ROTO y SOSPECHOSO, ordenados por gravedad. Vacío = nada que reportar."""
    lineas: List[str] = []
    for veredicto in (ROTO, SOSPECHOSO):
        delv = [r for r in resultados if r.veredicto == veredicto]
        if not delv:
            continue
        lineas.append(f"\n### {ICONO[veredicto]} {veredicto} — {len(delv)}\n")
        for r in sorted(delv, key=lambda x: x.path):
            lineas.append(f"- **`{r.metodo} {r.path}`** — {r.detalle}")
    return "\n".join(lineas) if lineas else "\nNinguno.\n"


def imprimir_consola(resultados: List[Resultado], res: Dict[str, int]) -> None:
    """Salida corta a stdout, para cuando se corre a mano."""
    for r in resultados:
        if r.veredicto in (ROTO, SOSPECHOSO):
            t = f"{r.segundos:.2f}s" if r.segundos is not None else "—"
            print(f"  {r.icono} {r.metodo:6} {r.path:60} {r.status or '—':>4}  {t:>7}  {r.detalle}")
    print(f"\n  {ICONO[ROTO]} {res[ROTO]} roto(s) · {ICONO[SOSPECHOSO]} {res[SOSPECHOSO]} sospechoso(s) "
          f"· {ICONO[NO_PROBADO]} {res[NO_PROBADO]} no probado(s) · {ICONO[OK]} {res[OK]} ok")
