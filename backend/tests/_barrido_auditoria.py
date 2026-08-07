"""
Motor del barrido de coherencia de auditoría. HELPER, no test (molde: `_barrido_callers.py`).
El test que lo consume es `test_auditoria_coherente.py`.

QUÉ RESUELVE, EN ORDEN, y por qué cada paso existe (los siete falsos positivos se midieron
contra este repo en el diagnóstico previo; el número entre paréntesis es cuántos producía):

  1. RESOLUCIÓN DE TIPOS. `self._repo.update(...)` no dice qué repo es, y `create`/`update`/
     `delete` existen en decenas. Se lee el `__init__` y se mapea atributo → clase. Sin esto el
     matcheo por nombre suelto es inservible.
  2. PROPAGACIÓN ACOTADA (23→56 AUDITA falsos). Un nombre solo propaga dentro del MISMO archivo
     o por un import explícito. Globalmente, `area_service.update_area` quedaba "auditado"
     porque otra función llamada `update` auditaba en otro módulo.
  3. PROPAGACIÓN ASCENDENTE. El evento suele estar en el ANCESTRO, no en la función que escribe:
     el import de evaluaciones emite UN evento en `confirmar` y las escrituras cuelgan de ahí.
     Mirando solo hacia abajo, todo ese flujo aparecía sin auditar.
  4. SERVICE→SERVICE. Se mapean también los atributos cuya clase termina en `Service`, no solo
     en `Repo`. Sin eso `EvaluacionService.crear_lote` salía como falso NO AUDITA.
  5. REPOS SATÉLITE Y COLABORADORES POR PARÁMETRO. Los write paths extraídos por límite de
     líneas (`_ausencias_write`, `_vacante_candidatos`, `_adjuntos_masivo`) reciben el repo y el
     audit como PARÁMETROS, sin tipo. Se detectan por nombre de parámetro (`*repo*`, `audit`).
  6. `registrar` NO ES SIEMPRE AUDITORÍA. `AuditRepo.registrar` y `MailEnviadoRepo.registrar`
     son otra cosa. Un `.registrar()` cuyo receptor resuelve a una clase `*Repo` NO cuenta.
  7. ESCRITURA TÉCNICA. Los upserts de estado técnico (oauth_states, tokens de Google) no son
     eventos de negocio; el test los declara como excepción con su motivo.

🔴 LO QUE ESTE MOTOR NO PUEDE RESOLVER — está escrito también en el test, porque condiciona
cómo hay que leer el verde: un ANCESTRO QUE AUDITA OTRA COSA da la escritura por cubierta. Es
generoso en la dirección peligrosa (sub-reporta), y es exactamente el modo de falla que dejó
pasar el import de costos, que ocurría dentro de un flujo que sí emitía otros eventos. No tiene
solución automática: haría falta comparar la ENTIDAD del evento con la tabla escrita, y el
payload no siempre la nombra.
"""
import ast
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_BACKEND = Path(__file__).resolve().parent.parent
_IGNORADOS = {"venv", ".venv", "__pycache__", "migrations", "tests"}
_OPS_ESCRITURA = {"insert", "update", "upsert", "delete", "rpc"}
# `audit_service.py` ES la auditoría: sus propias escrituras no se auditan a sí mismas.
_FUERA = {"services/audit_service.py"}


def _archivos() -> List[Path]:
    return [p for p in _BACKEND.rglob("*.py")
            if not _IGNORADOS & set(p.relative_to(_BACKEND).parts)]


def _rel(p: Path) -> str:
    return p.relative_to(_BACKEND).as_posix()


@lru_cache(maxsize=1)
def _arboles() -> Dict[str, ast.Module]:
    out = {}
    for p in _archivos():
        try:
            out[_rel(p)] = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            pass
    return out


def _escribe(nodo: ast.AST) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr in _OPS_ESCRITURA for n in ast.walk(nodo))


