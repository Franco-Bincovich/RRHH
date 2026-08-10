"""
Motor del barrido de símbolos y endpoints sin caller. HELPER, no test (molde:
`tests/_postgrest_schema.py`). El test que lo consume es `test_callers_huerfanos.py`.

🔑 LA ASIMETRÍA ES DELIBERADA: **AST preciso para las DEFINICIONES, conjunto generoso de nombres
para las REFERENCIAS.** Definir mal sobra símbolos; contar callers de menos inventa huérfanos.
Al sobre-contar callers (cuenta cualquier aparición del nombre, no solo la llamada real), lo que
IGUAL sale sin caller lo está de verdad. Un barrido que se equivoca en la dirección contraria
produce una lista de falsos que nadie mira, y a los dos meses está desactivada.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? Los siete falsos positivos de abajo
son REALES: cada uno se midió contra este repo y el número entre paréntesis es cuántos huérfanos
falsos producía antes de cubrirlo. Sin ellos el barrido nace en rojo con ~48 falsos y se apaga.

  1. USO INTRA-MÓDULO (20). Un helper público usado solo dentro de su archivo NO está muerto:
     es un nombre al que le falta el guion bajo. Se cuenta `intra` aparte y se lo da por vivo.
  2. IMPORT CON ALIAS (8). `from x import es_update_sin_cambios as _es_update_sin_cambios`: el
     nombre original nunca vuelve a aparecer. Se mapea alias → original.
  3. `${API_BASE}` COMO PREFIJO (7). El front escribe `${API_BASE}/api/empleados`; filtrar por
     "empieza con /api" lo descartaba. Se recorta todo lo previo al primer `/api/`.
  4. SUFIJO DE QUERYSTRING. `` `${BASE}/lotes/${id}/evaluados${qs}` `` normaliza a
     `.../evaluados{}` y no matchea `.../evaluados`. Se poda el `{}` final que no sigue a `/`.
  5. MÉTODO POR PROXIMIDAD. Buscar `method:` en una ventana de N caracteres se mete en la
     función siguiente: marcaba `GET /api/areas` como muerto porque alcanzaba el `method: "POST"`
     de 9 líneas abajo. Se parsea el objeto de opciones de ESA llamada con brace matching.
  6. CONST DESNUDO COMO ARGUMENTO (13). `apiFetch<T>(BASE, {method: "POST"})`: el path no aparece
     como literal. Se sustituyen los const cuyo valor arranca en `/api`.
  7. FAKES DE TEST QUE REDEFINEN EL NOMBRE. `test_google_scopes.py` define
     `class _Remitente: def set_remitente(...)`. Contado por nombre, ese fake se leía como
     "caller en tests" del símbolo REAL — justo la categoría que este barrido existe para
     detectar. Por eso de un archivo de test se restan los nombres que ese archivo DEFINE.
"""
import ast
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_BACKEND = Path(__file__).resolve().parent.parent
_FRONT = _BACKEND.parent / "frontend"
_IGNORADOS = {"venv", ".venv", "__pycache__", "migrations", "node_modules", ".next", ".git"}
_BAJO_BARRIDO = ("services", "repositories")


def _archivos_py() -> List[Path]:
    return [p for p in _BACKEND.rglob("*.py") if not _IGNORADOS & set(p.relative_to(_BACKEND).parts)]


def _rel(p: Path) -> str:
    return p.relative_to(_BACKEND).as_posix()


def _es_test(p: Path) -> bool:
    return "tests" in p.relative_to(_BACKEND).parts


