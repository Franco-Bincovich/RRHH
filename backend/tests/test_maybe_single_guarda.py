"""
BARRIDO ESTRUCTURAL — `maybe_single().execute()` puede devolver `None` PELADO, y todo call site
tiene que chequear el OBJETO antes de tocar `.data`.

## Qué bug cierra

`POST /api/offboarding` devolvía **500 en producción para toda persona sin offboarding previo**
— o sea, para el primer offboarding de cualquiera, que es el único que existe cuando la tabla
está vacía. Medido el 23/8/2026 al sembrar datos de prueba: los 5 intentos, 500. La causa está
en `offboarding_repo.find_by_empleado`:

    res = _with_empresa(q, empresa_id).maybe_single().execute()
    if not res.data:            # ← `res` es None cuando la query no devuelve filas

`maybe_single().execute()` devuelve **`None`**, no un objeto con `.data = None`, cuando no hay
filas. El `res.data` levanta `AttributeError` y el handler global lo convierte en 500. Y el caso
que lo dispara es SIEMPRE el mismo: **"no hay filas"**, que es exactamente la rama menos probada
de cada módulo — la que corresponde a un id inexistente o a un recurso de otra empresa.

Efecto medido contra el backend desplegado, con un uuid inexistente:

    GET /api/vacantes/<uuid>        → 500   (debería ser 404)
    GET /api/proyectos/<uuid>       → 500   (debería ser 404)
    GET /api/capacitaciones/<uuid>  → 500   (debería ser 404)
    GET /api/clientes/<uuid>        → 404 ✅ (tiene la guarda)
    GET /api/empleados/<uuid>       → 404 ✅ (tiene la guarda)

O sea: además de romper endpoints, **rompe el contrato del "404 idéntico siempre"** de la barrera
de empresa — la pantalla dice "error interno" donde el diseño dice "no encontrado".

## 🔴 POR QUÉ NINGÚN TEST LO VEÍA, Y POR QUÉ ESTE BARRIDO ES ESTRUCTURAL Y NO DE COMPORTAMIENTO

El doble de Supabase devolvía `Resp(None)` —un objeto con `.data = None`— donde el cliente real
devuelve `None`. Es el caso de manual de la doctrina del repo: **el fake no modelaba la única
diferencia que importaba**, así que el modo de falla no podía aparecer. Eso ya se corrigió en
`tests/_almacen_tabla.py`, que ahora devuelve `None` pelado.

Pero arreglar el fake no alcanza, y por eso además va este barrido: el fake solo cubre los repos
que lo usan, y los 18 call sites rotos viven en 13 archivos que en su mayoría tienen su propio
doble. Un test de comportamiento por cada uno serían 18 tests que nadie va a escribir; **este
barre por AST los que existan hoy y los que se agreguen mañana**.

⚠️ El barrido acepta CUALQUIER forma de chequear el objeto (`if res and res.data`, `if not res
or not res.data`, `res.data if res else None`, …): lo que exige no es una sintaxis sino que el
nombre se pruebe antes de desreferenciarlo. Y solo mira los call sites que ASIGNAN el resultado
a una variable y después leen `.data` de ella — uno que consuma la respuesta inline no tiene
dónde poner la guarda y se cuenta aparte.
"""
import ast
import pathlib
from typing import List, Tuple

CAPAS = ("repositories", "services", "integrations", "utils")

# Guarda de mínimo: sin esto, un cambio que rompa el descubrimiento (un rename de carpeta, un
# `maybe_single` que pase a llamarse de otra forma) dejaría el barrido comparando cero contra
# cero y pasando en el vacío. Medido el 23/8/2026: 62 call sites.
MINIMO_CALL_SITES = 45


def _raiz() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


