"""
Armado de la query del listado de objetivos: el ORDEN, los SEIS filtros y el predicado de
empresa que el resto del repo repetía en cuatro lugares.

Salió de `objetivo_repo.py`, que estaba en 100/100 contra su límite. Molde:
`_rango_fechas.aplicar_rango(q, ...)` y `_objetivo_responsables.aplicar_filtro_responsable(q, ...)`
— funciones libres que reciben la query EN CONSTRUCCIÓN y la devuelven con el predicado puesto.

🔴 ACÁ NO SE CONSTRUYE LA QUERY, SE LA RECIBE — y no es una preferencia de estilo.
El espía de `test_objetivos.py::TestLaQueryDelRepo` parchea `supabase_admin` MÓDULO POR MÓDULO
(hoy tres: `objetivo_repo`, `_objetivo_responsables` y `_objetivos_arbol`). Un satélite que
importara el cliente por su cuenta quedaría sin parchear, y esos tests dejarían de fallar por una
aserción para fallar con ConnectError contra la red de verdad — un rojo que no dice nada. Ya pasó
en este mismo módulo al mover el filtro por responsable a su satélite. Por eso `supabase_admin.table(...)`
se queda en el repo. (`utils.postgrest_array` no rompe la regla: es una función pura de strings,
no toca la base.)

⚠️ El orden de encadenado se conserva tal cual estaba en `find_all`: primero el `.order()`,
después los `.eq()`. Para PostgREST da igual —son parámetros independientes de la request— pero
conservarlo deja el movimiento puro y no obliga a releer los tests que afirman sobre la query.

🔴 LOS FILTROS ENTRAN EN UN OBJETO, NO COMO PARÁMETROS SUELTOS. `aplicar_filtros` recibe un
`ObjetivosFiltros` entero. Con los tres filtros de la migración 119 eran SIETE `Optional[str]` en
fila, que es el corrimiento silencioso de argumentos que el bloque B ya pagó en vacaciones y
ausencias. El porqué completo —y lo que el objeto NO resuelve— está en `schemas/objetivo_filtros.py`.
El único que queda suelto es `empresa_id`: es la barrera multiempresa, no un filtro de pantalla.

📌 QUÉ CRECE ACÁ Y QUÉ NO. Un filtro nuevo es un campo en `ObjetivosFiltros` y una línea acá, y
CERO líneas en el repo — que es el punto del corte. El `.order()` vive aparte del filtrado
justamente porque las vistas nuevas pueden querer otro orden sin tocar los filtros.
"""
from typing import Optional
from uuid import UUID

from repositories._objetivo_area import por_area
from repositories._objetivo_responsables import aplicar_filtro_responsable
from schemas.objetivo_filtros import SIN_FILTROS, ObjetivosFiltros


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


def aplicar_filtros(q, empresa_id: Optional[UUID] = None,
                    filtros: ObjetivosFiltros = SIN_FILTROS):
    """Acota la query del listado con los seis filtros, compuestos por AND.

    El AND lo da el encadenado de PostgREST: cada predicado se suma al anterior. Un filtro en
    None no agrega nada — no es "traer todo", es "no restringir por ese eje".

    CÓMO COMPARA CADA UNO, que no es lo mismo en los seis:

      · `estado`, `prioridad`, `tipo` → `.eq()`. Los tres son vocabulario cerrado por CHECK, así
        que el valor que llega es exactamente uno de los literales de la base.
      · `periodicidad` → `.eq()` TAMBIÉN, y no `.ilike()`. Es texto libre, así que la tentación es
        comparar sin distinguir mayúsculas; se descartó por el mismo motivo que en
        `cliente_repo.existe_nombre`: **PostgREST interpreta `*` como comodín dentro de `ilike`**,
        y una periodicidad escrita "1er trim*" pasaría a matchear cualquier cosa. Y no hace falta:
        el desplegable le ofrece al usuario los valores TAL COMO ESTÁN GUARDADOS, así que lo que
        elige es el string exacto. Si además existe "Anual" y "anual", son dos entradas distintas
        del desplegable — que es honesto, porque son dos strings distintos en la base.
      · `area` → `.contains()`. Ver `por_area`.
      · `responsable_id` → NO es un `.eq()`: desde la migración 096 el responsable puede estar en
        la tabla puente sin ser el dueño, así que el predicado lo arma `aplicar_filtro_responsable`,
        que mira los DOS lados. Ver el encabezado de `_objetivo_responsables`.

    Args:
        q: Query de Supabase en construcción.
        empresa_id: Empresa del request. None = consolidado. NO viene en `filtros` a propósito:
            es la barrera multiempresa, no un filtro de pantalla.
        filtros: El objeto con los seis. Su default es `SIN_FILTROS`, que no restringe nada.

    Returns:
        La query con los filtros aplicados (sin cambios si no hay ninguno puesto).
    """
    q = con_empresa(q, empresa_id)
    if filtros.estado:         q = q.eq("estado",       filtros.estado)
    if filtros.prioridad:      q = q.eq("prioridad",    filtros.prioridad)
    if filtros.tipo:           q = q.eq("tipo",         filtros.tipo)
    if filtros.periodicidad:   q = q.eq("periodicidad", filtros.periodicidad)
    if filtros.area:           q = por_area(q, filtros.area)
    if filtros.responsable_id: q = aplicar_filtro_responsable(q, filtros.responsable_id)
    return q
