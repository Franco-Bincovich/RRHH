"""
LAS ACCIONES DE ESCRITURA: un botón, un modal o un control por fila, con la pantalla donde vive,
el endpoint que llama, el rol que lo ve y si deja el sistema cambiado sin vuelta.

🔴 QUÉ SE DERIVA Y QUÉ NO — leer esto antes de usar la lista, porque la diferencia importa.
LA UNIDAD DE ESTA LISTA ES «EL COMPONENTE QUE IMPORTA UNA FUNCIÓN DE ESCRITURA Y LA LLAMA»,
no «el botón». Son casi lo mismo y no exactamente lo mismo:
  · Un componente con DOS botones que llaman a la MISMA función (Guardar arriba y Guardar abajo)
    da UNA fila. Sub-cuenta, y es el único lado por el que esta lista sub-cuenta.
  · Un componente con un `<Button>` que llama a dos funciones distintas da DOS filas. Sobre-cuenta.
  · Un `onSubmit` de formulario, un `onChange` de un toggle y un `onClick` de un botón son
    indistinguibles acá: los tres se leen como "el componente llama a la función".
LO QUE NO SE PUEDE DERIVAR DEL CÓDIGO ESTÁTICO, y por eso no está en ninguna columna:
  · EL TEXTO DEL BOTÓN. Vive en el JSX, muchas veces armado con un ternario sobre el estado
    (`{editando ? "Guardar" : "Crear"}`), y atarlo al `onClick` correcto pide un parser de JSX
    de verdad. La columna dice el COMPONENTE, que es lo que un tester puede abrir y buscar.
  · SI EL CONTROL ESTÁ VISIBLE. Casi todos cuelgan de `useCanWrite()` o de un `canWrite &&`, pero
    también hay condiciones de estado (un botón que sólo aparece si la vacante está abierta). El
    rol que figura es el que el BACKEND exige, que es el que decide si la llamada entra.
  · CUÁNTAS VECES SE PUEDE APRETAR sin consecuencia. La idempotencia es del backend y no se lee
    desde el front.

🔑 SE ATRIBUYE POR EL GRAFO DE IMPORTS Y ES TRANSITIVO. Un componente puede vivir en varias
pantallas (`AdjuntosPanel` está en la ficha del empleado, en vacaciones y en ausencias) y
entonces la fila lista las tres: no se elige una. Un componente que no cuelga de ninguna página
sale con pantalla vacía, y eso es un hallazgo, no un vacío del inventario.
"""
from functools import lru_cache
from typing import Dict, List, NamedTuple, Set, Tuple

import re

from _inv_cobertura import veredicto
from _inv_destructivo import es_destructivo
from _inv_front import alcanza, codigo
from _inv_llamadas import funciones_importadas, llamadas_por_funcion
from _inv_pantallas import Pantalla, pantallas

# Guarda contra el falso verde: si el grafo de imports o el mapa de llamadas se rompen, esto
# muerde antes de que el inventario declare "no hay acciones de escritura". Medido: 139 el 23/8.
MINIMO_ACCIONES = 120


class Accion(NamedTuple):
    componente: str
    funcion: str
    modulo: str                     # archivo de services/ del que sale la función
    endpoints: Tuple[Tuple[str, str], ...]
    rutas: Tuple[str, ...]          # pantallas donde vive
    roles: Tuple[str, ...]
    destructivo: bool
    razon: str
    automatizable: str
    motivo: str


def _llama(fuente: str, nombre: str) -> bool:
    """¿Este archivo INVOCA la función, o sólo la importa y la reexporta?"""
    return bool(re.search(r"\b" + re.escape(nombre) + r"\s*\(", fuente))


