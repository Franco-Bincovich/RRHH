"""
Mapper de `inventario_asignaciones`: fila cruda → AsignacionResponse, con los derivados de join
resueltos por LOTE.

SALIÓ DE `inventario_asignaciones_repo.py`, que estaba en 100/100 cuando le tocaba sumar la
paginación. Es el mismo corte que ya tienen `_empleado_row.py`, `_nomina_row.py` y `_hora_row.py`:
el mapper crece con cada columna que se quiere mostrar, el repo crece con cada filtro, y juntos no
entran.

🔴 TRES LOOKUPS POR LOTE, NO TRES POR FILA. `empresas`, `inventario_items` y `empleados` se
consultan una vez cada uno con el set de ids de la página. Al paginar esto MEJORA solo: los sets
pasan de tener los ids de la tabla entera a tener los de 20 filas, que es justo el problema de
URLs largas que el diagnóstico de escala midió en 51 KB para este módulo.

⚠️ Los cinco campos que agrega —`empresa_nombre`, `item_nombre`, `item_tipo`,
`item_numero_serie`, `empleado_nombre`— son DERIVADOS DE JOIN: no entran en ningún diff de
auditoría (ver la regla en CLAUDE.md, "un diff nunca registra campos derivados de joins").
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.inventario import AsignacionResponse


def build(rows: List[dict]) -> List[AsignacionResponse]:
    """Enriquece filas con empresa_nombre, campos del ítem y empleado_nombre.

    Args:
        rows: Filas crudas de `inventario_asignaciones`.

    Returns:
        Lista de AsignacionResponse. `[]` con la lista vacía, y ahí NO dispara ninguna query.
    """
    if not rows:
        return []
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", list({r["empresa_id"] for r in rows})).execute().data or [])
    }
    item_data = (supabase_admin.table("inventario_items")
                 .select("id, nombre, tipo, numero_serie")
                 .in_("id", list({r["item_id"] for r in rows})).execute().data or [])
    item_map = {i["id"]: i for i in item_data}

    emp_data = (supabase_admin.table("empleados").select("id, nombre, apellido")
                .in_("id", list({r["empleado_id"] for r in rows})).execute().data or [])
    emp_map = {e["id"]: f"{e['nombre']} {e['apellido']}" for e in emp_data}

    return [
        AsignacionResponse.model_validate({
            **r,
            "empresa_nombre":    empresa_map.get(r["empresa_id"]),
            "item_nombre":       item_map.get(r["item_id"], {}).get("nombre"),
            "item_tipo":         item_map.get(r["item_id"], {}).get("tipo"),
            "item_numero_serie": item_map.get(r["item_id"], {}).get("numero_serie"),
            "empleado_nombre":   emp_map.get(r["empleado_id"]),
        })
        for r in rows
    ]
