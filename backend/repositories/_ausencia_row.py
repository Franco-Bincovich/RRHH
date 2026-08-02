"""
El enriquecido de una fila de ausencia: empresa, empleado, área y tipo resueltos a nombre.

Molde: `_tipo_ausencia_row.py` y `_empleado_row.py` — la forma de la lectura y su traducción a
schema viven en un solo lugar para que no puedan divergir entre dos repos. Vive aparte además
porque `ausencias_repo.py` llegó a 101 contra un límite de 100 al pasar el filtro de tipo de
`.eq()` a `.in_()` (migración 088).

🔴 Los lookups son BATCH (un `IN` por dimensión), nunca uno por fila: con 20 ausencias en
pantalla, resolver el nombre del tipo fila por fila serían 20 consultas para 4 valores
distintos.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.ausencias import AusenciaResponse

def _q(table: str, cols: str, ids: list) -> list:
    return supabase_admin.table(table).select(cols).in_("id", ids).execute().data or []


def _build(rows: List[dict]) -> List[AusenciaResponse]:
    """Enriquece filas con empresa_nombre, empleado_nombre, area_nombre y tipo_nombre."""
    if not rows:
        return []
    empresa_map = {e["id"]: e["nombre"] for e in _q("empresas", "id, nombre", list({r["empresa_id"] for r in rows}))}
    emp_data = _q("empleados", "id, nombre, apellido, area_id", list({r["empleado_id"] for r in rows}))
    emp_map = {e["id"]: {"nombre": f"{e['nombre']} {e['apellido']}", "area_id": e.get("area_id")} for e in emp_data}
    area_ids = list({e["area_id"] for e in emp_data if e.get("area_id")})
    area_map = {a["id"]: a["nombre"] for a in (_q("areas", "id, nombre", area_ids) if area_ids else [])}
    tipo_map = {t["id"]: t["nombre"] for t in _q(_TA, "id, nombre", list({r["tipo_id"] for r in rows}))}
    result = []
    for r in rows:
        emp = emp_map.get(r["empleado_id"]) or {}
        aid = emp.get("area_id")
        result.append(AusenciaResponse.model_validate({
            **r,
            "empresa_nombre": empresa_map.get(r["empresa_id"]),
            "empleado_nombre": emp.get("nombre"),
            "area_id": aid,
            "area_nombre": area_map.get(aid) if aid else None,
            "tipo_nombre": tipo_map.get(r["tipo_id"]),
        }))
    return result
