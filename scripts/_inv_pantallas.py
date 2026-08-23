"""
LAS PANTALLAS: una fila por `page.tsx` del App Router, con los endpoints que alcanza, quién la
puede ver, si filtra, si pagina y si está apagada.

🔴 "QUÉ ENDPOINTS DISPARA AL MONTAR" NO SE PUEDE DERIVAR EXACTO DEL CÓDIGO ESTÁTICO, y este
módulo no finge que sí. Lo que se deriva es **qué endpoints ALCANZA la pantalla**: el cierre
transitivo de lo que importa, hasta las funciones de `services/` y de ahí a sus paths. Es un
SUPERCONJUNTO de lo que se dispara al montar — adentro caen también el export (que sale por un
botón) y los fetch de un modal que quizás no se abra. Se separa lo que se puede separar (los
export van a su propia columna) y el resto se declara como alcanzable, no como automático.
Sobrecontar es la dirección correcta para un inventario cuyo objetivo es que NADA QUEDE SIN
LISTAR: un endpoint de más se prueba y se tacha, uno de menos no se descubre nunca.

🔴 LOS ROLES SALEN DEL BACKEND, NO DEL ESPEJO DE TYPESCRIPT. La sección la decide `RUTA_SECCION`
de `frontend/services/permisos.ts` (es el mapa que usa el AuthGuard, así que es el que manda para
"quién entra a esta URL"), pero quién puede leerla se responde con `utils.permisos.puede`, que es
la fuente canónica. Reimplementar `puede()` acá agregaría un TERCER espejo de un modelo que ya
tiene dos y que este repo declara como deuda sin test.
"""
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from _inv_backend import _preparar
from _inv_front import FRONT, alcanza, archivos, codigo
from _inv_llamadas import funciones_importadas, llamadas_por_funcion

# Guarda contra el falso verde: si el recorrido del árbol se rompe, esto muerde antes de que el
# inventario salga con tres pantallas y en verde. Medido: 46 el 23/8/2026.
MINIMO_PANTALLAS = 40

_RE_RUTA_SECCION = re.compile(r"^\s*\"?([\w-]+)\"?\s*:\s*\"(\w+)\"\s*,", re.M)


class Pantalla(NamedTuple):
    ruta: str
    archivo: str
    seccion: Optional[str]
    roles: Tuple[str, ...]
    lecturas: Tuple[Tuple[str, str], ...]
    exports: Tuple[Tuple[str, str], ...]
    escrituras: Tuple[Tuple[str, str], ...]
    filtra: bool
    pagina: bool
    apagada: Optional[str]     # motivo, o None si está viva


def ruta_de(archivo: str) -> str:
    """`app/(dashboard)/empleados/[id]/page.tsx` -> `/empleados/{}`.

    Los grupos de ruta —los segmentos entre paréntesis— NO son URL: `(dashboard)` es una carpeta
    de layout compartido y no aparece en la barra de direcciones. Confundirlos daría rutas que
    no existen y ninguna coincidiría con `RUTA_SECCION`, que indexa por el primer segmento REAL.
    """
    partes = archivo[len("app/"):-len("/page.tsx")].split("/") if archivo != "app/page.tsx" else []
    limpio = [("{}" if p.startswith("[") else p) for p in partes
              if not (p.startswith("(") and p.endswith(")"))]
    return "/" + "/".join(limpio) if limpio else "/"


@lru_cache(maxsize=1)
def ruta_seccion() -> Dict[str, str]:
    """`RUTA_SECCION` de `frontend/services/permisos.ts`: primer segmento -> sección.

    Se lee del archivo real en vez de copiarse: es el mapa que consulta el AuthGuard, y una copia
    acá se separaría de él en la primera ruta nueva — justo el modo de falla que este inventario
    existe para no repetir.
    """
    src = codigo("services/permisos.ts")
    bloque = src[src.index("const RUTA_SECCION"):]
    bloque = bloque[:bloque.index("\n}")]
    return {m.group(1): m.group(2) for m in _RE_RUTA_SECCION.finditer(bloque)}


