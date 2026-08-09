"""
Detección por AST del patrón `if not <param>: return <vacío>` como PRIMERA sentencia.

Helper, no test. Lo usan los tres archivos que ejercitan mappers con filas
(`test_ausencia_row`, `test_objetivo_row`, `test_proyectos_enrich`, `test_ev_row_mappers`) y el
barrido `test_mappers_ejercitados`.

## Por qué AST y no leer líneas

La primera versión de esto miraba `getsource().splitlines()` y salteaba las líneas que empiezan
con comilla. Falla con cualquier docstring de más de una línea —la segunda línea no empieza con
comilla— y daba un falso rojo en `_proyectos_enrich.enriquecer`. Con `ast` el docstring es un
nodo que se descarta por lo que ES, no por cómo se ve.

## Qué reconoce, exactamente

    def f(rows, ...):
        \"\"\"...\"\"\"            ← el docstring se ignora
        if not rows:            ← primera sentencia real
            return []           ← un literal vacío: [], {}, None, ()

Nada más. Un `if not rows: return otra_cosa()` NO cuenta: el punto del patrón es que el cuerpo
entero se saltea sin efectos, que es lo que hace que llamar al mapper con `[]` no pruebe nada.
"""
import ast
import inspect
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

_REPOSITORIES = Path(__file__).resolve().parent.parent / "repositories"

# Lo que puede devolver el early-return para que cuente como "cuerpo enteramente salteado".
_VACIOS = (ast.List, ast.Dict, ast.Tuple, ast.Set)


def _guarda_del_nodo(nodo: ast.AST) -> Optional[str]:
    """Nombre del parámetro guardado, o None si la función no tiene el patrón."""
    cuerpo = list(getattr(nodo, "body", []))
    if cuerpo and isinstance(cuerpo[0], ast.Expr) and isinstance(cuerpo[0].value, ast.Constant) \
            and isinstance(cuerpo[0].value.value, str):
        cuerpo = cuerpo[1:]                                   # descarta el docstring
    if not cuerpo or not isinstance(cuerpo[0], ast.If):
        return None
    test, interno = cuerpo[0].test, cuerpo[0].body
    if not (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Name)):
        return None
    if len(interno) != 1 or not isinstance(interno[0], ast.Return):
        return None
    valor = interno[0].value
    vacio = valor is None or (isinstance(valor, _VACIOS) and not getattr(valor, "elts", [1])) \
        or (isinstance(valor, ast.Dict) and not valor.keys) \
        or (isinstance(valor, ast.Constant) and valor.value is None)
    return test.operand.id if vacio else None


def guarda_de(fn) -> Optional[str]:
    """El parámetro que corta la función recibida, o None. Para anclarlo desde un test."""
    arbol = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return _guarda_del_nodo(arbol.body[0])


@lru_cache(maxsize=1)
def descubrir() -> Dict[str, str]:
    """`modulo.funcion` → parámetro guardado, para TODO `repositories/`.

    Descubrimiento por introspección, nunca contra una lista escrita a mano: un mapper nuevo
    queda cubierto sin tocar nada.
    """
    encontrados: Dict[str, str] = {}
    for py in sorted(_REPOSITORIES.rglob("*.py")):
        try:
            arbol = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            param = _guarda_del_nodo(nodo)
            if param:
                encontrados[f"{py.stem}.{nodo.name}"] = param
    return encontrados
