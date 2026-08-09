"""
La forma de la lectura de una vacante: el SELECT con joins y su traducción a schema.

Extraído de `vacante_repo.py`, que estaba en 98 contra un límite de 100 y no admitía el lookup
por código que pide el CV screening. Molde: `_empleado_row.py`, `_inventario_items_row.py` —
la forma de la lectura y su mapper viven en un solo lugar para que no puedan divergir entre los
CUATRO métodos que los usan (`find_all`, `find_by_ids`, `find_by_id` y, por vía de `find_by_id`,
el retorno de `save`/`update`/`update_estado`).

El movimiento fue VERBATIM: el spec, el mapper, su comentario y los nombres son idénticos a los
que estaban embebidos en `vacante_repo.py`. `_V` (la tabla) NO se movió: la usan también el
insert, el update y el delete, así que es del repo y no de la forma de la lectura.

⚠️ Vive en `repositories/`, así que su límite es 100 líneas, como cualquier repositorio. No
hereda un límite más alto por ser un satélite.

🔴 El área se embebe por el NOMBRE de la constraint (`areas!vacantes_area_id_fkey`) y no por
`areas(nombre)` a secas: entre `vacantes` y `areas` hay más de una relación posible, y un embed
ambiguo lo rechaza PostgREST con 300 PGRST201 — el reporte sale en blanco y el único síntoma es
ese. `tests/test_selects_repos.py` valida este spec contra `db/schema.sql`, y resuelve la
constante a través de este import (el mismo camino que ya usa `_empleado_row`).
"""
from schemas.vacante import VacanteResponse

_JOIN = "*, areas!vacantes_area_id_fkey(nombre), empresas(nombre)"


def _vrow(r: dict) -> VacanteResponse:
    # requisitos es TEXT plano (migración 070); fluye tal cual, sin parseo de array.
    area = r.get("areas")
    empresa = r.get("empresas")
    data = {k: v for k, v in r.items() if k not in ("areas", "empresas")}
    data["area_id"] = str(data["area_id"])
    data["area_nombre"] = area["nombre"] if isinstance(area, dict) else None
    if data.get("empresa_id"):
        data["empresa_id"] = str(data["empresa_id"])
    data["empresa_nombre"] = empresa["nombre"] if isinstance(empresa, dict) else None
    return VacanteResponse.model_validate(data)
