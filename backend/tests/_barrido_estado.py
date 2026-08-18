"""
Maquinaria del barrido de comparaciones sobre `empleados.estado`. NO es un archivo de tests: lo
consume `tests/test_estado_preingreso_lecturas.py`, que es donde vive el inventario declarado.

Molde: `tests/_postgrest_schema.py` y `tests/_barrido_callers.py` — helpers con nombre `_*.py`
dentro de `tests/`, para que pytest no los recoja como suite.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 POR AST Y NO POR TEXTO, Y ACÁ IMPORTA MÁS QUE EN OTROS BARRIDOS
═══════════════════════════════════════════════════════════════════════════════════════════
Media docena de docstrings del backend escriben `estado='baja'` o `estado='activo'` EN PROSA
para explicar qué hace la función (`_empleado_write_repo`, `_offboarding_efectivizar`,
`_offboarding_iniciar`, `inventario_items_service`, `empleado_roles_repo`). Un grep los marcaría
como hallazgos y el inventario se llenaría de entradas que no son código.

Peor: al ser ruido evidente, la reacción natural sería BORRAR esos comentarios para "limpiar el
barrido" — y son justamente los comentarios que registran el bug que cada uno de esos módulos
arregló. El AST no los ve, así que el problema no existe. Es la misma decisión que tomó
`test_storage_punto_unico.py`, que además fija con un test que la prosa NO cuenta.

═══════════════════════════════════════════════════════════════════════════════════════════
CÓMO SE RESUELVE A QUÉ TABLA APUNTA CADA COMPARACIÓN — y los tres buckets
═══════════════════════════════════════════════════════════════════════════════════════════
`estado` es una columna de MUCHAS tablas (`vacantes`, `onboarding_instancias`, `adjuntos`,
`inventario_items`, `objetivos`, `planes_carrera`, `mails_enviados`, `periodos_cerrados`…), así
que un barrido que las mezcle rojea por lo que no le importa y se vuelve ruido que nadie mira.

`_tabla_de` baja por la cadena de atributos del builder hasta encontrar el `.table(X)` que la
originó, y resuelve `X` contra las constantes string de nivel de módulo del propio archivo (así
`supabase_admin.table(_EMP)` con `_EMP = "empleados"` se resuelve solo).

🔑 LO QUE NO SE PUEDE RESOLVER NO SE DESCARTA: SE DEVUELVE COMO `INDETERMINADA`. Es la decisión
que sostiene todo el barrido. Cuando el `.eq()` ocurre sobre una query que llegó por parámetro
—`filtro_estado(q, estado)` en `_empleado_row`, o `procesos_service` que recibe la tabla como
argumento— la cadena no llega a ningún `.table()`. Si esos casos se filtraran por "no pude
determinar la tabla", el barrido perdería en silencio justo las comparaciones más indirectas, que
son las que más fácil se escapan de una revisión a ojo. Al quedar en un bucket propio, el test
las OBLIGA a estar declaradas una por una con su tabla real.
"""
import ast
from pathlib import Path
from typing import NamedTuple, Optional

RAIZ = Path(__file__).resolve().parent.parent
CAPAS = ("repositories", "services", "routers")

# Los cinco valores del CHECK `empleados_estado_check` (migración 120).
ESTADOS_CHECK = frozenset({"activo", "baja", "licencia", "suspendido", "preingreso"})
TABLA_EMPLEADOS = "empleados"
INDETERMINADA = "??"

_METODOS = frozenset({"eq", "neq", "in_"})

# 🔴 LOS NOMBRES DE `utils/estados_empleado`, Y SIN ESTO EL BARRIDO SE VUELVE CIEGO EN VERDE.
# Pasó de verdad el 18/8/2026: `asignaciones_service` cambió `estado == "baja"` por
# `estado not in ESTADOS_EN_PLANTILLA` y **desapareció del barrido** — el escaneo solo miraba
# `ast.Constant`, así que una comparación contra la constante compartida no existía para él.
# El conteo bajó de 3 a 2 y el único motivo por el que se notó fue la guarda de mínimo.
# Es el peor modo de falla posible acá: cuanto MÁS se usa la constante —que es lo que queremos—
# menos ve el barrido, y nadie se entera porque no hay rojo. Por eso se matchea por NOMBRE
# además de por literal, y por eso este set tiene que crecer si el módulo suma constantes.
_NOMBRES_ESTADO = frozenset({"ESTADO_PREINGRESO", "ESTADOS_EN_PLANTILLA"})


class Hallazgo(NamedTuple):
    """Una comparación sobre la columna `estado`, con la tabla que se le pudo resolver."""

    archivo: str      # ruta relativa a backend/, en formato posix
    linea: int
    metodo: str       # "eq" | "neq" | "in_" | "kwarg" | "python"
    valor: str        # el literal comparado, o el NOMBRE de la constante si es un identificador
    tabla: str        # nombre de tabla, o INDETERMINADA


def archivos(raiz: Optional[Path] = None) -> list[Path]:
    """Todos los .py de las tres capas. El separador se normaliza en `_rel`, no acá."""
    base = raiz or RAIZ
    return sorted(p for capa in CAPAS for p in (base / capa).rglob("*.py"))


