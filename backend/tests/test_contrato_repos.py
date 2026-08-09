"""
BARRIDO ESTRUCTURAL — un service no puede llamar un método que su colaborador no tiene.

## Qué clase de bug cierra

`gmail_service.crear_candidato_desde_email` llamaba a `self._vacante_repo.save_candidato(...)`.
Ese método **nunca existió en `VacanteRepo`**: vive en `CandidatoRepo`. La llamada estaba fuera
del try/except, así que el endpoint moría con `AttributeError` → handler global → **500**, y el
botón "Agregar como candidato" estuvo roto en producción desde que los dos repos se separaron.

**Es un bug de DIVISIÓN DE ARCHIVOS, y por eso pide un barrido y no un test.** Cuando un repo se
parte en dos, los callers siguen apuntando al objeto viejo: el import sigue resolviendo, el
atributo sigue existiendo, y Python no dice nada hasta que esa línea se ejecuta. Arreglar la
instancia no impide la próxima; este archivo sí, porque descubre los pares por introspección y
cubre automáticamente cualquier service o repo que se agregue después.

## Cómo resuelve a quién se le está llamando

Igual que `_barrido_auditoria`: se lee el `__init__` de cada clase y se mapea
`self.<atributo>` → clase colaboradora (`self._repo = repo or VacanteRepo()` → `VacanteRepo`).
Después, cada `self.<atributo>.<metodo>(...)` del archivo se contrasta contra los métodos que esa
clase declara.

## 🔴 Lo que NO se puede resolver, y por qué se saltea en vez de forzarse

El barrido **solo mira receptores `self.<attr>` cuyo `__init__` los ata a una clase concreta**.
Queda afuera, a propósito:

  · **Los colaboradores que llegan por parámetro** (`def crear(repo, audit, ...)`, el molde de
    todos los satélites `_*_write.py`). Ahí el tipo real lo elige el caller y en los tests es un
    doble; afirmar contra una clase concreta sería inventar un contrato que el código no declara.
  · **Los atributos que el `__init__` no ata a un constructor** (los que salen de un helper, de
    un `settings`, o de otro atributo).

Ese recorte es lo que hace que el barrido no tenga falsos positivos. La contrapartida honesta:
**no es una red completa, es una red sobre el patrón que produjo el bug** — service con repos
instanciados en su `__init__`, que es como están escritos los 4 services del módulo de vacantes
y la enorme mayoría del backend.

## Guarda contra el falso verde

`_MINIMO_LLAMADAS` y `_MINIMO_ARCHIVOS`: si la derivación se rompe (un cambio de layout, un
`__init__` que deje de parsearse), el barrido devolvería 0 pares y **todos los tests pasarían sin
haber comparado nada** — que es el modo de falla que este repo ya pagó cinco veces.
"""
import ast
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_BACKEND = Path(__file__).resolve().parent.parent
_IGNORADOS = {"venv", ".venv", "__pycache__", "migrations", "tests"}

# Solo se resuelven receptores atados a una clase de estas familias. Es el mismo criterio que
# `_barrido_auditoria._mapa_atributos`: son las que se instancian sin argumentos en un __init__.
_SUFIJOS = ("Repo", "Service")

# Mínimos del barrido. Ver "Guarda contra el falso verde" en el encabezado.
_MINIMO_LLAMADAS = 150
_MINIMO_ARCHIVOS = 25


def _archivos() -> List[Path]:
    return [p for p in _BACKEND.rglob("*.py")
            if not _IGNORADOS & set(p.relative_to(_BACKEND).parts)]


def _rel(p: Path) -> str:
    return p.relative_to(_BACKEND).as_posix()


@lru_cache(maxsize=1)
def _arboles() -> Dict[str, ast.Module]:
    out: Dict[str, ast.Module] = {}
    for p in _archivos():
        try:
            out[_rel(p)] = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            pass
    return out


