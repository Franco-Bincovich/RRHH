"""
El enriquecido de una fila de `capacitaciones`: `empresa_nombre` resuelto a nombre.

Molde: `_asignacion_row.py` (y antes `_ausencia_row.py`) — la lectura y su traducción a schema
viven en un solo lugar para que no puedan divergir entre dos repos. Vive aparte porque
`capacitacion_repo.py` estaba en 98/100 y las tres columnas nuevas de la migración 116
(`entidad_capacitadora`, `modalidad`, `tipo`) no entraban en el `save()` sin pasarlo.

🔴 El lookup es BATCH (un `IN` por lote de empresas), nunca uno por fila.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.capacitacion import CapacitacionResponse


def _build(rows: List[dict]) -> List[CapacitacionResponse]:
    """Enriquece filas con empresa_nombre."""
    if not rows:
        return []
    emp_map = {
        e["id"]: e["nombre"]
        for e in supabase_admin.table("empresas").select("id, nombre")
        .in_("id", list({r["empresa_id"] for r in rows})).execute().data or []
    }
    return [
        CapacitacionResponse.model_validate({**r, "empresa_nombre": emp_map.get(r["empresa_id"])})
        for r in rows
    ]
