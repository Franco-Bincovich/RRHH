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
El único filtro del listado es por `fecha`, que las DOS formas tienen NOT NULL, así que no se cae
ninguna. Quién resuelve al empleado de cada una es `_hora_row.build`, que ya sabe hacerlo por
los dos orígenes. Filtrar por `cliente_id IS NOT NULL` habría sido lo cómodo para una pantalla
que agrupa por cliente, y habría hecho DESAPARECER en silencio las horas del camino viejo — que
es el modo de falla que este repo ya documentó tres veces.

🔴 EL LISTADO NO SE ACOTA POR EMPRESA, Y ES UNA DECISIÓN DE PRODUCTO (L8).
Las empresas son sociedades de un MISMO grupo económico. Las horas que consume un cliente son
las horas del cliente, venga de la sociedad que venga el empleado que las cargó — así que
`find_por_periodo`, que alimenta el listado Y el export, trae el período completo.

El recorte anterior no era una barrera de seguridad: `horas_proyecto.empresa_id` sale del
EMPLEADO (link público) o del PROYECTO (camino viejo), nunca del cliente. Cuando `clientes` pasó
a ser global (mig 108/109) un mismo cliente empezó a poder recibir horas de las dos sociedades, y
el filtro convirtió el total en un número que la pantalla presentaba como "las horas del cliente"
sin serlo: 3 de 8. El reparto por sociedad no se pierde — se muestra DESGLOSADO dentro de cada
cliente (`_horas_cliente_agrupacion.agrupar`).

🔴 NINGUNA lectura ni la baja se acotan por empresa (L9). Si las horas de un cliente son del
cliente, ver y borrar una carga también lo es: no hay lectura en la que el total sea global y el
detalle no. L8 dejó esa incoherencia a la vista —la pantalla listaba empleados de las dos
sociedades y hacer clic en uno de la otra abría un modal vacío, y borrarlo daba 404—; acá se
cierra. Ningún endpoint de esta vista llama ya a `get_empresa_id`.

⚠️ LO QUE SÍ SIGUE ACOTANDO ES EL `id`. `find_by_id` y `delete` llevan su `.eq("id", ...)` en la
query, y ésa es ahora la ÚNICA guarda sobre qué fila se toca: al sacar el filtro de empresa, un
DELETE sin ese `.eq` se llevaría la tabla entera. Hay un test que lo cubre por mutación.
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from repositories._hora_row import build
from schemas.horas import HoraResponse

_T = "horas_proyecto"


def find_por_periodo(desde: str, hasta: str) -> List[HoraResponse]:
    """TODAS las horas del período, de todas las sociedades. Insumo del listado Y del export.

    No recibe `empresa_id` —no lo ignora: no lo acepta—, así que no hay forma de volver a
    recortarlo por descuido desde un caller. Ver el encabezado.

    Los dos consumidores entran por ESTA función, que es lo que hace estructuralmente imposible
    que el archivo traiga filas que la pantalla no muestra (invariante 1 del bloque B)."""
    q = supabase_admin.table(_T).select("*")
    filas = q.gte("fecha", desde).lte("fecha", hasta).order("fecha", desc=True).execute().data
    return build(filas or [])


def find_por_empleado(empleado_id: str, desde: str, hasta: str) -> List[HoraResponse]:
    """Las cargas día por día de UN empleado en el período. Es el "ver detalle" del mockup.

    Va por `empleado_id`, así que las del camino viejo aparecen igual: `_hora_row.build` les
    resuelve el empleado por la asignación, pero la COLUMNA está en NULL — por eso el filtro se
    hace en Python sobre el resultado ya enriquecido y no en el WHERE."""
    return [h for h in find_por_periodo(desde, hasta)
            if str(h.empleado_id or "") == str(empleado_id)]


def find_by_id(hora_id: str) -> Optional[HoraResponse]:
    """Una carga, o None si no existe. Sin recorte por empresa (L9)."""
    filas = supabase_admin.table(_T).select("*").eq("id", hora_id).execute().data or []
    return build(filas)[0] if filas else None


def delete(hora_id: str) -> bool:
    """Borra la carga.

    🔴 EL `.eq("id", ...)` VA EN EL DELETE, no solo en la lectura previa, y desde L9 es la ÚNICA
    guarda que tiene esta query: sin él, el DELETE alcanza a TODA la tabla. Antes había además un
    `.eq("empresa_id")` que limitaba el daño de un descuido a una sociedad; ya no está."""
    return bool(supabase_admin.table(_T).delete().eq("id", hora_id).execute().data)