@lru_cache(maxsize=1)
def _metodos_por_clase() -> Dict[str, Set[str]]:
    """`NombreDeClase` → métodos que declara. None (ausente) si el nombre está duplicado.

    Un nombre de clase repetido en dos archivos no se puede resolver desde el nombre solo, así
    que se DESCARTA en vez de unir los dos conjuntos: unirlos haría pasar una llamada que apunta
    a la clase equivocada, que es justo el bug que se persigue.
    """
    vistos: Dict[str, Set[str]] = {}
    duplicados: Set[str] = set()
    for arbol in _arboles().values():
        for node in ast.walk(arbol):
            if not isinstance(node, ast.ClassDef) or not node.name.endswith(_SUFIJOS):
                continue
            if node.name in vistos:
                duplicados.add(node.name)
                continue
            vistos[node.name] = {
                sub.name for sub in node.body
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    return {k: v for k, v in vistos.items() if k not in duplicados}


@lru_cache(maxsize=1)
def _mapa_atributos() -> Dict[Tuple[str, str, str], str]:
    """(archivo, Clase, atributo) → clase colaboradora, leído del `__init__`.

    Molde: `_barrido_auditoria._mapa_atributos`. Toma el PRIMER constructor que aparece en el
    valor asignado, que es lo que resuelve el idioma `repo or VacanteRepo()` de todo el repo.
    """
    out: Dict[Tuple[str, str, str], str] = {}
    for arch, arbol in _arboles().items():
        for node in ast.walk(arbol):
            if not isinstance(node, ast.ClassDef):
                continue
            for sub in node.body:
                if not (isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and sub.name == "__init__"):
                    continue
                for a in ast.walk(sub):
                    if not (isinstance(a, ast.Assign) and isinstance(a.targets[0], ast.Attribute)):
                        continue
                    clases = [n.func.id for n in ast.walk(a.value)
                              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                              and n.func.id.endswith(_SUFIJOS)]
                    if clases:
                        out[(arch, node.name, a.targets[0].attr)] = clases[0]
    return out


class Llamada:
    """Un `self.<attr>.<metodo>(...)` resuelto a una clase concreta."""

    def __init__(self, arch: str, clase: str, attr: str, colaborador: str,
                 metodo: str, linea: int) -> None:
        self.arch, self.clase, self.attr = arch, clase, attr
        self.colaborador, self.metodo, self.linea = colaborador, metodo, linea

    def __str__(self) -> str:
        return (f"{self.arch}:{self.linea} — {self.clase} llama "
                f"self.{self.attr}.{self.metodo}(), pero {self.colaborador} no lo tiene")


@lru_cache(maxsize=1)
def _llamadas() -> List[Llamada]:
    """Todas las llamadas `self.<attr>.<metodo>()` cuyo receptor se pudo atar a una clase."""
    mapa, out = _mapa_atributos(), []
    for arch, arbol in _arboles().items():
        for node in ast.walk(arbol):
            if not isinstance(node, ast.ClassDef):
                continue
            for n in ast.walk(node):
                if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                    continue
                recep = n.func.value
                # self.<attr>.<metodo>() — nada más. Ver el recorte del encabezado.
                if not (isinstance(recep, ast.Attribute) and isinstance(recep.value, ast.Name)
                        and recep.value.id == "self"):
                    continue
                colaborador: Optional[str] = mapa.get((arch, node.name, recep.attr))
                if colaborador is None:
                    continue
                out.append(Llamada(arch, node.name, recep.attr, colaborador,
                                   n.func.attr, n.lineno))
    return out


# ── El barrido ────────────────────────────────────────────────────────────────

def test_la_derivacion_encuentra_algo():
    """GUARDA CONTRA EL FALSO VERDE: sin esto, una derivación rota pasaría en el vacío.

    ¿Qué tendría que ser distinto para que falle? Que `_mapa_atributos` o `_llamadas` dejaran de
    resolver receptores — exactamente el caso en que el resto de los tests dejan de mirar nada.
    """
    llamadas = _llamadas()
    archivos = {ll.arch for ll in llamadas}
    assert len(llamadas) >= _MINIMO_LLAMADAS, (
        f"El barrido resolvió {len(llamadas)} llamadas (mínimo {_MINIMO_LLAMADAS}). "
        "La derivación se rompió: sin esto los demás tests pasan sin comparar nada."
    )
    assert len(archivos) >= _MINIMO_ARCHIVOS, (
        f"Solo {len(archivos)} archivos aportaron llamadas (mínimo {_MINIMO_ARCHIVOS})."
    )
    assert len(_metodos_por_clase()) >= 40, "No se indexaron las clases colaboradoras."


def test_todo_metodo_llamado_existe_en_su_colaborador():
    """🔴 EL BARRIDO. Un service no puede pedirle a un repo un método que ese repo no tiene.

    Es la generalización del bug de `gmail_service` → `VacanteRepo.save_candidato`: el import
    resuelve, el atributo existe, y Python solo se entera al ejecutar esa línea.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla sola en cuanto alguien
    llame un método inexistente. Con el bug reinstalado, rojea acá.
    """
    conocidas = _metodos_por_clase()
    rotas = [
        ll for ll in _llamadas()
        # Si la clase no se pudo indexar (nombre duplicado), no se afirma nada sobre ella.
        if ll.colaborador in conocidas and ll.metodo not in conocidas[ll.colaborador]
    ]
    assert not rotas, (
        "Hay llamadas a métodos que el colaborador NO declara (AttributeError en runtime):\n  "
        + "\n  ".join(str(r) for r in rotas)
    )


def test_save_candidato_es_de_candidato_repo_y_no_de_vacante_repo():
    """El dueño de `save_candidato`, anclado por nombre. Es la instancia del bug original.

    ⚠️ El barrido de arriba ya cubre las llamadas `self._attr.metodo()`, pero **este caso salió
    de su alcance el 9/8/2026**: el alta desde mail se mudó a `_cv_ingesta_mail`, que recibe el
    repo POR PARÁMETRO (molde de los satélites). El barrido no resuelve esos receptores a
    propósito —ver su encabezado—, así que sin este test la propiedad quedaría sin red.

    Lo que sigue siendo verificable, y es lo que importaba: que `VacanteRepo` NO declare un
    `save_candidato`. El bug era pedírselo a él; mientras no exista, pedírselo es un
    `AttributeError` inmediato y no un alta silenciosa contra el repo equivocado.

    ¿Qué tendría que ser distinto para que falle? Que alguien le agregue `save_candidato` a
    `VacanteRepo` "para que funcione", que es exactamente el arreglo equivocado.
    """
    metodos = _metodos_por_clase()
    assert "save_candidato" in metodos.get("CandidatoRepo", set()), (
        "CandidatoRepo dejó de declarar save_candidato: el alta no tiene dueño"
    )
    assert "save_candidato" not in metodos.get("VacanteRepo", set()), (
        "VacanteRepo declara save_candidato: pedírselo dejaría de ser un error visible"
    )
