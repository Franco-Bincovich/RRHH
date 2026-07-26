"""
Enriquecimiento del historial de lotes de evaluaciones: nombre de empresa, nombre de quien
importó y conteo de evaluados. Todo con lookups batch — una query por dimensión, sin N+1
(mismo patrón que audit_repo / _vacaciones_utils). Aislado de evaluacion_repo para no pasar su
límite de líneas. Un helper más a portar a asyncpg junto con su repo.
"""
from collections import Counter
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.evaluacion_resultados import LoteResponse

_EVALUADOS = "evaluacion_evaluados"


def enriquecer_lotes(rows: List[dict]) -> List[LoteResponse]:
    """Mapea filas crudas de evaluacion_lotes a LoteResponse con los campos derivados.
    [] si no hay filas — ahí no dispara ninguna query de lookup."""
    if not rows:
        return []
    emp_ids = list({r["empresa_id"] for r in rows if r.get("empresa_id")})
    user_ids = list({r["importado_por"] for r in rows if r.get("importado_por")})
    emp_map = _nombres("empresas", emp_ids)
    user_map = _nombres_usuarios(user_ids)
    conteo = _conteo_evaluados([r["id"] for r in rows])
    return [LoteResponse.model_validate({
        **r,
        "empresa_nombre": emp_map.get(r.get("empresa_id")),
        "importado_por_nombre": user_map.get(r["importado_por"]) if r.get("importado_por") else None,
        "evaluados": conteo.get(r["id"], 0),
    }) for r in rows]


def _nombres(tabla: str, ids: list) -> dict:
    """id → nombre para una tabla con columna `nombre`. {} si no hay ids."""
    if not ids:
        return {}
    data = supabase_admin.table(tabla).select("id, nombre").in_("id", ids).execute().data or []
    return {e["id"]: e["nombre"] for e in data}


def _nombres_usuarios(ids: list) -> dict:
    """id → 'Nombre Apellido' de users. {} si no hay ids (mismo formato que audit_repo)."""
    if not ids:
        return {}
    data = supabase_admin.table("users").select("id, nombre, apellido").in_("id", ids).execute().data or []
    return {u["id"]: f"{u['nombre']} {u['apellido']}" for u in data}


def _conteo_evaluados(lote_ids: list) -> Counter:
    """lote_id → cantidad de evaluados, en una sola query (evita N+1). Counter() si no hay ids."""
    if not lote_ids:
        return Counter()
    data = supabase_admin.table(_EVALUADOS).select("lote_id").in_("lote_id", lote_ids).execute().data or []
    return Counter(r["lote_id"] for r in data)