def _definiciones(tree: ast.Module) -> List[Tuple[str, str, str, int]]:
    """(kind, qualname, nombre, línea) de los símbolos PÚBLICOS de un módulo.

    Público = sin guion bajo inicial. Incluye métodos (set_remitente era uno) y constantes de
    módulo en MAYÚSCULAS. `__init__` y los dunder quedan afuera: nadie los llama por nombre.
    """
    out: List[Tuple[str, str, str, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            out.append(("func", node.name, node.name, node.lineno))
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                out.append(("class", node.name, node.name, node.lineno))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("_"):
                    out.append(("method", f"{node.name}.{sub.name}", sub.name, sub.lineno))
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("_") and t.id.isupper():
                    out.append(("const", t.id, t.id, node.lineno))
    return out


def _nombres_definidos(tree: ast.Module) -> Set[str]:
    """Todo nombre que este módulo DEFINE (falso positivo 7)."""
    out: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.Assign):
            out |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    return out


def _usos(tree: ast.Module) -> List[Tuple[str, int]]:
    """(nombre, línea) de cada referencia. Generoso a propósito: `Name`, `Attribute` y strings
    literales — los strings cubren `getattr("x")` y los registries por clave."""
    out: List[Tuple[str, int]] = []
    alias: Dict[str, str] = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.append((a.name.split(".")[-1], n.lineno))
                if a.asname:
                    alias[a.asname] = a.name.split(".")[-1]
        elif isinstance(n, ast.Name):
            out.append((n.id, n.lineno))
        elif isinstance(n, ast.Attribute):
            out.append((n.attr, n.lineno))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append((n.value, n.lineno))
    usados = {nombre for nombre, _ in out}
    out += [(orig, 0) for al, orig in alias.items() if al in usados]  # falso positivo 2
    return out


@lru_cache(maxsize=1)
def _indice() -> Tuple[dict, dict, dict]:
    """(usos_por_archivo, defs_por_archivo, definidos_por_archivo)."""
    usos, defs, definidos = {}, {}, {}
    for p in _archivos_py():
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        usos[p] = _usos(tree)
        definidos[p] = _nombres_definidos(tree)
        if p.parent.name != "tests" and p.name != "__init__.py" and \
                set(p.relative_to(_BACKEND).parts) & set(_BAJO_BARRIDO):
            defs[p] = _definiciones(tree)
    return usos, defs, definidos


@lru_cache(maxsize=1)
def clasificar_simbolos() -> Tuple[List[str], List[str], int]:
    """(sin_ningun_caller, solo_callers_en_tests, total_barrido). Clave: `ruta::qualname`."""
    usos, defs, definidos = _indice()
    # nombre → archivos que lo referencian (de un test se restan los nombres que ese test DEFINE)
    ref_prod: Dict[str, Set[Path]] = {}
    ref_test: Dict[str, Set[Path]] = {}
    for p, lista in usos.items():
        destino = ref_test if _es_test(p) else ref_prod
        propios = definidos[p] if _es_test(p) else set()      # falso positivo 7
        for nombre, _ in lista:
            if nombre not in propios:
                destino.setdefault(nombre, set()).add(p)
    huerfanos, solo_tests, total = [], [], 0
    for p, lista in defs.items():
        for _kind, qual, sym, linea in lista:
            total += 1
            clave = f"{_rel(p)}::{qual}"
            intra = any(n == sym and ln != linea for n, ln in usos[p])   # falso positivo 1
            if intra or (ref_prod.get(sym, set()) - {p}):
                continue
            (solo_tests if (ref_test.get(sym, set()) - {p}) else huerfanos).append(clave)
    return sorted(huerfanos), sorted(solo_tests), total


# ── Endpoints ────────────────────────────────────────────────────────────────

_CONST = re.compile(r'const\s+([A-Za-z_$][\w$]*)\s*=\s*["\'`]([^"\'`]*)["\'`]')
_LITERAL = re.compile(r'["\'`]([^"\'`\n]*/api/[^"\'`\n]*)["\'`]')
_METHOD = re.compile(r'method:\s*["\'`](\w+)["\'`]')
_HELPERS_POST = {"subirArchivo", "postMultipart"}


def _expandir(valor: str, consts: Dict[str, str]) -> str:
    for k, v in consts.items():
        valor = valor.replace("${" + k + "}", v)
    return valor


def _norm(path: str) -> str:
    """Normaliza los dos lados al mismo alfabeto: segmentos dinámicos → `{}`."""
    path = path.split("?")[0].split("#")[0]
    path = re.sub(r"\$\{[^}]*\}", "{}", path)
    path = re.sub(r"\{[^}]*\}", "{}", path)
    path = re.sub(r"([^/])\{\}$", r"\1", path)          # falso positivo 4
    return path[:-1] if len(path) > 1 and path.endswith("/") else path


def _metodo_de_opciones(src: str, fin: int) -> Optional[str]:
    """Método del objeto de opciones de ESA llamada, por brace matching (falso positivo 5)."""
    i = fin
    while i < len(src) and src[i].isspace():
        i += 1
    if i >= len(src) or src[i] != ",":
        return None
    i += 1
    while i < len(src) and src[i].isspace():
        i += 1
    if i >= len(src) or src[i] != "{":
        return None
    profundidad, j = 0, i
    while j < len(src):
        if src[j] == "{":
            profundidad += 1
        elif src[j] == "}":
            profundidad -= 1
            if profundidad == 0:
                break
        j += 1
    hallado = _METHOD.search(src[i:j + 1])
    return hallado.group(1).upper() if hallado else None


def _helper_envolvente(src: str, inicio: int) -> Optional[str]:
    """Identificador de la función que envuelve al literal (`subirArchivo(...)` ⇒ POST)."""
    k = inicio - 1
    while k >= 0 and src[k].isspace():
        k -= 1
    if k < 0 or src[k] != "(":
        return None
    hallado = re.search(r"([A-Za-z_$][\w$]*)\s*<?[^<>()]*>?\s*$", src[max(0, k - 60):k])
    return hallado.group(1) if hallado else None


@lru_cache(maxsize=1)
def paths_del_front() -> Set[Tuple[str, str]]:
    """(path_normalizado, MÉTODO) de cada llamada al backend que hace el front."""
    encontrados: Set[Tuple[str, str]] = set()
    for f in _FRONT.rglob("*.ts*"):
        if _IGNORADOS & set(f.relative_to(_FRONT).parts) or f.suffix not in (".ts", ".tsx"):
            continue
        src = f.read_text(encoding="utf-8", errors="ignore")
        consts = dict(_CONST.findall(src))
        # Un const se puede apoyar en otro (`const BASE_AS = `${BASE}/asignaciones``): hay que
        # resolver los VALORES entre sí antes de usarlos, o se inyecta un `${BASE}` sin expandir
        # y el path se descarta por no empezar en /api.
        for _ in range(3):
            consts = {k: _expandir(v, consts) for k, v in consts.items()}
        for _ in range(3):
            for k, v in consts.items():
                src = src.replace("${" + k + "}", v)
        for k, v in consts.items():                                     # falso positivo 6
            if v.startswith("/api"):
                src = re.sub(r"\(\s*" + re.escape(k) + r"\s*(?=[,)])", '("' + v + '"', src)
        for m in _LITERAL.finditer(src):
            crudo = m.group(1)
            corte = crudo.find("/api/")
            path = _norm(crudo[corte:] if corte > 0 else crudo)         # falso positivo 3
            if not path.startswith("/api"):
                continue
            metodo = _metodo_de_opciones(src, m.end())
            if metodo is None:
                metodo = "POST" if _helper_envolvente(src, m.start()) in _HELPERS_POST else "GET"
            encontrados.add((path, metodo))
    return encontrados


def _rutas_de(app) -> Set[Tuple[str, str]]:
    """(MÉTODO, path) de las rutas de UNA app. Introspección, nunca una lista."""
    from fastapi.routing import APIRoute
    return {
        (m, r.path)
        for r in app.routes if isinstance(r, APIRoute)
        for m in r.methods if m not in ("HEAD", "OPTIONS")
    }


@lru_cache(maxsize=1)
def rutas_backend() -> List[Tuple[str, str]]:
    """(MÉTODO, path) de TODA la superficie HTTP, INCLUIDA la que hoy está apagada por un flag.

    🔴 ESTE BARRIDO ERA CIEGO A LOS MÓDULOS GATEADOS POR FLAG, y no en teoría: `main.app` se
    construye con la config por DEFAULT, donde `HORAS_PUBLICO_ENABLED` y `ASSESSMENT_ENABLED`
    están en False y sus routers NO SE MONTAN. Medido: con el default veía 0 de las 3 rutas del
    link público de horas y 0 de las 7 de assessment. Consecuencia concreta — el link público se
    construyó ENTERO (tres endpoints, cinco sesiones) sin una sola pantalla que lo llamara, y
    este barrido, que existe exactamente para detectar eso, nunca dio rojo.

    Un endpoint apagado sigue siendo un endpoint que alguien va a tener que llamar algún día, o
    declarar como excepción con su razón. Apagarlo no lo exime del barrido: lo esconde.

    LA CORRECCIÓN es genérica y no nombra ningún flag: se enciende TODO campo de `Settings` que
    termine en `_enabled` y se arma una app aparte con `registrar()`. Un módulo gateado que se
    agregue mañana entra solo — que es la propiedad que el barrido ya tenía para los módulos NO
    gateados y que le faltaba para estos.

    ⚠️ NO se recarga `main`: se construye una app NUEVA. Reloadear el módulo global dejaría
    `main.app` en un estado distinto para los tests que corran después (varios lo reconstruyen
    ellos mismos en fixtures), y el resultado dependería del orden de la suite.

    ⚠️ Se UNE con las rutas de `main.app` porque `/health` se declara ahí y no en `registrar()`.
    Sin la unión desaparecería de la superficie y su excepción declarada quedaría "muerta",
    rompiendo el chequeo de la dirección inversa.
    """
    from fastapi import FastAPI

    from config.settings import settings
    from main import app as app_real
    from registro_routers import registrar

    flags = [n for n in type(settings).model_fields if n.endswith("_enabled")]
    previos = {n: getattr(settings, n) for n in flags}
    try:
        for n in flags:
            setattr(settings, n, True)
        completa = FastAPI()
        registrar(completa)
        rutas = _rutas_de(completa) | _rutas_de(app_real)
    finally:
        for n, v in previos.items():
            setattr(settings, n, v)
    return sorted(rutas)


def endpoints_sin_front() -> List[Tuple[str, str]]:
    front = paths_del_front()
    return [(m, p) for m, p in rutas_backend() if (_norm(p), m) not in front]
