"""
Cómo se LEE una plantilla de evaluación: los mappers de fila y el enriquecimiento por lotes.

Aislado por el mismo motivo que `_ev_instancias_row.py`: el repo estaba en 129 líneas contra el
límite de 100. Acá quedan las traducciones fila→schema; en el repo, las queries.

🔑 `enrich` hace UN lookup por dimensión (empresas, áreas) para TODAS las filas, no uno por fila.
El nombre de área solo se busca si alguna plantilla tiene `area_id`: sin plantillas por área, la
segunda query no se emite.
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from schemas.evaluaciones import CriterioResponse, PlantillaResponse


def crit(r: dict) -> CriterioResponse:
    return CriterioResponse(
        id=r["id"], plantilla_id=r["plantilla_id"], empresa_id=r["empresa_id"],
        nombre=r["nombre"], descripcion=r.get("descripcion"),
        peso=float(r.get("peso", 1)), orden=r.get("orden", 1),
    )


def plantilla(r: dict, criterios: Optional[List[dict]] = None) -> PlantillaResponse:
    crits = [crit(c) for c in (criterios or r.get("ev_criterios") or [])]
    return PlantillaResponse(
        id=r["id"], empresa_id=r["empresa_id"],
        empresa_nombre=r.get("_empresa_nombre"),
        nombre=r["nombre"], descripcion=r.get("descripcion"),
        tipo_escala=r["tipo_escala"], escala_min=r.get("escala_min"),
        escala_max=r.get("escala_max"),
        opciones_cualitativas=r.get("opciones_cualitativas"),
        activa=r.get("activa", True),
        area_id=r.get("area_id"), area_nombre=r.get("_area_nombre"),
        criterios=sorted(crits, key=lambda c: c.orden),
        created_at=r.get("created_at"),
    )


def enrich(rows: List[dict]) -> List[PlantillaResponse]:
    if not rows:
        return []
    emp_ids = list({r["empresa_id"] for r in rows})
    area_ids = list({r["area_id"] for r in rows if r.get("area_id")})
    emp_map = {e["id"]: e["nombre"] for e in
               supabase_admin.table("empresas").select("id,nombre").in_("id", emp_ids).execute().data or []}
    area_map = {}
    if area_ids:
        area_map = {a["id"]: a["nombre"] for a in
                    supabase_admin.table("areas").select("id,nombre").in_("id", area_ids).execute().data or []}
    result = []
    for r in rows:
        r["_empresa_nombre"] = emp_map.get(r["empresa_id"])
        r["_area_nombre"] = area_map.get(r.get("area_id", ""))
        result.append(plantilla(r))
    return result
