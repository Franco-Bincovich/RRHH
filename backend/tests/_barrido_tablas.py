"""
Qué TABLAS puede escribir el código. HELPER, no test (molde: `_barrido_auditoria.py`).
Lo consumen `test_semilla_alcanza_lo_que_se_escribe.py` y cualquier barrido que necesite el
inventario real de tablas escritas.

🔴 LOS NOMBRES DE TABLA CASI NUNCA SON LITERALES EN EL CALL SITE, y resolverlos es todo el
trabajo de este módulo. El repo usa una constante de módulo (`_T = "objetivos"`, `TABLE =
"empleados"`) y los write paths extraídos por límite de líneas la IMPORTAN del hermano
(`from repositories._empleado_row import TABLE`). Un barrido que sólo mirara
`.table("literal")` resolvería una minoría de los call sites y **reportaría de menos, en
silencio** — que en un barrido de cobertura es el peor resultado posible: el verde se leería
como "está todo cubierto".

Por eso la resolución es en TRES pasos, en orden:
  1. Literal en el propio call site: `.table("auditoria")`.
  2. Constante de módulo del MISMO archivo: `_T = "objetivos"` arriba.
  3. Constante IMPORTADA: se sigue el `from repositories.X import TABLE` hasta el módulo X.
Y lo que no se resuelve **se reporta**, para que el test pueda exigir que sean pocos en vez de
tragárselos.
"""
import ast
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

_BACKEND = Path(__file__).resolve().parent.parent
_IGNORADOS = {"venv", ".venv", "__pycache__", "migrations", "tests"}
_OPS = {"insert", "upsert", "update", "delete"}
_CREA_FILAS = {"insert", "upsert"}


@lru_cache(maxsize=1)
def _arboles() -> Dict[str, ast.Module]:
    out = {}
    for p in _BACKEND.rglob("*.py"):
        if _IGNORADOS & set(p.relative_to(_BACKEND).parts):
            continue
        try:
            out[p.relative_to(_BACKEND).as_posix()] = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            pass
    return out


@lru_cache(maxsize=1)
def _constantes() -> Dict[str, Dict[str, str]]:
    """archivo → {NOMBRE: valor} de las constantes de módulo que son strings."""
    out: Dict[str, Dict[str, str]] = {}
    for arch, arbol in _arboles().items():
        locales: Dict[str, str] = {}
        for n in arbol.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, str) and isinstance(n.targets[0], ast.Name):
                locales[n.targets[0].id] = n.value.value
        out[arch] = locales
    return out


@lru_cache(maxsize=1)
def _importadas() -> Dict[str, Dict[str, str]]:
    """archivo → {NOMBRE: valor}, siguiendo `from modulo import NOMBRE` (paso 3)."""
    consts = _constantes()
    out: Dict[str, Dict[str, str]] = {}
    for arch, arbol in _arboles().items():
        traidas: Dict[str, str] = {}
        for n in ast.walk(arbol):
            if not (isinstance(n, ast.ImportFrom) and n.module):
                continue
            destino = n.module.replace(".", "/") + ".py"
            for alias in n.names:
                valor = consts.get(destino, {}).get(alias.name)
                if valor is not None:
                    traidas[alias.asname or alias.name] = valor
        out[arch] = traidas
    return out


def _resolver(nodo: ast.AST, arch: str) -> Tuple[str, bool]:
    """Baja por la cadena `...table(X)...` → (nombre, resuelto). Ver los tres pasos del encabezado."""
    cur = nodo
    while isinstance(cur, (ast.Call, ast.Attribute)):
        if isinstance(cur, ast.Call) and isinstance(cur.func, ast.Attribute) \
                and cur.func.attr == "table" and cur.args:
            a = cur.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                return a.value, True
            if isinstance(a, ast.Name):
                v = _constantes()[arch].get(a.id) or _importadas()[arch].get(a.id)
                return (v, True) if v else (a.id, False)
            return ("<expr>", False)
        cur = cur.func.value if isinstance(cur, ast.Call) else cur.value
    return ("", False)


@lru_cache(maxsize=1)
def _escrituras() -> Tuple[Dict[str, Set[str]], List[str]]:
    """({tabla: {ops}}, [call sites sin resolver])."""
    tablas: Dict[str, Set[str]] = {}
    sin_resolver: List[str] = []
    for arch, arbol in _arboles().items():
        for n in ast.walk(arbol):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in _OPS):
                continue
            nombre, ok = _resolver(n.func.value, arch)
            if not nombre:
                continue                       # no es una cadena de PostgREST
            if ok:
                tablas.setdefault(nombre, set()).add(n.func.attr)
            else:
                sin_resolver.append(f"{arch}::{nombre}")
    return tablas, sin_resolver


def tablas_escritas() -> Dict[str, Set[str]]:
    """Toda tabla que el código toca, con sus operaciones."""
    return _escrituras()[0]


def tablas_que_crean_filas() -> Set[str]:
    """Las que el código INSERTA o UPSERTEA: las únicas que pueden dejar basura tras un smoke.

    🔑 `update` y `delete` NO cuentan: modifican filas que ya existían. Lo que el limpiador de la
    semilla tiene que poder alcanzar es lo que la corrida CREÓ.
    """
    return {t for t, ops in tablas_escritas().items() if ops & _CREA_FILAS}


def sin_resolver() -> List[str]:
    """Call sites cuyo nombre de tabla no se pudo resolver. El test exige que sean pocos."""
    return _escrituras()[1]


@lru_cache(maxsize=1)
def orden_del_limpiador() -> List[str]:
    """Las tablas de `ORDEN`, en `scripts/_semilla_plan_borrado.py`, **leídas por AST**.

    🔴 NO SE IMPORTA EL MÓDULO, y no es una preferencia de estilo: `_semilla_plan_borrado`
    importa `_semilla_plan_barrera`, que importa `integrations.supabase_client`, que instancia
    `Settings()` al importarse. O sea que un `import` acá exigiría env vars y levantaría un
    cliente real de Supabase **dentro de la suite de tests**, que es exactamente lo que
    `_cliente_real_en_tests.py` existe para impedir.
    """
    ruta = _BACKEND.parent / "scripts" / "_semilla_plan_borrado.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for n in ast.walk(arbol):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "ORDEN":
            return [elt.elts[0].value for elt in n.value.elts]
    return []


@lru_cache(maxsize=1)
def buckets_del_storage() -> Set[str]:
    """Los buckets declarados en `integrations/storage.py` — el punto de contacto único.

    Se leen de ahí y no de una lista a mano por el mismo motivo que todo lo demás de este
    archivo: un bucket nuevo tiene que entrar al barrido solo.
    """
    consts = _constantes().get("integrations/storage.py", {})
    return {v for k, v in consts.items() if k.isupper()}