class _Visitante(ast.NodeVisitor):
    """Encuentra `X = <...>.maybe_single().execute()` y decide si `X` se protege antes de usarse.

    Trabaja sobre el AST y no sobre texto: `utils/errors.py` tiene código de ejemplo dentro de un
    docstring, y este repo ya pagó una vez el precio de un grep que confunde prosa con código
    (ver `test_espejo_codes_401.py`).
    """

    def __init__(self) -> None:
        self.protegidos: List[Tuple[int, str]] = []
        self.desprotegidos: List[Tuple[int, str]] = []
        self.inline: List[int] = []

    @staticmethod
    def _es_maybe_single(nodo: ast.AST) -> bool:
        """True si la expresión termina en `.maybe_single()....execute()`."""
        actual = nodo
        visto = False
        while isinstance(actual, ast.Call) and isinstance(actual.func, ast.Attribute):
            if actual.func.attr == "maybe_single":
                visto = True
            actual = actual.func.value
        return visto

    def visit_Assign(self, nodo: ast.Assign) -> None:
        if not self._es_maybe_single(nodo.value) or len(nodo.targets) != 1:
            self.generic_visit(nodo)
            return
        destino = nodo.targets[0]
        if not isinstance(destino, ast.Name):
            self.generic_visit(nodo)
            return
        self._pendientes.append((destino.id, nodo.lineno))
        self.generic_visit(nodo)

    def visit_Expr(self, nodo: ast.Expr) -> None:
        if self._es_maybe_single(nodo.value):
            self.inline.append(nodo.lineno)
        self.generic_visit(nodo)


def _analizar(ruta: pathlib.Path) -> Tuple[List[tuple], List[tuple]]:
    """(protegidos, desprotegidos) del archivo, como (línea, nombre de la variable).

    La detección de la guarda se hace sobre el TEXTO de las líneas siguientes y no sobre el AST
    a propósito: las formas válidas son muchas (`and`, `or`, ternario, walrus) y enumerarlas en
    AST daría un barrido que rechaza una forma correcta nueva. Lo que se busca es que el NOMBRE
    aparezca en una posición de prueba booleana antes del `.data`.
    """
    src = ruta.read_text(encoding="utf-8")
    if "maybe_single" not in src:
        return [], []
    lineas = src.split("\n")
    arbol = ast.parse(src)
    protegidos, desprotegidos = [], []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Assign) or len(nodo.targets) != 1:
            continue
        if not _Visitante._es_maybe_single(nodo.value):
            continue
        destino = nodo.targets[0]
        if not isinstance(destino, ast.Name):
            continue
        var, linea = destino.id, nodo.lineno
        ventana = "\n".join(lineas[linea:linea + 8])
        if f"{var}.data" not in ventana:
            protegidos.append((linea, var))       # no desreferencia: nada que proteger
            continue
        prueba = any(patron in ventana for patron in (
            f"not {var} or", f"not ({var} and", f"({var} and ", f"if {var} and",
            f"{var} is None", f"if not {var}:", f"{var} if {var}", f") if {var} else",
            f"if {var} else",
        ))
        (protegidos if prueba else desprotegidos).append((linea, var))
    return protegidos, desprotegidos


def _barrer():
    raiz = _raiz()
    protegidos, desprotegidos = [], []
    for capa in CAPAS:
        for archivo in sorted((raiz / capa).rglob("*.py")):
            ok, mal = _analizar(archivo)
            rel = archivo.relative_to(raiz).as_posix()
            protegidos += [(rel, n, v) for n, v in ok]
            desprotegidos += [(rel, n, v) for n, v in mal]
    return protegidos, desprotegidos


def test_hay_call_sites_que_barrer():
    """Guarda de mínimo: un barrido que no encuentra nada pasa en el vacío."""
    protegidos, desprotegidos = _barrer()
    total = len(protegidos) + len(desprotegidos)
    assert total >= MINIMO_CALL_SITES, (
        f"El barrido encontró {total} call sites de maybe_single() y esperaba al menos "
        f"{MINIMO_CALL_SITES}. Si bajaron de verdad, actualizá el mínimo; si no, el "
        "descubrimiento se rompió y este test estaba por pasar sin mirar nada.")


def test_todo_maybe_single_chequea_el_objeto_antes_de_su_data():
    """🔴 Ningún call site lee `.data` sin haber probado antes el objeto.

    Qué tendría que ser distinto para que este test falle: que alguien escriba
    `res = ...maybe_single().execute()` seguido de `res.data` sin un `if res and ...`. Eso es
    exactamente el bug que dejó `POST /api/offboarding` en 500 permanente — ver el encabezado.
    """
    _, desprotegidos = _barrer()
    detalle = "\n".join(f"  {f}:{n}  ->  la variable `{v}` se desreferencia sin chequearla"
                        for f, n, v in desprotegidos)
    assert not desprotegidos, (
        f"{len(desprotegidos)} call sites de maybe_single() leen `.data` sin chequear el "
        f"objeto. Con 0 filas `execute()` devuelve None y eso es un 500, no un 404:\n{detalle}\n"
        "La forma correcta: `return res.data if res and res.data else None`.")
