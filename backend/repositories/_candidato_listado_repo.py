"""
El LISTADO de candidatos: su query base, su página y el conteo por búsqueda.

SALIÓ DE `candidato_repo.py`, que estaba en 100/100 exacto —ya partido tres veces— cuando le
tocaba sumar la paginación y el conteo por grupo. Se lleva la parte que CRECE: cada filtro nuevo
del listado se suma acá y no empuja al repo.

🔴 EL CONTEO POR GRUPO SE RESUELVE EN UNA SOLA QUERY, no en una por grupo.
La pantalla agrupa por búsqueda (`grupo_nombre`) y su encabezado dice cuántos candidatos tiene
cada una EN TOTAL, no cuántos entraron en la página. La forma obvia de conseguir eso —un
`count` por vacante— es exactamente el patrón que el diagnóstico de escala marcó en
`/api/procesos`: una query por cada valor de estado cuando lo que se necesita es un GROUP BY.
Con 200 búsquedas serían 200 round trips.

Acá se trae UNA vez la columna de agrupamiento de todo el conjunto filtrado y se cuenta en
Python. Es el mismo patrón que `_area_row.counts_by_area()`, que cuenta empleados por área con
un solo `select("area_id")`. Lo que viaja son dos columnas por fila —un uuid y un texto corto—,
no la fila del candidato con su CV y su clasificación.

⚠️ PostgREST no expone `GROUP BY`. La alternativa real sería una RPC, y no se hizo porque
agregaría una función SQL versionada aparte para ahorrar un recorrido en memoria sobre un
conjunto que ya está acotado por los mismos filtros que el listado.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._candidato_row import _crow
from schemas.candidato import CandidatoResponse

TABLE = "candidatos"


def base(empresa_id: Optional[UUID], sin_vacante: bool, clasificacion: Optional[str],
         columnas: str = "*", contar: bool = False):
    """La query del listado. UNA definición para la página, el total y el conteo por grupo.

    🔴 Los tres filtros van EN EL WHERE, no en Python. Es la invariante del Bloque B: el export
    va por el mismo camino, y un filtro aplicado en la capa de arriba haría que el archivo
    saliera con más filas de las que muestra la pantalla, sin error y sin aviso.
    """
    q = supabase_admin.table(TABLE).select(columnas, count="exact") if contar \
        else supabase_admin.table(TABLE).select(columnas)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    if sin_vacante:
        q = q.is_("vacante_id", "null")
    # En el WHERE, no en Python. `sin_clasificar` es un valor; `None` = no filtres.
    if clasificacion == "sin_clasificar":
        q = q.is_("clasificacion_ia", "null")
    elif clasificacion:
        q = q.eq("clasificacion_ia", clasificacion)
    return q


def todos(empresa_id: Optional[UUID] = None, sin_vacante: bool = False,
          clasificacion: Optional[str] = None) -> List[CandidatoResponse]:
    """TODOS los candidatos del filtro, más recientes primero. Sin paginar."""
    q = base(empresa_id, sin_vacante, clasificacion).order("created_at", desc=True).order("id")
    return [_crow(r) for r in (q.execute().data or [])]


def pagina(empresa_id: Optional[UUID] = None, sin_vacante: bool = False,
           clasificacion: Optional[str] = None, page: int = 1, page_size: int = 20,
           ) -> Tuple[List[CandidatoResponse], int]:
    """Una página del listado + el total real del filtro.

    `.order("id")` = desempate. Los candidatos entran por lotes desde la casilla de mail —una
    corrida de "Revisar casilla" crea varios con el mismo `created_at` al segundo— así que los
    empates son la norma. ASC aunque la fecha vaya DESC: es la forma de
    `idx_candidatos_empresa_created` (migración 118).
    """
    res = (base(empresa_id, sin_vacante, clasificacion, contar=True)
           .order("created_at", desc=True).order("id")
           .range((page - 1) * page_size, page * page_size - 1).execute())
    return [_crow(r) for r in (res.data or [])], (res.count or 0)


def claves_de_grupo(empresa_id: Optional[UUID] = None, sin_vacante: bool = False,
                    clasificacion: Optional[str] = None) -> List[dict]:
    """La clave de agrupamiento de CADA fila del filtro: `{vacante_id, busqueda_congelada}`.

    Dos columnas, una query, todo el conjunto. El service las convierte en nombres de grupo y
    cuenta — ver el encabezado del módulo para por qué no es un `count` por búsqueda.
    """
    q = base(empresa_id, sin_vacante, clasificacion, columnas="vacante_id, busqueda_congelada")
    return q.execute().data or []
