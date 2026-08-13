"""
Armado de la query del listado de objetivos: el ORDEN, los cuatro FILTROS y el predicado de
empresa que el resto del repo repetía en cuatro lugares.

Salió de `objetivo_repo.py`, que estaba en 100/100 contra su límite. Molde:
`_rango_fechas.aplicar_rango(q, ...)` y `_objetivo_responsables.aplicar_filtro_responsable(q, ...)`
— funciones libres que reciben la query EN CONSTRUCCIÓN y la devuelven con el predicado puesto.

🔴 ACÁ NO SE CONSTRUYE LA QUERY, SE LA RECIBE — y no es una preferencia de estilo.
El espía de `test_objetivos.py::TestLaQueryDelRepo` parchea `supabase_admin` MÓDULO POR MÓDULO
(hoy tres: `objetivo_repo`, `_objetivo_responsables` y `_objetivos_arbol`). Un satélite que
importara el cliente por su cuenta quedaría sin parchear, y esos tests dejarían de fallar por una
aserción para fallar con ConnectError contra la red de verdad — un rojo que no dice nada. Ya pasó
en este mismo módulo al mover el filtro por responsable a su satélite, y está escrito en el
docstring de `_repo_con_espia`. Por eso `supabase_admin.table(...)` se queda en el repo.

⚠️ El orden de encadenado se conserva tal cual estaba en `find_all`: primero el `.order()`,
después los `.eq()`. Para PostgREST da igual —son parámetros independientes de la request— pero
conservarlo deja el movimiento puro y no obliga a releer los tests que afirman sobre la query.

📌 QUÉ CRECE ACÁ Y QUÉ NO. Los filtros nuevos del módulo (periodicidad, áreas involucradas) son
una línea en `aplicar_filtros` y CERO líneas en el repo, que es el punto del corte. El
`.order()` vive aparte del filtrado justamente porque las vistas nuevas pueden querer otro orden
sin tocar los filtros.
"""
from typing import Optional
from uuid import UUID

from repositories._objetivo_responsables import aplicar_filtro_responsable


def con_empresa(q, empresa_id: Optional[UUID]):
    """Filtro de empresa EN LA QUERY. None = vista consolidada: no restringe.

    Molde: `_empleado_row.with_empresa`. Vive acá porque `find_by_id`, `update`, `set_estado` y
    `delete` repetían el mismo `if` de dos líneas, y el listado necesita exactamente el mismo
    predicado.
    """
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def aplicar_orden(q):
    """Ordena el listado por fecha de entrega ASCENDENTE: lo primero que vence, arriba.

    Va en la QUERY y no en Python: ordenar después de traer las filas depende de haberlas traído
    todas, así que con paginación el orden sería el de la página y no el del conjunto.
    """
    return q.order("fecha_entrega", desc=False)


def aplicar_filtros(
    q,
    empresa_id:     Optional[UUID] = None,
    estado:         Optional[str]  = None,
    responsable_id: Optional[str]  = None,
    prioridad:      Optional[str]  = None,
):
    """Acota la query del listado con los cuatro filtros, compuestos por AND.

    El AND lo da el encadenado de PostgREST: cada predicado se suma al anterior. Un filtro en
    None no agrega nada — no es "traer todo", es "no restringir por ese eje".

    ⚠️ `responsable_id` NO es un `.eq()`: desde la migración 096 el responsable puede estar en la
    tabla puente sin ser el dueño, así que el predicado lo arma `aplicar_filtro_responsable`, que
    mira los DOS lados. Ver el encabezado de `_objetivo_responsables`.

    Args:
        q: Query de Supabase en construcción.
        empresa_id: Empresa del request. None = consolidado.
        estado: por_hacer | haciendo | terminado.
        responsable_id: user id; matchea por la puente O por ser el dueño.
        prioridad: baja | media | alta.

    Returns:
        La query con los filtros aplicados (sin cambios si los cuatro son None).
    """
    q = con_empresa(q, empresa_id)
    if estado:         q = q.eq("estado",    estado)
    if prioridad:      q = q.eq("prioridad", prioridad)
    if responsable_id: q = aplicar_filtro_responsable(q, responsable_id)
    return q
