"""
Maquinaria del barrido de ESCRITURAS sobre `empleados.estado`. Hermano de `_barrido_estado.py`,
que cubre las COMPARACIONES. NO es un archivo de tests: lo consume
`tests/test_estado_preingreso_escrituras.py`.

Vive en un archivo aparte y no adentro de su hermano por una razón boba y verificable:
`_barrido_estado.py` está en 194/200 y esto son ~90 líneas. El resolvedor de tabla, el listado
de archivos y la normalización de rutas se IMPORTAN de allá — son la misma pregunta ("¿esta
query es de `empleados`?") y dos copias se separarían.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 POR QUÉ HACEN FALTA DOS BARRIDOS Y NO ALCANZA CON EXTENDER EL DE COMPARACIONES
═══════════════════════════════════════════════════════════════════════════════════════════
Una comparación y una escritura **no se parecen en el AST**. El de lecturas busca
`.eq/.neq/.in_("estado", X)` y `==`/`!=` contra un valor conocido: todas formas donde el nombre
de la columna aparece como string al lado del valor. Una escritura de `estado` toma CUATRO
formas distintas y en tres de ellas **el string `"estado"` no aparece en ningún lado**:

  · `dict`      — `.update({"estado": "baja", ...})`. La única que se parece a una lectura.
  · `campo`     — `estado: EstadoAlta = "activo"` en un schema Pydantic. **Esto ES una escritura**
                  aunque no toque la base: el default entra al `model_dump()` y de ahí al INSERT.
                  Es el camino del ALTA, y es invisible para cualquier grep de `"estado"`.
  · `kwarg`     — `EmpleadoUpdate(estado="activo")`. El camino del pase a activo.
  · `dar_de_baja` — una LLAMADA. La escritura física está en otro archivo; lo que importa acá es
                  **quién la dispara**, porque cada caller es un camino con sus propias guardas
                  (o sin ninguna: ver el de nómina).

Un solo barrido que mezclara las cuatro formas con las dos de lecturas tendría un `if` por
forma y una lista de excepciones que nadie lee. Separados, cada uno responde una pregunta.

═══════════════════════════════════════════════════════════════════════════════════════════
EL FILTRO POR TABLA ES EL MISMO QUE EL DE LECTURAS, Y POR EL MISMO MOTIVO
═══════════════════════════════════════════════════════════════════════════════════════════
`estado` es columna de una docena de tablas y casi todas tienen su `.update({"estado": ...})`
(adjuntos, vacantes, objetivos, inventario, onboarding, planes de carrera…). La forma `dict` se
resuelve con `_tabla_de` de `_barrido_estado`: lo que da otra tabla se descarta, y lo que no se
puede resolver queda declarado a mano. Las otras tres formas no necesitan filtro: nombran un
modelo de empleado o una función de empleado, así que son de `empleados` por construcción.

⚠️ `schemas/empleado_out.py` se EXCLUYE de la forma `campo` a propósito: `EmpleadoResponse` es
el schema de SALIDA. Su `estado: str` describe lo que se lee, no lo que se escribe, y contarlo
metería una fila que nadie puede "arreglar" en un inventario de caminos de escritura.
"""
import ast
from pathlib import Path
from typing import NamedTuple, Optional

from tests._barrido_estado import RAIZ, _constantes_str, _rel, _tabla_de, archivos

TABLA_EMPLEADOS = "empleados"
INDETERMINADA = "??"

# Los modelos de ENTRADA de empleado. `EmpleadoResponse` no está: es salida (ver el encabezado).
_MODELOS_ESCRITURA = frozenset({
    "EmpleadoCreate", "EmpleadoUpdate", "EmpleadoCreateNomina", "EmpleadoUpdateNomina",
})
_SCHEMAS_DE_SALIDA = ("schemas/empleado_out.py",)
_FUNCION_BAJA = "dar_de_baja"


class Escritura(NamedTuple):
    """Un sitio que puede cambiar `empleados.estado`."""

    archivo: str
    linea: int
    forma: str    # "dict" | "campo" | "kwarg" | "dar_de_baja"
    detalle: str  # qué se escribe, o qué modelo/función interviene


def _campos(arbol: ast.Module, rel: str) -> list:
    """Forma `campo`: `estado: X = Y` declarado en un modelo de ENTRADA de empleado."""
    if rel in _SCHEMAS_DE_SALIDA:
        return []
    out = []
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.ClassDef) and nodo.name in _MODELOS_ESCRITURA):
            continue
        for item in nodo.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) \
                    and item.target.id == "estado":
                default = ast.unparse(item.value) if item.value else "<sin default>"
                out.append(Escritura(rel, item.lineno, "campo",
                                     f"{nodo.name}.estado = {default}"))
    return out


def _llamadas(arbol: ast.Module, rel: str, consts: dict) -> list:
    """Las otras tres formas: dict de insert/update, kwarg de modelo, y llamada a dar_de_baja."""
    out = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        if isinstance(f, ast.Attribute) and f.attr in ("insert", "update") and nodo.args \
                and isinstance(nodo.args[0], ast.Dict):
            claves = [k.value for k in nodo.args[0].keys
                      if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if "estado" in claves and _tabla_de(f, consts) in (TABLA_EMPLEADOS, INDETERMINADA):
                out.append(Escritura(rel, nodo.lineno, "dict", ast.unparse(nodo.args[0])[:70]))
        if isinstance(f, ast.Name) and f.id in _MODELOS_ESCRITURA:
            for kw in nodo.keywords:
                if kw.arg == "estado":
                    out.append(Escritura(rel, nodo.lineno, "kwarg",
                                         f"{f.id}(estado={ast.unparse(kw.value)})"))
        nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        if nombre == _FUNCION_BAJA:
            out.append(Escritura(rel, nodo.lineno, _FUNCION_BAJA, ast.unparse(f)))
    return out


def escrituras(raiz: Optional[Path] = None) -> list[Escritura]:
    """Todos los sitios que pueden escribir `empleados.estado`, en las cuatro formas."""
    base = raiz or RAIZ
    salida: list[Escritura] = []
    for p in archivos(base) + sorted((base / "schemas").rglob("*.py")):
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        rel = _rel(p, base)
        salida.extend(_campos(arbol, rel))
        salida.extend(_llamadas(arbol, rel, _constantes_str(arbol)))
    return salida
