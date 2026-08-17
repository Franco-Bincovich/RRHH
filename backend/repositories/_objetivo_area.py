"""
El filtro por área involucrada: el único de los seis que compara contra un `text[]`.

Vive aparte de `_objetivo_filtros.py` por el MISMO criterio con el que
`aplicar_filtro_responsable` vive en `_objetivo_responsables.py`: los cuatro filtros planos son un
`.eq()` que se explica solo, y estos dos tienen un predicado que hay que razonar. Con este bloque
adentro, `_objetivo_filtros` quedaba en 122 contra un tope de 100.
"""
from utils.postgrest_array import literal_array


def por_area(q, area: str):
    """Objetivos cuyas `areas_involucradas` CONTIENEN esa área. Comparación por ELEMENTO.

    🔴 ES LA RAZÓN ENTERA POR LA QUE LA MIGRACIÓN 119 PASÓ LA COLUMNA DE `text` A `text[]`.
    Con texto plano el filtro no podía ser honesto de dos maneras a la vez: `ILIKE '%Sistemas%'`
    también matcheaba "Sistemas Corporativos" —que es OTRA área—, y el desplegable de valores ya
    usados ofrecía la CELDA entera ("Sistemas; Legales") en vez de cada área. Con `@>` la
    comparación es por elemento completo: "Sistemas" no matchea "Sistemas Corporativos", y sí
    matchea una fila cuyo array sea `{Sistemas, Legales}` aunque el área no esté primera.

    🔴 EL VALOR VIAJA COMO LITERAL DE ARRAY YA COMILLADO, no como lista de Python, y esto NO es
    ceremonia: `.contains(col, ["Legales, Compliance"])` hace `",".join(...)` sin comillar
    (verificado en `postgrest/base_request_builder.py:451-454`), así que PostgREST recibiría DOS
    elementos, la consulta pasaría a significar "que contenga Legales Y Compliance", devolvería
    cero filas y **no habría ningún error**. El escapado y su porqué viven en
    `utils.postgrest_array`.

    ⚠️ UN área por vez, no una lista. Con dos elementos `@>` pide LOS DOS (es AND, no OR), que no
    es lo que una pantalla con un desplegable simple significa. El día que haya multiselect, la
    decisión AND-vs-OR hay que tomarla a propósito acá — `literal_array` ya acepta la lista.

    Args:
        q: Query de Supabase en construcción.
        area: UN área, tal como la escribió el usuario. No se normaliza ni se recorta.

    Returns:
        La query con el predicado de contención puesto.
    """
    return q.contains("areas_involucradas", literal_array([area]))