@lru_cache(maxsize=1)
def _escritores() -> Set[str]:
    """`Clase.metodo` de repositories/ que ejecutan un insert/update/upsert/delete/rpc."""
    out: Set[str] = set()
    for arch, arbol in _arboles().items():
        if not arch.startswith("repositories/"):
            continue
        for node in arbol.body:
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and _escribe(sub):
                        out.add(f"{node.name}.{sub.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _escribe(node):
                out.add(f"<mod>.{node.name}")      # satélites: _empleado_write_repo, etc.
    return out


@lru_cache(maxsize=1)
def _mapa_atributos() -> Dict[Tuple[str, str, str], str]:
    """(archivo, Clase, atributo) → clase colaboradora. Cubre `*Repo` Y `*Service` (falso 4)."""
    out: Dict[Tuple[str, str, str], str] = {}
    for arch, arbol in _arboles().items():
        for node in ast.walk(arbol):
            if not isinstance(node, ast.ClassDef):
                continue
            for sub in node.body:
                if not (isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == "__init__"):
                    continue
                for a in ast.walk(sub):
                    if not (isinstance(a, ast.Assign) and isinstance(a.targets[0], ast.Attribute)):
                        continue
                    clases = [n.func.id for n in ast.walk(a.value)
                              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                              and n.func.id.endswith(("Repo", "Service"))]
                    if clases:
                        out[(arch, node.name, a.targets[0].attr)] = clases[0]
    return out


class Funcion:
    def __init__(self, archivo: str, qual: str, linea: int) -> None:
        self.archivo, self.qual, self.linea = archivo, qual, linea
        self.audita_directo = False
        self.escrituras: Set[str] = set()     # `Clase.metodo` de repo que invoca
        self.llamadas: Set[str] = set()

    @property
    def clave(self) -> Tuple[str, str]:
        return (self.archivo, self.qual)


def _receptor_es_repo(fn: ast.Attribute, arch: str, clase: Optional[str]) -> bool:
    """¿El receptor de la llamada resuelve a una clase `*Repo`? (falso 6)."""
    if isinstance(fn.value, ast.Attribute) and isinstance(fn.value.value, ast.Name) \
            and fn.value.value.id == "self":
        destino = _mapa_atributos().get((arch, clase, fn.value.attr))
        return bool(destino and destino.endswith("Repo"))
    return False


def _analizar(nodo, arch: str, clase: Optional[str]) -> Funcion:
    f = Funcion(arch, f"{clase}.{nodo.name}" if clase else nodo.name, nodo.lineno)
    params = {a.arg for a in nodo.args.args}
    for n in ast.walk(nodo):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        if isinstance(fn, ast.Name):
            f.llamadas.add(fn.id)
            continue
        if not isinstance(fn, ast.Attribute):
            continue
        f.llamadas.add(fn.attr)
        if fn.attr == "registrar" and not _receptor_es_repo(fn, arch, clase):
            f.audita_directo = True
        # self._colaborador.metodo(...)
        if isinstance(fn.value, ast.Attribute) and isinstance(fn.value.value, ast.Name) \
                and fn.value.value.id == "self":
            destino = _mapa_atributos().get((arch, clase, fn.value.attr))
            if destino and f"{destino}.{fn.attr}" in _escritores():
                f.escrituras.add(f"{destino}.{fn.attr}")
        # Colaborador por PARÁMETRO, sin tipo (falso 5): `repo`, `candidato_repo`, …
        # 🔴 NO se adivina la clase. Un parámetro sin anotación puede ser cualquier repo, y elegir
        # "el primer escritor que se llame igual" atribuía `_vacaciones_write.crear` a
        # `ProyectosRepo.save`. Se reporta `<param>.metodo`: alcanza para saber QUE escribe, que
        # es lo único que decide la cobertura, y no miente sobre CUÁL es.
        elif isinstance(fn.value, ast.Name) and fn.value.id in params and "repo" in fn.value.id:
            if any(esc.split(".", 1)[1] == fn.attr for esc in _escritores()):
                f.escrituras.add(f"{fn.value.id}.{fn.attr}")
    return f


@lru_cache(maxsize=1)
def _funciones() -> Dict[Tuple[str, str], Funcion]:
    out: Dict[Tuple[str, str], Funcion] = {}
    for arch, arbol in _arboles().items():
        if arch.startswith("repositories/") or arch in _FUERA:
            continue
        for node in arbol.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                f = _analizar(node, arch, None)
                out[f.clave] = f
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        f = _analizar(sub, arch, node.name)
                        out[f.clave] = f
    return out


@lru_cache(maxsize=1)
def _llamadores() -> Dict[Tuple[str, str], Set[Tuple[str, str]]]:
    """callee → callers, resuelto SOLO por mismo archivo o import explícito (falso 2)."""
    por_arch_nombre: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for clave, f in _funciones().items():
        por_arch_nombre.setdefault((f.archivo, f.qual.split(".")[-1]), clave)
    # 🔴 Un SET de destinos por archivo, no un dict nombre→destino. Con dict, la segunda entrada
    # (el módulo-como-paquete, `from services import _x`) PISABA a la primera cuando el import no
    # lleva `as`, y se perdía el path real: por eso `EvaluacionService.crear_lote` salía sin
    # llamadores y aparecía como falso NO AUDITA.
    importado: Dict[str, Set[str]] = defaultdict(set)
    for arch, arbol in _arboles().items():
        for n in ast.walk(arbol):
            if isinstance(n, ast.ImportFrom) and n.module:
                importado[arch].add(n.module.replace(".", "/") + ".py")
                for a in n.names:
                    importado[arch].add((n.module + "." + a.name).replace(".", "/") + ".py")
    out: Dict[Tuple[str, str], Set[Tuple[str, str]]] = defaultdict(set)
    for clave, f in _funciones().items():
        for nombre in f.llamadas:
            candidatos = []
            if (f.archivo, nombre) in por_arch_nombre:
                candidatos.append(por_arch_nombre[(f.archivo, nombre)])
            for destino in importado[f.archivo]:
                if (destino, nombre) in por_arch_nombre:
                    candidatos.append(por_arch_nombre[(destino, nombre)])
            for c in candidatos:
                if c != clave:
                    out[c].add(clave)
    return out


def _cubierto(clave: Tuple[str, str], visto: Optional[Set] = None) -> bool:
    """La escritura está auditada si ELLA o algún ANCESTRO emite un evento (falso 3)."""
    visto = visto if visto is not None else set()
    if clave in visto:
        return False
    visto.add(clave)
    if _funciones()[clave].audita_directo:
        return True
    return any(_cubierto(a, visto) for a in _llamadores().get(clave, ()))


@lru_cache(maxsize=1)
def modulos_que_auditan() -> Set[str]:
    """Archivos con AL MENOS UN evento de auditoría. Son el ALCANCE del barrido."""
    return {f.archivo for f in _funciones().values() if f.audita_directo}


@lru_cache(maxsize=1)
def escrituras_del_alcance() -> List[Tuple[str, str, str, bool]]:
    """(archivo, qual, `Clase.metodo` escrito, cubierto) para los módulos que ya auditan."""
    alcance = modulos_que_auditan()
    out = []
    for clave, f in sorted(_funciones().items()):
        if f.archivo not in alcance:
            continue
        for esc in sorted(f.escrituras):
            out.append((f.archivo, f.qual, esc, _cubierto(clave)))
    return out


def sin_auditar() -> List[Tuple[str, str, str]]:
    return [(a, q, e) for a, q, e, ok in escrituras_del_alcance() if not ok]


@lru_cache(maxsize=1)
def total_escritores() -> int:
    return len(_escritores())
