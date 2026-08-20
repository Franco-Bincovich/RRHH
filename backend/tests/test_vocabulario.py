"""
🔴 BARRIDO ESTRUCTURAL — la mitad de backend del vocabulario del sistema de diseño §4.

Se dice **Colaboradores**, no empleados, y **Capital Humano**, no Recursos Humanos. El renombre
va en pantalla, en los encabezados y nombres de archivo de export, y en los mensajes de error
visibles al usuario. **NO va en tablas, columnas, endpoints, el valor `entidad` de la auditoría,
ni en identificadores de código.**

## 🔑 Cómo distingue texto visible de identificador — que es lo único que lo hace usable

En Python la frontera es más borrosa que en el front: un docstring, la `description` de un
`Query` de OpenAPI y un `select()` de PostgREST son todos strings, y ninguno es texto de
pantalla. Un barrido que los mirara marcaría `empleados!inner(...)` —una relación de la base— y
alguien lo apagaría en dos semanas, con razón.

Por eso NO mira strings sueltos. Mira **por AST** exactamente dos superficies, las dos con
destino conocido en la pantalla del usuario:

  1. **El primer argumento de `AppError(...)`** — el `message`, que es lo que el front muestra
     en el toast. El `code` (segundo argumento) es un identificador y no se toca.
  2. **Las claves de diccionario de `services/_*_export.py`** — son los encabezados de columna
     del archivo que se descarga. El VALOR de cada clave (`a.empleado_nombre`) es un campo del
     modelo y se deja como está.

Lo que queda deliberadamente afuera y no es un olvido: docstrings, `description=` de OpenAPI
(documentación de la API, no pantalla), prompts de IA, y todo `select()`/nombre de columna.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
  · El descubrimiento es por recorrido del árbol y parseo del AST: ningún archivo en una lista.
  · Guardas de mínimo ANTES de comparar: si el parseo se rompiera, el barrido encontraría 0
    mensajes y "no hay violaciones" pasaría en el vacío.
  · Las excepciones se verifican en las dos direcciones: declarada y todavía presente.
"""

import ast
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
PROHIBIDO = re.compile(r"\bEmplead[oa]s?\b|\bRecursos Humanos\b|\bRRHH\b", re.I)

# (archivo, fragmento, razón). Cada una dice por qué ESE texto es el correcto, no "por ahora".
EXCEPCIONES: tuple[tuple[str, str, str], ...] = ()


def _modulos() -> list[Path]:
    return [p for c in ("services", "routers") for p in (BACKEND / c).rglob("*.py")]


def _texto_de(nodo: ast.AST) -> str | None:
    """El literal de un nodo, incluidas las f-strings (se mira su parte constante)."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr):
        return "".join(v.value for v in nodo.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        izq, der = _texto_de(nodo.left), _texto_de(nodo.right)
        if izq is not None and der is not None:
            return izq + der
    return None


def _mensajes_de_apperror() -> list[tuple[str, int, str]]:
    """El `message` de cada AppError del código. Es lo que el usuario lee en el toast."""
    salida = []
    for p in _modulos():
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(arbol):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "AppError"):
                continue
            texto = _texto_de(n.args[0]) if n.args else next(
                (_texto_de(k.value) for k in n.keywords if k.arg == "message"), None)
            if texto:
                salida.append((str(p.relative_to(BACKEND)), n.lineno, texto))
    return salida


def _encabezados_de_export() -> list[tuple[str, int, str]]:
    """Las CLAVES de los dicts de `_*_export.py`: los encabezados de columna del archivo."""
    salida = []
    for p in (BACKEND / "services").glob("_*_export.py"):
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(arbol):
            if not isinstance(n, ast.Dict):
                continue
            for k in n.keys:
                texto = _texto_de(k) if k is not None else None
                if texto:
                    salida.append((str(p.relative_to(BACKEND)), n.lineno, texto))
    return salida


MENSAJES = _mensajes_de_apperror()
ENCABEZADOS = _encabezados_de_export()


def _viola(items):
    return [f"{a}:{ln}  {t!r}" for a, ln, t in items
            if PROHIBIDO.search(t) and not any(a == ea and ef in t for ea, ef, _ in EXCEPCIONES)]


class TestGuardas:
    def test_el_barrido_no_esta_vacio(self):
        # Sin esto, un parseo roto daría 0 hallazgos y "no hay violaciones" pasaría sin mirar.
        assert len(MENSAJES) >= 150, f"solo {len(MENSAJES)} AppError encontrados"
        assert len(ENCABEZADOS) >= 100, f"solo {len(ENCABEZADOS)} encabezados de export"

    def test_el_detector_detecta(self):
        # Ancla la expresión con literales antes de creerle a la medición de arriba.
        assert PROHIBIDO.search("El empleado ya está dado de baja")
        assert PROHIBIDO.search("hablá con Recursos Humanos")
        assert PROHIBIDO.search("Administrador RRHH")
        assert not PROHIBIDO.search("El colaborador ya está dado de baja")
        assert not PROHIBIDO.search("Capital Humano")


class TestVocabulario:
    def test_ningun_mensaje_de_error_dice_empleado(self):
        assert _viola(MENSAJES) == []

    def test_ningun_encabezado_de_export_dice_empleado(self):
        assert _viola(ENCABEZADOS) == []

    @pytest.mark.parametrize("archivo,fragmento,razon", EXCEPCIONES)
    def test_toda_excepcion_sigue_viva(self, archivo, fragmento, razon):
        # Una excepción muerta es ruido que oculta el próximo caso real.
        assert fragmento in (BACKEND / archivo).read_text(encoding="utf-8")
        assert len(razon) > 40, "una excepción sin razón escrita no es una excepción"
