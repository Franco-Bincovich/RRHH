"""
Cómo se LEE una instancia de evaluación: el mapper de fila y el enriquecimiento por lotes.

Aislado por el mismo motivo que `_empleado_row.py` y `_nomina_row.py`: `ev_instancias_repo`
estaba en 146 líneas contra el límite de 100. Acá quedan las tres traducciones fila→schema; en
el repo, las queries.

🔑 `enrich_rows` hace UN lookup por dimensión (empleados, evaluadores, ciclos, empresas) para
TODAS las filas, no uno por fila: es el patrón anti-N+1 que ya se aplicó en sucesión y en el
historial de importaciones. Con 300 instancias son 4 requests, no 1200.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.evaluaciones import InstanciaResponse, ResultadoResponse

_TC = "ev_criterios"


def build_inst(r: dict) -> InstanciaResponse:
    emp = r.get("_emp") or {}
    evaluador = r.get("_evaluador") or {}
    ciclo = r.get("_ciclo") or {}
    return InstanciaResponse(
        id=r["id"], empresa_id=r["empresa_id"],
        empresa_nombre=r.get("_empresa_nombre"),
        ciclo_id=r["ciclo_id"], ciclo_nombre=ciclo.get("nombre") or r.get("_ciclo_nombre"),
        empleado_id=r["empleado_id"],
        empleado_nombre=f"{emp.get('nombre','')} {emp.get('apellido','')}".strip() or r.get("_emp_nombre"),
        empleado_area=emp.get("_area") or r.get("_emp_area"),
        evaluador_id=r.get("evaluador_id"),
        evaluador_nombre=f"{evaluador.get('nombre','')} {evaluador.get('apellido','')}".strip() or None,
        estado=r["estado"],
        puntaje_global=r.get("puntaje_global"),
        fecha_evaluacion=r.get("fecha_evaluacion"),
    )


def enrich_rows(rows: List[dict]) -> List[InstanciaResponse]:
    if not rows:
        return []
    emp_ids = list({r["empleado_id"] for r in rows})
    eval_ids = list({r["evaluador_id"] for r in rows if r.get("evaluador_id")})
    ciclo_ids = list({r["ciclo_id"] for r in rows})
    emp_map = {e["id"]: e for e in supabase_admin.table("empleados").select(
        "id,nombre,apellido,areas!empleados_area_id_fkey(nombre)").in_("id", emp_ids).execute().data or []}
    eval_map = {e["id"]: e for e in supabase_admin.table("empleados").select(
        "id,nombre,apellido").in_("id", eval_ids).execute().data or []} if eval_ids else {}
    ciclo_map = {c["id"]: c for c in supabase_admin.table("ev_ciclos").select(
        "id,nombre,plantilla_id").in_("id", ciclo_ids).execute().data or []}
    emp_empresa_map = {e["id"]: e.get("empresa_nombre") for e in supabase_admin.table("empresas").select(
        "id,nombre").in_("id", list({r["empresa_id"] for r in rows})).execute().data or []}
    result = []
    for r in rows:
        emp = emp_map.get(r["empleado_id"], {})
        area = emp.get("areas") or {}
        r["_emp"] = {**emp, "_area": area.get("nombre")}
        r["_evaluador"] = eval_map.get(r.get("evaluador_id", ""), {})
        r["_ciclo"] = ciclo_map.get(r["ciclo_id"], {})
        r["_empresa_nombre"] = emp_empresa_map.get(r["empresa_id"])
        result.append(build_inst(r))
    return result


def resultados(raw: List[dict]) -> List[ResultadoResponse]:
    """Traduce las filas de `ev_resultados` (con el criterio embebido) y las ordena por criterio.

    El orden lo pone el criterio, no la fila: `ev_resultados` no tiene columna de orden, así que
    ordenar en la query pediría un `order` sobre la tabla embebida. Con los ~15 criterios de una
    plantilla, ordenar acá es correcto y no depende de haber traído todo (siempre se traen todos
    los resultados de UNA instancia).
    """
    return sorted([
        ResultadoResponse(
            id=r["id"], criterio_id=r["criterio_id"],
            criterio_nombre=(r.get(_TC) or {}).get("nombre", ""),
            criterio_peso=float((r.get(_TC) or {}).get("peso", 1)),
            criterio_orden=(r.get(_TC) or {}).get("orden", 1),
            puntaje=r.get("puntaje"), valor=r.get("valor"), comentario=r.get("comentario"),
        ) for r in raw
    ], key=lambda x: x.criterio_orden)
