"""
Filtro por rango de fechas para registros que ocupan un PERÍODO (fecha_desde / fecha_hasta).

Lo comparten vacaciones y ausencias. Una sola implementación, server-side: si viviera en cada
repo serían dos copias de la misma regla, y si viviera en el front el export no la vería y
descargaría más filas de las que se ven en pantalla.

🔴 SEMÁNTICA: SOLAPAMIENTO, NO CONTENCIÓN.
"Las vacaciones de marzo" incluye una licencia del 25/2 al 5/3: empezó antes pero cae dentro
del período que se está mirando. Con contención esa fila desaparecería del listado, y también
del total — que es peor, porque un reporte de ausentismo del mes dejaría afuera justo los casos
que cruzan el borde, que son los que más importan.

Y no es una preferencia estética: es la MISMA semántica que ya usa
`services/_periodo_utils._solapa` para decidir si una solicitud cae dentro de un período
cerrado. Tener dos definiciones de "esta solicitud pertenece a este período" en el mismo módulo
—una para bloquear la carga y otra para listar— es un bug esperando a que alguien las compare.

La condición es:  solicitud.fecha_desde <= hasta  AND  solicitud.fecha_hasta >= desde

Escrita así, las dos mitades son INDEPENDIENTES, y de ahí sale gratis el soporte de rangos
abiertos: con solo `desde` se pide "todo lo que siga vigente desde esa fecha en adelante", con
solo `hasta` "todo lo que haya empezado hasta esa fecha", y sin ninguno no se filtra nada.

⚠️ Un rango invertido (desde > hasta) NO se rechaza. El predicado sigue siendo válido y
devuelve las solicitudes que cubren el hueco entero, que no es lo que nadie quiso pedir. No se
valida acá a propósito: es la UI la que tiene que impedir armarlo (con `min`/`max` en los dos
inputs), no el repo el que tiene que adivinar la intención.
"""
from datetime import date


def aplicar_rango(q, desde: date | None, hasta: date | None):
    """Acota la query a las filas cuyo período se SOLAPA con [desde, hasta].

    Args:
        q: Query de Supabase en construcción.
        desde: Inicio del rango pedido. None = sin cota inferior.
        hasta: Fin del rango pedido. None = sin cota superior.

    Returns:
        La query con el filtro aplicado (sin cambios si los dos son None).
    """
    if desde:
        q = q.gte("fecha_hasta", str(desde))
    if hasta:
        q = q.lte("fecha_desde", str(hasta))
    return q
