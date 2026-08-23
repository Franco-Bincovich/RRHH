"""
MAPA `función de services/ -> (MÉTODO, path)`. Es la pieza que le pone nombre y método a cada
llamada del front, y sin ella no hay forma de decir qué endpoint dispara una pantalla ni qué
escritura hay detrás de un botón.

🔴 LA COMPOSICIÓN ENTRE FUNCIONES NO ES UN DETALLE: sin resolverla se pierden escrituras
REALES, no wrappers. Medido en este repo:
  · `crearAusenciaConAdjuntos` no escribe ningún literal: llama a `createAusencia` (POST) y a
    `subirAdjunto` (POST multipart). Es la función que usa el modal de alta de ausencias, o sea
    que sin composición la ÚNICA alta de ausencias con adjuntos queda fuera del inventario.
  · `fetchEmpleadosLideres` / `fetchEmpleadosTodos` delegan en un helper privado del archivo.
Se resuelve a punto fijo (3 vueltas alcanzan y sobran: la cadena más larga medida es de 2).

🔴 Y SE RESUELVE POR ARCHIVO, NO POR NOMBRE GLOBAL, porque los nombres CHOCAN: `fetchClientes`
existe en `services/clientes.ts` (catálogo interno, con auth) y en `services/horasPublico.ts`
(link público, con token de sesión de horas). Emparejar por nombre a secas le atribuiría al link
público el endpoint interno — y al revés. Los candidatos de un archivo son los que ese archivo
DEFINE más los que IMPORTA, que es exactamente lo que TypeScript resuelve.

⚠️ LO QUE NO VE, y sobre-cuenta en vez de sub-contar (da por vivo algo muerto, nunca al revés):
una llamada dentro de un `if` inalcanzable cuenta igual, y un path que el front arme fuera de un
literal (concatenación con `+`, o un id que venga de una variable con el prefijo partido) no se
ve. No hay ninguno hoy: las 258 funciones con endpoint salen de literales.
"""
import re
from functools import lru_cache
from typing import Dict, List, Set, Tuple

from _inv_front import (archivos, cerrar, codigo, cuerpo_de_funcion, destino, normalizar)

_RE_EXPORT = re.compile(r"^export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.M)
_RE_FN = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.M)
_RE_LIT = re.compile(r"""["'`]([^"'`\n]*/api/[^"'`\n]*)["'`]""")
_RE_METHOD = re.compile(r"""method:\s*["'`](\w+)["'`]""")
_RE_CONST = re.compile(r"""const\s+([A-Za-z_$][\w$]*)\s*=\s*["'`]([^"'`]*)["'`]""")
_RE_INTERP = re.compile(r"\$\{([A-Za-z_$][\w$]*)\}")
_RE_IMPORT = re.compile(r"""import\s+(?:type\s+)?\{([^}]*)\}\s+from\s+["']([^"']+)["']""")

# Helpers de `services/api.ts` que fijan el método sin escribir `method:` en la llamada.
_HELPERS_POST = ("subirArchivo", "postMultipart")

# 🔴 LA COMPOSICIÓN NO ATRAVIESA EL INTERCEPTOR, y sin este corte el mapa MIENTE en 20 filas.
# `descargarArchivo` llama a `conRefresh`, que llama a `refreshSession`, que hace
# `POST /api/auth/refresh`. Propagando eso, las VEINTE funciones `exportarX` del front —que son
# lecturas -- aparecían como escrituras a `/api/auth/refresh`, y el inventario de acciones se
# llenaba de renovaciones de token que ningún botón dispara a propósito.
# El refresh es plomería de transporte: lo dispara CUALQUIER llamada cuyo token venció, no la
# feature. Sigue teniendo su propia fila (`refreshSession`, con /login como pantalla), que es
# donde corresponde probarlo.
_NO_PROPAGAN = ("services/authRefresh.ts",)

Clave = Tuple[str, str]        # (archivo, nombre de la función)
Llamada = Tuple[str, str]      # (MÉTODO, path normalizado)


def _metodo(cuerpo: str, fin: int, inicio: int) -> str:
    """Método de ESA llamada: el objeto de opciones que la sigue, o el helper que la envuelve.

    🔴 Por brace matching y no por "buscar `method:` en los próximos N caracteres": esa ventana
    se mete en la función siguiente. Es el falso positivo 5 de `tests/_barrido_callers.py`, que
    ahí marcaba `GET /api/areas` como muerto por alcanzar el `method: "POST"` de 9 líneas abajo.
    """
    m = re.match(r"\s*,\s*\{", cuerpo[fin:fin + 200])
    if m:
        ini = fin + m.end() - 1
        hallado = _RE_METHOD.search(cuerpo[ini:cerrar(cuerpo, ini, "{", "}") + 1])
        if hallado:
            return hallado.group(1).upper()
    antes = cuerpo[max(0, inicio - 80):inicio]
    if re.search(r"(" + "|".join(_HELPERS_POST) + r")\s*<?[^<>()]*>?\s*\($", antes):
        return "POST"
    return "GET"