def _rel(p: Path, base: Path) -> str:
    """Ruta relativa SIEMPRE en posix. En Windows `relative_to` da `\\` y comparar contra un
    literal con `/` haría que el barrido descubriera cero archivos y pasara en el vacío — el bug
    exacto que tuvo `barridoFront.test.ts`, verde en la Mac y rojo en la Lenovo."""
    return p.relative_to(base).as_posix()


def _constantes_str(arbol: ast.Module) -> dict:
    """Constantes string de nivel de módulo: `_EMP = "empleados"` → {"_EMP": "empleados"}."""
    out: dict = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant) \
                and isinstance(nodo.value.value, str):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name):
                    out[destino.id] = nodo.value.value
    return out


def _tabla_de(func: ast.expr, consts: dict) -> str:
    """Baja por la cadena del builder hasta el `.table(X)` que la originó. Ver el encabezado."""
    nodo: ast.expr = func
    while True:
        if isinstance(nodo, ast.Attribute):
            nodo = nodo.value
        elif isinstance(nodo, ast.Call):
            f = nodo.func
            if isinstance(f, ast.Attribute) and f.attr == "table" and nodo.args:
                arg = nodo.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    return arg.value
                if isinstance(arg, ast.Name):
                    return consts.get(arg.id, INDETERMINADA)
                return INDETERMINADA
            nodo = f
        else:
            return INDETERMINADA


def _valor(nodo: ast.expr) -> str:
    """El literal comparado, o el NOMBRE del identificador si es una constante importada.

    Devolver `ESTADOS_EN_PLANTILLA` en vez de su contenido es a propósito: lo que el barrido
    ancla es QUÉ CRITERIO usa cada sitio, y "usa la constante compartida" es un criterio
    distinto de "enumera tres strings a mano" aunque hoy den el mismo conjunto."""
    if isinstance(nodo, ast.Constant):
        return str(nodo.value)
    if isinstance(nodo, ast.Name):
        return nodo.id
    return "<expr>"


def hallazgos_query(raiz: Optional[Path] = None) -> list[Hallazgo]:
    """`.eq/.neq/.in_("estado", X)` sobre el builder, más los `estado=` por keyword.

    El kwarg existe por UN caso real y no por completitud: `dashboard_service` cuenta con un
    helper propio (`_count("empleados", estado="activo")`) en vez de encadenar el `.eq()`, así
    que sin esta rama el KPI de headcount —una de las 15 lecturas del grupo A— quedaría fuera
    del barrido sin que nada lo indique."""
    base = raiz or RAIZ
    salida: list[Hallazgo] = []
    for p in archivos(base):
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        consts = _constantes_str(arbol)
        rel = _rel(p, base)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            f = nodo.func
            if isinstance(f, ast.Attribute) and f.attr in _METODOS and len(nodo.args) >= 2 \
                    and isinstance(nodo.args[0], ast.Constant) and nodo.args[0].value == "estado":
                salida.append(Hallazgo(rel, nodo.lineno, f.attr, _valor(nodo.args[1]),
                                       _tabla_de(f, consts)))
                continue
            for kw in nodo.keywords:
                if kw.arg != "estado" or not isinstance(kw.value, ast.Constant):
                    continue
                if kw.value.value not in ESTADOS_CHECK:
                    continue
                tabla = nodo.args[0].value if nodo.args and isinstance(nodo.args[0], ast.Constant) \
                    else INDETERMINADA
                salida.append(Hallazgo(rel, nodo.lineno, "kwarg", str(kw.value.value), str(tabla)))
    return salida


def hallazgos_python(raiz: Optional[Path] = None) -> list[Hallazgo]:
    """Comparaciones en Python (`==` / `!=`) contra un literal del CHECK.

    Matchea DOS formas: contra un literal del CHECK (`== "baja"`) y contra una constante de
    `utils/estados_empleado` (`not in ESTADOS_EN_PLANTILLA`). Ver `_NOMBRES_ESTADO`: mirar solo
    literales dejaba invisible justamente al código que usa la constante compartida.

    Acá NO se puede resolver ninguna tabla —son valores ya traídos de la base— así que todas
    salen como INDETERMINADA y el test las declara una por una. Son pocas y no crecen solas.
    El filtro por `ESTADOS_CHECK` es lo que deja afuera el `== "completado"` de capacitaciones,
    el `== "cerrada"` de vacantes y los otros veinte estados de otras tablas."""
    base = raiz or RAIZ
    salida: list[Hallazgo] = []
    for p in archivos(base):
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        rel = _rel(p, base)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Compare):
                continue
            for lado in [nodo.left, *nodo.comparators]:
                if isinstance(lado, ast.Constant) and lado.value in ESTADOS_CHECK:
                    valor = str(lado.value)
                elif isinstance(lado, ast.Name) and lado.id in _NOMBRES_ESTADO:
                    valor = lado.id
                else:
                    continue
                salida.append(Hallazgo(rel, nodo.lineno, "python", valor, INDETERMINADA))
                break
    return salida
