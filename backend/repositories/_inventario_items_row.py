"""
El enriquecido de una fila de ítem de inventario: empresa y empleado resueltos a nombre.

Molde: `_ausencia_row.py` y `_empleado_row.py` — la forma de la lectura y su traducción a schema
viven en un solo lugar para que no puedan divergir entre los dos métodos que la usan. Vive
aparte porque `inventario_items_repo.py` estaba en 98 contra un límite de 100 y el filtro por
área no entraba.

El movimiento fue PURO: los tres lookups, su orden y el dict final son idénticos a los que
estaban embebidos en `inventario_items_repo.py`.

🔴 `asignado_a` NO sale de una columna del ítem: se deriva de la asignación ACTIVA
(`fecha_devolucion IS NULL`). Un ítem sin asignación activa queda con `asignado_a = None`, que
es lo correcto — no tiene tenedor hoy.

🔴 Los lookups son BATCH (un `IN` por dimensión), nunca uno por fila: con 50 ítems en pantalla,
resolver el nombre de la empresa fila por fila serían 50 consultas para 2 valores distintos.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.inventario import ItemResponse


def _build(rows: List[dict]) -> List[ItemResponse]:
    """Enriquece filas con empresa_nombre y asignado_a (empleado con asignación activa)."""
    if not rows:
        return []
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", list({r["empresa_id"] for r in rows})).execute().data or [])
    }
    item_ids = [r["id"] for r in rows]
    asig_data = (supabase_admin.table("inventario_asignaciones")
                 .select("item_id, empleado_id").in_("item_id", item_ids)
                 .is_("fecha_devolucion", "null").execute().data or [])
    emp_ids = list({a["empleado_id"] for a in asig_data})
    emp_map: dict = {}
    if emp_ids:
        emp_map = {
            e["id"]: f"{e['nombre']} {e['apellido']}"
            for e in (supabase_admin.table("empleados").select("id, nombre, apellido")
                      .in_("id", emp_ids).execute().data or [])
        }
    asig_map = {a["item_id"]: emp_map.get(a["empleado_id"]) for a in asig_data}
    return [
        ItemResponse.model_validate({**r, "empresa_nombre": empresa_map.get(r["empresa_id"]),
                                     "asignado_a": asig_map.get(r["id"])})
        for r in rows
    ]