@lru_cache(maxsize=1)
def _roles_por_seccion() -> Dict[Optional[str], Tuple[str, ...]]:
    _preparar()
    from utils.permisos import ROLES_VALIDOS, puede
    out: Dict[Optional[str], Tuple[str, ...]] = {
        None: tuple(sorted(ROLES_VALIDOS))}                # sin gate de ruta: entra cualquiera
    for seccion in set(ruta_seccion().values()):
        out[seccion] = tuple(sorted(r for r in ROLES_VALIDOS if puede(r, seccion, "read")))
    return out


def _endpoints_alcanzables(archivo: str) -> Set[Tuple[str, str]]:
    """Todos los (MÉTODO, path) que la pantalla alcanza por su grafo de imports."""
    importadas = funciones_importadas()
    llamadas = llamadas_por_funcion()
    out: Set[Tuple[str, str]] = set()
    for f in alcanza(archivo):
        for clave in importadas.get(f, set()):
            out |= set(llamadas.get(clave, ()))
    return out


def _apagada(archivo: str, endpoints: Set[Tuple[str, str]]) -> Optional[str]:
    """Por qué la pantalla está apagada, o None.

    Dos mecanismos distintos y el inventario los distingue porque se prueban distinto:
      · el flag del FRONT (`useState(false)` con el setter descartado) esconde una pantalla cuyo
        backend sigue montado y respondiendo — se prueba por HTTP, no por navegador;
      · el flag del BACKEND deja el router sin montar, así que ni la pantalla ni sus endpoints
        existen hasta encenderlo.
    """
    if re.search(r"const \[\w+\] = useState\(false\)", codigo(archivo)):
        return "flag del front (la página redirige a /dashboard)"
    from _inv_backend import endpoints as todos
    con_flag = {(e.metodo, e.path) for e in todos() if e.solo_con_flag}
    equiv = {(m, _norm_backend(p)) for m, p in con_flag}
    if endpoints and endpoints <= equiv:
        return "flag del backend (el router no se monta)"
    return None


def _es_export(path: str) -> bool:
    """¿Es una descarga de archivo? 🔴 `/export`, no `/exportar`: de los 28 exports del backend
    hay UNO escrito distinto —`/lotes/{id}/evaluados/export`, en evaluaciones— y filtrando por
    `/exportar` la pantalla de evaluaciones salía con CERO exports teniendo uno. El plural
    tolerante cuesta nada y no produce falsos: ninguna ruta del repo dice "export" sin serlo."""
    return "/export" in path


def _norm_backend(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


@lru_cache(maxsize=1)
def pantallas() -> List[Pantalla]:
    """Una fila por `page.tsx`. Aborta si el recorrido del árbol devolvió casi nada."""
    paginas = [f for f in archivos() if f.startswith("app/") and f.endswith("/page.tsx")]
    paginas += ["app/page.tsx"] if (FRONT / "app/page.tsx").exists() and \
        "app/page.tsx" not in paginas else []
    out: List[Pantalla] = []
    for f in sorted(set(paginas)):
        ruta = ruta_de(f)
        seccion = ruta_seccion().get(ruta.split("/")[1] if len(ruta) > 1 else "")
        eps = _endpoints_alcanzables(f)
        unidad_src = " ".join(codigo(x) for x in alcanza(f))
        out.append(Pantalla(
            ruta=ruta, archivo=f, seccion=seccion,
            roles=_roles_por_seccion()[seccion],
            lecturas=tuple(sorted(x for x in eps if x[0] == "GET" and not _es_export(x[1]))),
            exports=tuple(sorted(x for x in eps if _es_export(x[1]))),
            escrituras=tuple(sorted(x for x in eps if x[0] != "GET")),
            filtra=("FiltersBar" in unidad_src or "useFiltros" in unidad_src),
            pagina="<Pagination" in unidad_src,
            apagada=_apagada(f, eps),
        ))
    if len(out) < MINIMO_PANTALLAS:
        raise SystemExit(
            f"ABORTADO: se encontraron {len(out)} pantallas y el mínimo es {MINIMO_PANTALLAS}. "
            "El recorrido del árbol del front se rompió.")
    return out
