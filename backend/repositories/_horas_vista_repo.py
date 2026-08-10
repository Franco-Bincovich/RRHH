"""
Lecturas de `horas_proyecto` para la vista interna "Horas por cliente", más la baja que RRHH
hace desde ahí.

SATÉLITE DE `horas_repo.py`, que está en 98/100 y no admitía cuatro métodos más. El corte es
por forma de la lectura, igual que `_empleado_lookup_repo` respecto de `empleado_repo`: allá
queda "las horas de ESTE proyecto / ESTA asignación" (el camino viejo) y acá "las horas de ESTE
período", que es la pregunta de la pantalla nueva.

🔴 TRAE LOS DOS CAMINOS DE CARGA, y es una decisión, no un descuido:
  · las del link público   → `empleado_id` con valor, `proyecto_id` NULL, `cliente_id` con valor
  · las del camino viejo   → `empleado_id` NULL, `proyecto_id` con valor, `cliente_id` NULL
El filtro es por `fecha` y `empresa_id`, que las DOS formas tienen NOT NULL, así que no se cae
ninguna. Quién resuelve al empleado de cada una es `_hora_row.build`, que ya sabe hacerlo por
los dos orígenes. Filtrar por `cliente_id IS NOT NULL` habría sido lo cómodo para una pantalla
que agrupa por cliente, y habría hecho DESAPARECER en silencio las horas del camino viejo — que
es el modo de falla que este repo ya documentó tres veces.

🔴 LA BARRERA DE EMPRESA VA EN EL WHERE (Forma A), nunca comparada en Python después.
`empresa_id=None` es la vista consolidada y no restringe.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._hora_row import build
from schemas.horas import HoraResponse

_T = "horas_proyecto"


def _con_empresa(q, empresa_id: Optional[UUID]):
    """Barrera de empresa. None = consolidado, sin filtro."""
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def find_por_periodo(desde: str, hasta: str,
                     empresa_id: Optional[UUID] = None) -> List[HoraResponse]:
    """Todas las horas del período, más recientes primero. Insumo del listado Y del export.

    Los dos consumen ESTA función, que es lo que hace estructuralmente imposible que el archivo
    traiga filas que la pantalla no muestra (invariante 1 del bloque B)."""
    q = _con_empresa(supabase_admin.table(_T).select("*"), empresa_id)
    filas = q.gte("fecha", desde).lte("fecha", hasta).order("fecha", desc=True).execute().data
    return build(filas or [])


def find_por_empleado(empleado_id: str, desde: str, hasta: str,
                      empresa_id: Optional[UUID] = None) -> List[HoraResponse]:
    """Las cargas día por día de UN empleado en el período. Es el "ver detalle" del mockup.

    Va por `empleado_id`, así que las del camino viejo aparecen igual: `_hora_row.build` les
    resuelve el empleado por la asignación, pero la COLUMNA está en NULL — por eso el filtro se
    hace en Python sobre el resultado ya enriquecido y no en el WHERE. Es una lista de un mes de
    una empresa; el costo es el mismo que el del listado, que ya se trajo entero."""
    return [h for h in find_por_periodo(desde, hasta, empresa_id)
            if str(h.empleado_id or "") == str(empleado_id)]


def find_by_id(hora_id: str, empresa_id: Optional[UUID] = None) -> Optional[HoraResponse]:
    """Una carga, o None si no existe O es de otra empresa. Los dos casos son el mismo 404."""
    q = _con_empresa(supabase_admin.table(_T).select("*").eq("id", hora_id), empresa_id)
    filas = q.execute().data or []
    return build(filas)[0] if filas else None


def delete(hora_id: str, empresa_id: Optional[UUID] = None) -> bool:
    """Borra la carga. La barrera va EN EL DELETE, no solo en la lectura previa: sin el `.eq`
    acá, un id de otra empresa se borraría igual y recién la relectura devolvería None — la
    fila ya no estaría."""
    q = _con_empresa(supabase_admin.table(_T).delete().eq("id", hora_id), empresa_id)
    return bool(q.execute().data)