@lru_cache(maxsize=1)
def _pantallas_de_componente() -> Dict[str, Set[str]]:
    """archivo -> rutas de las pantallas desde las que se llega a él.

    🔴 LOS LAYOUTS TAMBIÉN SON RAÍZ, y sin ellos se pierde una acción REAL: el botón de cerrar
    sesión vive en `components/layout/UserMenu.tsx`, que cuelga de `app/(dashboard)/layout.tsx`
    y de NINGÚN `page.tsx`. Atribuyendo sólo desde las páginas, la única escritura que un usuario
    dispara en TODAS las pantallas salía con la columna de pantalla vacía. El sidebar y el header
    entero están del mismo lado de esa frontera.
    """
    out: Dict[str, Set[str]] = {}
    for p in pantallas():
        for f in alcanza(p.archivo):
            out.setdefault(f, set()).add(p.ruta)
    for layout in sorted(f for f in _layouts()):
        etiqueta = "(layout) " + ("/" + layout[len("app/"):-len("/layout.tsx")] if
                                  layout != "app/layout.tsx" else "raíz")
        for f in alcanza(layout):
            out.setdefault(f, set()).add(etiqueta)
    return out


def _layouts() -> List[str]:
    from _inv_front import archivos
    return [f for f in archivos() if f.startswith("app/") and f.endswith("/layout.tsx")]


def _roles(rutas: Set[str]) -> Tuple[str, ...]:
    """Roles que ven la acción: los de las pantallas donde vive, INTERSECADOS con escritura.

    🔴 La intersección con `write` es la mitad que importa. `gerencia_lectura` LEE todas las
    pantallas, así que tomar los roles de la pantalla a secas diría que gerencia ve el botón de
    borrar — y el backend le responde 403. La pregunta de esta columna es quién puede EJECUTAR.
    """
    from _inv_backend import _preparar
    _preparar()
    from utils.permisos import ROLES_VALIDOS, puede
    por_ruta = {p.ruta: p.seccion for p in pantallas()}
    secciones = {por_ruta.get(r) for r in rutas}
    if None in secciones:                       # una pantalla sin gate de ruta no restringe
        return tuple(sorted(ROLES_VALIDOS))
    return tuple(sorted(r for r in ROLES_VALIDOS
                        if any(puede(r, s, "write") for s in secciones if s)))


@lru_cache(maxsize=1)
def acciones() -> List[Accion]:
    """Una fila por (componente, función de escritura). Aborta si el descubrimiento se rompió."""
    llamadas = llamadas_por_funcion()
    importadas = funciones_importadas()
    ubicacion = _pantallas_de_componente()
    con_flag = _flageados()
    out: List[Accion] = []
    for archivo, claves in sorted(importadas.items()):
        if archivo.startswith("services/"):     # composición interna, no es un control de la UI
            continue
        fuente = codigo(archivo)
        for modulo, nombre in sorted(claves):
            eps = [e for e in llamadas.get((modulo, nombre), ()) if e[0] != "GET"]
            if not eps or not _llama(fuente, nombre):
                continue
            rutas = ubicacion.get(archivo, set())
            metodo, path = eps[0]
            destructivo, razon = es_destructivo(metodo, path)
            apagada = next((p.apagada for p in pantallas() if p.ruta in rutas and p.apagada), None)
            v = veredicto(metodo, path, (metodo, path) in con_flag, apagada)
            out.append(Accion(
                componente=archivo, funcion=nombre, modulo=modulo,
                endpoints=tuple(eps), rutas=tuple(sorted(rutas)), roles=_roles(rutas),
                destructivo=destructivo, razon=razon,
                automatizable=v.automatizable, motivo=v.motivo))
    if len(out) < MINIMO_ACCIONES:
        raise SystemExit(
            f"ABORTADO: se encontraron {len(out)} acciones de escritura y el mínimo es "
            f"{MINIMO_ACCIONES}. El grafo de imports o el mapa de llamadas se rompió.")
    return out


@lru_cache(maxsize=1)
def _flageados() -> Set[Tuple[str, str]]:
    """(MÉTODO, path normalizado) de los endpoints que sólo existen con un flag encendido."""
    from _inv_backend import endpoints
    return {(e.metodo, re.sub(r"\{[^}]*\}", "{}", e.path)) for e in endpoints() if e.solo_con_flag}


def sin_pantalla() -> List[Accion]:
    """Acciones cuyo componente no cuelga de ninguna página. Es un HALLAZGO, no un hueco."""
    return [a for a in acciones() if not a.rutas]