def _consts(src: str) -> Dict[str, str]:
    """Los const string del módulo, ya resueltos entre sí (uno se apoya en otro)."""
    consts = dict(_RE_CONST.findall(src))
    for _ in range(3):
        consts = {k: _RE_INTERP.sub(lambda m: consts.get(m.group(1), m.group(0)), v)
                  for k, v in consts.items()}
    return consts


def _directas(cuerpo: str, consts: Dict[str, str]) -> Set[Llamada]:
    """Las llamadas que ESTE cuerpo escribe como literal, ya con los const sustituidos."""
    cuerpo = _RE_INTERP.sub(lambda x: consts.get(x.group(1), x.group(0)), cuerpo)
    for k, v in consts.items():                                   # `apiFetch(BASE, {...})`
        if v.startswith("/api"):
            cuerpo = re.sub(r"\(\s*" + re.escape(k) + r"\s*(?=[,)])", '("' + v + '"', cuerpo)
    out: Set[Llamada] = set()
    for lit in _RE_LIT.finditer(cuerpo):
        crudo = lit.group(1)
        corte = crudo.find("/api/")
        path = normalizar(crudo[corte:] if corte > 0 else crudo)
        if path.startswith("/api"):
            out.add((_metodo(cuerpo, lit.end(), lit.start()), path))
    return out


@lru_cache(maxsize=1)
def funciones_importadas() -> Dict[str, Set[Clave]]:
    """archivo -> {(archivo de services, función)} que ese archivo importa POR NOMBRE."""
    out: Dict[str, Set[Clave]] = {}
    for f in archivos():
        for m in _RE_IMPORT.finditer(codigo(f)):
            dest = destino(f, m.group(2))
            if not dest or not dest.startswith("services/"):
                continue
            for bruto in m.group(1).split(","):
                nombre = bruto.strip().split(" as ")[0].strip()
                if nombre and not nombre.startswith("type "):
                    out.setdefault(f, set()).add((dest, nombre))
    return out


@lru_cache(maxsize=1)
def _todas() -> Tuple[Dict[Clave, Set[Llamada]], Dict[Clave, str]]:
    """(llamadas por función, cuerpo por función) sobre TODA función de `services/`, privada
    incluida: las privadas no van al inventario, pero son eslabones de la composición."""
    llamadas: Dict[Clave, Set[Llamada]] = {}
    cuerpos: Dict[Clave, str] = {}
    for f in archivos():
        if not f.startswith("services/"):
            continue
        src = codigo(f)
        consts = _consts(src)
        for m in _RE_FN.finditer(src):
            cuerpo = cuerpo_de_funcion(src, m.end())
            clave = (f, m.group(1))
            cuerpos[clave] = cuerpo
            llamadas[clave] = _directas(cuerpo, consts)
    return llamadas, cuerpos


@lru_cache(maxsize=1)
def llamadas_por_funcion() -> Dict[Clave, List[Llamada]]:
    """(archivo, función EXPORTADA) -> [(MÉTODO, path)], con la composición ya resuelta."""
    llamadas, cuerpos = _todas()
    por_archivo: Dict[str, Set[str]] = {}
    for f, nombre in llamadas:
        por_archivo.setdefault(f, set()).add(nombre)
    importadas = funciones_importadas()
    for _ in range(3):                                            # punto fijo
        for clave, cuerpo in cuerpos.items():
            f = clave[0]
            candidatas = {(f, n) for n in por_archivo.get(f, set())}
            candidatas |= importadas.get(f, set())
            candidatas = {c for c in candidatas if c[0] not in _NO_PROPAGAN}
            for cand in candidatas:
                if cand != clave and re.search(r"\b" + re.escape(cand[1]) + r"\s*\(", cuerpo):
                    llamadas[clave] |= llamadas.get(cand, set())
    return {c: sorted(v) for c, v in llamadas.items()
            if v and _RE_EXPORT.search(codigo(c[0]) or "") and
            re.search(r"^export\s+(?:async\s+)?function\s+" + re.escape(c[1]) + r"\b",
                      codigo(c[0]), re.M)}
