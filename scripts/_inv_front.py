"""
LECTOR DEL FRONT para el inventario de smoke: árbol de archivos, grafo de imports y el mapa
`función de services/ -> (método, path)` que hace posible atribuirle endpoints a una pantalla.

🔴 POR QUÉ NO ALCANZA UN GREP DE `/api/`, que es lo primero que uno intenta. Un literal suelto no
dice ni el método ni quién lo dispara: el path por id de clientes lo escriben el GET, el PUT y el
DELETE, y los tres se leen igual. Lo que decide es el OBJETO DE OPCIONES DE ESA LLAMADA
(`method: "PUT"`), y para leerlo hay que saber dónde empieza y dónde termina cada función. De ahí
que este módulo parsee por cuerpo de función y no por línea.

⚠️ TRES TRAMPAS MEDIDAS CONTRA ESTE REPO, cada una con su conteo de daño:
  1. EL CUERPO NO EMPIEZA EN EL PRIMER `{` DESPUÉS DEL NOMBRE (66 funciones perdidas de 284).
     `fetchClientes(filtros: ClientesFiltros = {})` tiene un par de llaves en un DEFAULT DE
     PARÁMETRO, así que el brace matching ingenuo devolvía un cuerpo vacío y la función se leía
     como "no llama a ningún endpoint". Se cierra el paréntesis de la firma PRIMERO, y recién
     después se busca la llave del cuerpo — saltando el tipo de retorno, que en 5 funciones es
     un `Promise<...>` con llaves adentro de un par de ángulos.
  2. `const BASE = "/api/x"` y después `apiFetch(BASE)`. El path no aparece como literal en la
     llamada. Se resuelven los const entre sí (uno se apoya en otro) y se sustituyen antes.
  3. LOS COMENTARIOS MIENTEN, y en este repo a propósito: `services/clientes.ts` explica en prosa
     por qué NO tiene su fetch por id, y `objetivos/ListView.tsx` deja una barra de paginación
     comentada con la explicación al lado. Un barrido por texto plano los cuenta como código y la
     salida "natural" del falso positivo es borrar justo la explicación. Se enmascara antes.

Es el mismo alfabeto que `backend/tests/_barrido_callers.py` usa para emparejar front y backend
(el segmento dinámico colapsa a un par de llaves vacío), a propósito: los dos lados tienen que
normalizar igual o el cruce no cierra.
"""
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

RAIZ = Path(__file__).resolve().parent.parent
FRONT = RAIZ / "frontend"
CARPETAS = ("app", "components", "services", "hooks", "lib")

_RE_FROM = re.compile(r"""from\s+["']([^"']+)["']""")


def sin_comentarios(src: str) -> str:
    """El código con los comentarios en blanco, CONSERVANDO los saltos de línea.

    🔴 Normaliza CRLF antes de nada: media docena de barridos de este repo fueron verdes en la
    Mac y rojos en la Lenovo por un patrón de fin de línea que no matchea con el retorno de carro.
    """
    t = src.replace("\r\n", "\n")
    out: List[str] = []
    i = 0
    while i < len(t):
        if t.startswith("/*", i):
            fin = t.find("*/", i + 2)
            corte = len(t) if fin < 0 else fin + 2
            out.append(re.sub(r"[^\n]", " ", t[i:corte]))
            i = corte
        elif t.startswith("//", i):
            fin = t.find("\n", i)
            corte = len(t) if fin < 0 else fin
            out.append(" " * (corte - i))
            i = corte
        else:
            out.append(t[i])
            i += 1
    return "".join(out)


def cerrar(src: str, i: int, ab: str, ce: str) -> int:
    """Índice del delimitador que cierra el que abre en `i`."""
    d, j = 0, i
    while j < len(src):
        if src[j] == ab:
            d += 1
        elif src[j] == ce:
            d -= 1
            if d == 0:
                return j
        j += 1
    return len(src) - 1


