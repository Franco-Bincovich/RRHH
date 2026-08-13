"""
El enriquecido de una fila de `empleado_capacitacion`: empresa, capacitación, empleado y área
resueltos a nombre.

Molde: `_ausencia_row.py` — la lectura y su traducción a schema viven en un solo lugar para que
no puedan divergir entre dos repos. Vive aparte además porque `asignacion_repo.py` estaba en
97/100 y el manejo de `empleado_id` NULL (migración 116) no entraba con su porqué escrito, que
acá es justamente lo que no se puede omitir.

🔴 Los lookups son BATCH (un `IN` por dimensión), nunca uno por fila.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.capacitacion import AsignacionResponse


def _q(table: str, cols: str, ids: list) -> list:
    """Lookup por lote de `ids`. Con la lista VACÍA no consulta: `.in_("id", [])` se renderiza
    `id=in.()` y PostgREST lo rechaza. Deja de ser hipotético desde la migración 116 — un listado
    donde NINGUNA fila tiene empleado deja la lista de empleados vacía."""
    if not ids:
        return []
    return supabase_admin.table(table).select(cols).in_("id", ids).execute().data or []


def _build(rows: List[dict]) -> List[AsignacionResponse]:
    """Enriquece filas con empresa/capacitacion/empleado/area nombre."""
    if not rows:
        return []
    emp_map = {e["id"]: e["nombre"] for e in _q("empresas", "id, nombre", list({r["empresa_id"] for r in rows}))}
    cap_map = {c["id"]: c["nombre"] for c in _q("capacitaciones", "id, nombre", list({r["capacitacion_id"] for r in rows}))}
    # 🔴 EL `if r["empleado_id"]` NO ES DEFENSIVO. `empleado_id` es NULL en toda fila de nombre
    # libre (mig 116: el Excel de formación trae 41 nombres sin DNI contra 31 colaboradores, y
    # lo que no matchea entra igual con `nombre_libre`). El SDK renderiza el `.in_()` haciendo
    # `str()` de cada valor, así que un None viaja como `id=in.(None,<uuid>,…)` y PostgREST
    # responde 400 al castear "None" a uuid: se cae el listado ENTERO, no la fila sin empleado.
    emp_data = _q("empleados", "id, nombre, apellido, area_id", list({r["empleado_id"] for r in rows if r["empleado_id"]}))
    emp_info = {e["id"]: {"nombre": f"{e['nombre']} {e['apellido']}", "area_id": e.get("area_id")} for e in emp_data}
    area_ids = list({e["area_id"] for e in emp_data if e.get("area_id")})
    area_map = {a["id"]: a["nombre"] for a in _q("areas", "id, nombre", area_ids)}
    result = []
    for r in rows:
        emp = emp_info.get(r["empleado_id"]) or {}
        aid = emp.get("area_id")
        result.append(AsignacionResponse.model_validate({**r, "empresa_nombre": emp_map.get(r["empresa_id"]), "capacitacion_nombre": cap_map.get(r["capacitacion_id"]), "empleado_nombre": emp.get("nombre"), "area_id": aid, "area_nombre": area_map.get(aid) if aid else None}))
    return result
