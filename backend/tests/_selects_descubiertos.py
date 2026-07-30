"""
Descubrimiento de los `.table(X).select(Y)` del código, por INTROSPECCIÓN del AST.

🔴 POR QUÉ ESTO EXISTE Y NO UNA LISTA ESCRITA A MANO. `_postgrest_schema.py` se construyó para
cerrar la clase de bug "el select nombra algo que no existe", y validaba **solo los generadores
de reportes**. La clase reapareció DOS veces más en el código que quedó afuera: el listado de
plantillas de onboarding, y el embed de `planes_carrera_repo` con la FK mal nombrada que tiró
`GET /api/sucesion/planes` a 500 durante meses. Una lista de archivos habría tenido el mismo
agujero: los tres se colaron por no estar en ella. Un repo nuevo tiene que quedar cubierto SOLO.

Resuelve constantes de módulo, f-strings armados con ellas, y —lo que más importa— constantes
IMPORTADAS de otro módulo: el patrón `from repositories._empleado_row import SELECT, TABLE` es el
que usan los repos partidos por límite de líneas, y sin seguirlo se perdían justo los más grandes.

Lo que NO se puede resolver estáticamente se DEVUELVE igual, con `tabla`/`spec` en None, para que
el barrido lo cuente y lo declare excepción explícita. Nunca se descarta en silencio.
"""
import ast
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

_RAIZ = Path(__file__).resolve().parent.parent


class Select(NamedTuple):
    archivo: str
    linea: int
    tabla: Optional[str]
    spec: Optional[str]

    @property
    def resuelto(self) -> bool:
        return self.tabla is not None and self.spec is not None

    @property
    def tiene_embed(self) -> bool:
        return bool(self.spec) and "(" in self.spec

    @property
    def ubicacion(self) -> str:
        return f"{self.archivo}:{self.linea}"


def _resolver(nodo: ast.AST, consts: Dict[str, str]) -> Optional[str]:
    """Valor de un nodo si es una string estáticamente conocible. None si es dinámico."""
    if isinstance(nodo, ast.Constant):
        return nodo.value if isinstance(nodo.value, str) else None
    if isinstance(nodo, ast.Name):
        return consts.get(nodo.id)
    if isinstance(nodo, ast.JoinedStr):          # f-string
        partes = []
        for v in nodo.values:
            interno = v.value if isinstance(v, ast.FormattedValue) else v
            r = _resolver(interno, consts)
            if r is None:
                return None
            partes.append(r)
        return "".join(partes)
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        a, b = _resolver(nodo.left, consts), _resolver(nodo.right, consts)
        return None if a is None or b is None else a + b
    return None


def _constantes_locales(arbol: ast.Module, heredadas: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Constantes string de nivel de módulo. Contempla `A, B = "x", "y"` (lo usan los repos)."""
    out: Dict[str, str] = dict(heredadas or {})
    for n in arbol.body:
        if not isinstance(n, ast.Assign):
            continue
        objetivo = n.targets[0]
        if isinstance(objetivo, ast.Name):
            if (v := _resolver(n.value, out)) is not None:
                out[objetivo.id] = v
        elif isinstance(objetivo, ast.Tuple) and isinstance(n.value, ast.Tuple):
            for t, val in zip(objetivo.elts, n.value.elts):
                if isinstance(t, ast.Name) and (v := _resolver(val, out)) is not None:
                    out[t.id] = v
    return out


def _constantes(ruta: Path, cache: Dict[Path, Dict[str, str]]) -> Dict[str, str]:
    """Constantes del módulo MÁS las que importa de otros módulos del backend.

    Sin esto se pierden los repos partidos por límite de líneas, que son los más grandes:
    `empleado_repo` toma `TABLE` y `SELECT` de `_empleado_row`, y su select quedaba sin resolver.
    """
    if ruta in cache:
        return cache[ruta]
    cache[ruta] = {}                                    # corta ciclos de import
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))

    # 🔴 Los IMPORTADOS van PRIMERO, y el orden importa: `vacaciones_repo` hace
    # `from ._vacaciones_utils import TABLE` y después `_T = TABLE`. Resolviendo los locales antes
    # de traer los importados, `_T` quedaba sin valor y los cuatro selects de ese repo se perdían.
    heredadas: Dict[str, str] = {}
    for n in arbol.body:
        if not isinstance(n, ast.ImportFrom) or not n.module:
            continue
        origen = _RAIZ / (n.module.replace(".", "/") + ".py")
        if not origen.exists():
            continue
        ajenas = _constantes(origen, cache)
        for alias in n.names:
            if alias.name in ajenas:
                heredadas[alias.asname or alias.name] = ajenas[alias.name]

    out = {**heredadas, **_constantes_locales(arbol, heredadas)}
    cache[ruta] = out
    return out


def _tabla_de_la_cadena(nodo: ast.AST, consts: Dict[str, str]) -> Optional[str]:
    """Sube por la cadena `...table(X).select(...)` buscando el argumento de `.table(`."""
    actual = nodo
    while isinstance(actual, ast.Call) and isinstance(actual.func, ast.Attribute):
        if actual.func.attr == "table" and actual.args:
            return _resolver(actual.args[0], consts)
        actual = actual.func.value
    return None


def descubrir(*directorios: str) -> List[Select]:
    """Todos los `.select(...)` de los directorios dados, resueltos o no."""
    cache: Dict[Path, Dict[str, str]] = {}
    out: List[Select] = []
    for d in directorios:
        for ruta in sorted((_RAIZ / d).rglob("*.py")):
            arbol = ast.parse(ruta.read_text(encoding="utf-8"))
            consts = _constantes(ruta, cache)
            for n in ast.walk(arbol):
                if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "select"):
                    continue
                out.append(Select(
                    archivo=str(ruta.relative_to(_RAIZ)), linea=n.lineno,
                    tabla=_tabla_de_la_cadena(n.func.value, consts),
                    spec=_resolver(n.args[0], consts) if n.args else None))
    return out