def cuerpo_de_funcion(src: str, desde: int) -> str:
    """El cuerpo de la función cuyo nombre termina en `desde`. Ver trampa 1 del encabezado."""
    i = src.find("(", desde)
    if i < 0:
        return ""
    j, ang = cerrar(src, i, "(", ")") + 1, 0
    while j < len(src):
        c = src[j]
        if c == "<":
            ang += 1
        elif c == ">":
            ang = max(0, ang - 1)
        elif c == "{":
            if ang == 0:
                return src[j:cerrar(src, j, "{", "}") + 1]
            j = cerrar(src, j, "{", "}")
        j += 1
    return ""


def normalizar(path: str) -> str:
    """Colapsa el segmento dinámico y poda el querystring. Mismo alfabeto que el backend."""
    p = path.split("?")[0].split("#")[0]
    p = re.sub(r"\$\{[^}]*\}", "{}", p)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    p = re.sub(r"([^/])\{\}$", r"\1", p)
    return p[:-1] if len(p) > 1 and p.endswith("/") else p


@lru_cache(maxsize=1)
def archivos() -> List[str]:
    """Rutas relativas a `frontend/`, SIEMPRE con barra. Los `.test.*` quedan afuera.

    🔴 Excluirlos no es cosmético: cada pantalla tiene su archivo de patrón que importa sus
    componentes, así que con los tests adentro el grafo de imports une todo con todo.
    """
    out: List[str] = []
    for carpeta in CARPETAS:
        raiz = FRONT / carpeta
        if not raiz.exists():
            continue
        for p in raiz.rglob("*"):
            if not p.is_file() or p.suffix not in (".ts", ".tsx") or ".test." in p.name:
                continue
            partes = p.relative_to(FRONT).parts
            if any(x.startswith(".") or x == "node_modules" for x in partes):
                continue
            out.append(p.relative_to(FRONT).as_posix())
    return sorted(out)


@lru_cache(maxsize=1)
def _codigo() -> Dict[str, str]:
    return {f: sin_comentarios((FRONT / f).read_text(encoding="utf-8", errors="ignore"))
            for f in archivos()}


def codigo(f: str) -> str:
    return _codigo().get(f, "")


def destino(desde: str, spec: str) -> Optional[str]:
    """Un import del repo -> su ruta relativa, o None si apunta afuera (node_modules, types)."""
    if spec.startswith("@/"):
        base = spec[2:]
    elif spec.startswith("."):
        partes: List[str] = []
        for x in (Path(desde).parent / spec).as_posix().split("/"):
            if x == "..":
                if partes:
                    partes.pop()
            elif x not in (".", ""):
                partes.append(x)
        base = "/".join(partes)
    else:
        return None
    existe = set(archivos())
    for c in (f"{base}.tsx", f"{base}.ts", f"{base}/index.tsx", f"{base}/index.ts"):
        if c in existe:
            return c
    return None


@lru_cache(maxsize=1)
def grafo() -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """(importa, importadores): las dos direcciones, para recorrer el grafo en las dos."""
    importa: Dict[str, Set[str]] = {f: set() for f in archivos()}
    importadores: Dict[str, Set[str]] = {f: set() for f in archivos()}
    for f in archivos():
        for m in _RE_FROM.finditer(codigo(f)):
            t = destino(f, m.group(1))
            if t:
                importa[f].add(t)
                importadores[t].add(f)
    return importa, importadores


def _cierre(semilla: str, mapa: Dict[str, Set[str]]) -> Set[str]:
    vistos, cola = {semilla}, [semilla]
    while cola:
        for sig in mapa.get(cola.pop(), set()):
            if sig not in vistos:
                vistos.add(sig)
                cola.append(sig)
    return vistos


def alcanza(archivo: str) -> Set[str]:
    """Todo lo que `archivo` importa, transitivamente (hacia abajo)."""
    return _cierre(archivo, grafo()[0])


def unidad(archivo: str) -> Set[str]:
    """`archivo` mas todos sus importadores, transitivamente (hacia arriba)."""
    return _cierre(archivo, grafo()[1])
