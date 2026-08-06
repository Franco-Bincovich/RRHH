"""
Resolución de "qué ÍTEMS de inventario caen bajo un filtro de área".

Vive aparte y no en `_scope_filtros.py` —donde están sus hermanas— porque aquel está en 93
contra su límite y una función documentada como estas no entra. Reusa `empleados_de_area` de
allá: el primer salto es el mismo, lo que cambia es a dónde se llega después.

🔴 QUÉ SIGNIFICA EL FILTRO — decisión de producto, no detalle de implementación.
`inventario_items` NO tiene columna de área: un ítem no pertenece a un área, está asignado a un
empleado y ese empleado sí tiene área. Así que "ítems del área X" solo puede querer decir
**"los que un empleado del área tiene asignados HOY"**, y eso es lo que hace esta función.

🔴 POR QUÉ SOLO LA ASIGNACIÓN ACTIVA (`fecha_devolucion IS NULL`), y no el histórico.
Es la diferencia con `inventario_asignaciones_repo.find_all`, que hereda el recorte de su
listado: aquel YA muestra solo asignaciones sin devolver, así que no tiene que decidir nada.
El catálogo de ítems no: muestra TODO, incluidos los `disponible` y los `baja`. Sin este
recorte, un ítem devuelto hace dos años seguiría apareciendo bajo el área de quien lo usó —y
apareciendo además como "disponible"—, que es exactamente lo contrario de lo que alguien busca
cuando filtra un catálogo por área.

⚠️ CASO BORDE, ES LA DEFINICIÓN Y NO UN BUG: un ítem SIN asignación activa no aparece bajo
ninguna área. No hay área que pueda reclamarlo. Vale para los `disponible` (nadie los tiene),
los `en_reparacion` y los `baja`. Mismo criterio y mismas palabras que
`_scope_filtros.proyecto_ids_con_area` para un proyecto sin nadie asignado.

Dos queries batch fijas, ambas con `.in_()`: no escala con la cantidad de ítems del catálogo.
"""
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._scope_filtros import empleados_de_area


def items_de_area(area_id: UUID, empresa_id: UUID | None = None) -> list[str]:
    """Ids de los ítems que hoy tiene asignados algún empleado del área.

    Acota por empresa igual que `empleados_de_area`: un ítem y su tenedor son de la misma
    empresa (la FK compuesta de `inventario_asignaciones` lo garantiza), así que el `.eq` extra
    es una barandilla barata y no puede vaciar el conjunto.
    """
    empleados = empleados_de_area(area_id, empresa_id)
    if not empleados:
        return []
    filas = (supabase_admin.table("inventario_asignaciones").select("item_id")
             .in_("empleado_id", empleados)
             .is_("fecha_devolucion", "null").execute().data or [])
    return list({f["item_id"] for f in filas})
