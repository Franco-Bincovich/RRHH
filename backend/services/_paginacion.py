"""
Los metadatos de paginación de un listado, en un solo lugar.

POR QUÉ EXISTE. `total_pages` es una división con un caso borde (`page_size = 0`), y estaba
escrita a mano en `empleado_service`. Con seis listados paginados y catorce en camino, seis copias
de la misma división es la forma más barata de que dos módulos empiecen a contar páginas distinto
sobre el mismo total. Acá hay una definición y ninguna más.

🔴 EL OTRO MOTIVO, Y ES EL QUE IMPORTA: `sin_paginar()` tiene nombre propio para que se lea como
un estado transitorio. Un listado que devuelve todo y reporta `total = len(items)` es CORRECTO
—las que hay son las que mandó— pero deja de serlo en el instante en que alguien le agrega
`.range()` al repo y no toca el total. Ahí `total` pasa a valer el largo de la página en silencio,
la barra dice "1 de 1" y no hay error que lo delate.

**Ya pasó, en la misma tanda que trajo este archivo:** la pantalla de horas de un proyecto sumaba
sus totales sobre la página visible y decía "9 h" sobre un proyecto de 400. El `.reduce()` era
correcto cuando se escribió, y siguió compilando cuando dejó de serlo.

CÓMO SE MIGRA UN LISTADO A PAGINACIÓN DE VERDAD (los tres pasos, en este orden):
  1. el repo pide `count="exact"` y aplica `.range(...)`, y **devuelve `(items, count)`** — el
     count viaja en la MISMA query, no en una segunda;
  2. el repo lleva su orden TOTAL, con `.order("id")` de desempate (ver tests/test_paginacion_orden.py);
  3. el service reemplaza `**sin_paginar(items)` por los valores reales:
         total=count, page=page, page_size=page_size,
         total_pages=cantidad_paginas(count, page_size)
     Molde completo: `empleado_service.get_empleados`.
"""
import math


def cantidad_paginas(total: int, page_size: int) -> int:
    """Cuántas páginas hacen falta para `total` filas de a `page_size`.

    `page_size = 0` devuelve 0 en vez de reventar con ZeroDivisionError. Es el comportamiento que
    ya tenía `empleado_service` y se conserva: un listado vacío reporta 0 páginas, y la barra del
    front lo normaliza a 1 (`Math.max(1, ...)` en Pagination.tsx) para no dibujar "página 1 de 0".

    Args:
        total: Filas que devuelve el filtro, sin paginar.
        page_size: Tamaño de página pedido.

    Returns:
        Cantidad de páginas; 0 si `page_size` no es positivo.
    """
    return math.ceil(total / page_size) if page_size > 0 else 0


def sin_paginar(items: list) -> dict:
    """Los cuatro metadatos de un listado que devuelve TODO en una sola página.

    Se expande con `**` en el constructor del ListResponse:

        return ItemListResponse(items=items, **sin_paginar(items))

    🔴 Que `total` salga de `len(items)` es correcto SOLO mientras el listado no recorte. En
    cuanto el repo pagine, este helper miente: hay que reemplazarlo por los valores reales (los
    tres pasos del encabezado). El nombre está elegido para que el reemplazo sea obvio — un
    `sin_paginar()` en un listado que sí pagina se lee mal a propósito.

    Args:
        items: La lista completa que se va a devolver.

    Returns:
        dict con total, page, page_size y total_pages, listo para expandir con `**`.
    """
    n = len(items)
    # `page_size = n` y no una constante: la página ES todo el resultado, así que su tamaño es el
    # del resultado. Con eso `total_pages` da 1 (y 0 con la lista vacía, como el resto del repo).
    return {"total": n, "page": 1, "page_size": n, "total_pages": cantidad_paginas(n, n)}
