"""
El ORDEN del listado de empleados: el default de siempre y los dos órdenes por fecha.

Salió de `_empleado_row.py` el 20/8/2026, al dejar de ser un `return` de una línea. El corte NO
es por tamaño: los otros dos query-shapers de allá (`with_empresa`, `filtro_estado`) siguen
siendo UN predicado cada uno, y esto pasó a ser un vocabulario, una tabla de traducción y una
regla sobre el desempate. Son dos cosas distintas y ahora se leen por separado. La mitad que mira
hacia afuera —los valores que el router acepta— vive en `schemas/_empleado_orden.py`.

⚠️ El barrido de desempate (`tests/test_paginacion_orden.py::_sin_desempate`) resuelve UN nivel
de delegación indexando las funciones de `repositories/*.py` **por nombre**, así que mudar
`ordenado` de archivo no lo esconde: lo sigue encontrando y `empleado_repo.find_all` sigue
cubierto. Si algún día se lo renombra, hay que mirar ese barrido.
"""
from typing import Dict, Optional, Tuple

# La traducción del vocabulario de la API a (columna, descendente). Vive de este lado porque son
# nombres de COLUMNA: el schema publica qué se puede pedir, el repo sabe contra qué se traduce.
ORDENES: Dict[str, Tuple[str, bool]] = {
    # Próximos ingresos: quién entra primero. `fecha_ingreso` es NOT NULL, así que acá no hay
    # ninguna pregunta de nulos que contestar.
    "fecha_ingreso_asc": ("fecha_ingreso", False),
    # Bajas: quién se fue último. Ver la nota de NULOS en `ordenado()`.
    "fecha_egreso_desc": ("fecha_egreso", True),
}


def ordenado(q, orden: Optional[str] = None):
    """Aplica el orden del listado. Sin `orden`, el de siempre: apellido, nombre y `id`.

    🔴 HASTA EL 14/8/2026 ESTE LISTADO PAGINABA SIN NINGÚN `.order()`. Un `.range()` sobre un
    SELECT sin orden le deja a Postgres elegir el orden de las filas, y no tiene por qué elegir
    el mismo en dos consultas distintas: la página 2 podía repetir a alguien de la 1 o saltearlo.
    No daba error ni se veía en los tests — se veía como un empleado que "no está en la lista".

    🔴 EL `id` NO ES DECORACIÓN, Y VA EN LAS DOS RAMAS. `apellido, nombre` no es un orden TOTAL:
    en el padrón de escala 411 de 1.005 personas comparten los dos campos con alguien. Y una
    FECHA empata todavía más fácil que un apellido —un lote de altas entra todo el mismo día, y
    `fecha_ingreso` no tiene hora—, así que en las ramas nuevas el desempate no es el borde: es
    el caso normal. Entre empatados Postgres no garantiza un orden estable entre ejecuciones, así
    que sin el `id` el bug de arriba vuelve entero.

    ⚠️ El `id` va ASCENDENTE SIEMPRE, incluso cuando la fecha va DESC. Lo pide la forma de los
    índices: `idx_empleados_empresa_apellido (empresa_id, apellido, nombre, id)` (migración 118)
    se creó así, y pedir el desempate al revés obligaría a un nodo de sort que el índice existe
    para evitar. En las ramas por fecha hoy NO hay índice que las sirva (ver el reporte de la
    sesión): el `id` ascendente las deja listas para el día que se creen.

    🔴 `fecha_egreso_desc` DEJA LOS NULOS ARRIBA, y es un límite MEDIDO del cliente, no una
    elección. En Postgres un `ORDER BY ... DESC` es `NULLS FIRST` por default, y `postgrest`
    0.17.2 expone `nullsfirst=True` pero **no tiene `nullslast`** (`base_request_builder.order`),
    así que `NULLS LAST` no se puede expresar desde acá. Consecuencia concreta: una baja a la que
    nadie le cargó `fecha_egreso` —hoy alcanzable con un `PUT /api/empleados/{id}` que mande
    `estado: "baja"`, que no pasa por `dar_de_baja` y no escribe la fecha— sale ARRIBA de las
    bajas recientes en vez de al final. Está pineado en `tests/test_empleado_orden.py` para que
    sea una conducta declarada y no un accidente que alguien descubra en pantalla.

    Args:
        q: la query de Supabase ya construida (con sus filtros aplicados).
        orden: uno de `ORDENES`, o None para el orden por defecto. La validación del valor la
            hizo Pydantic en el router (`OrdenEmpleados`); acá un valor desconocido sería un bug
            de programación y revienta con KeyError, que es lo correcto: no es entrada de usuario.

    Returns:
        La query con el orden aplicado.
    """
    if orden is None:
        return q.order("apellido").order("nombre").order("id")
    columna, desc = ORDENES[orden]
    return q.order(columna, desc=desc).order("id")
