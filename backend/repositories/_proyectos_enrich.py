"""
Enriquecimiento de proyectos: nombre de la empresa dueña y resumen de costeo (costo
acumulado, presupuesto restante, % consumido). Todo con lookups batch — una query por
dimensión, sin N+1 (mismo patrón que _evaluacion_lotes_enrich / audit_repo). Aislado de
proyectos_repo para no pasar su límite de líneas. Un helper más a portar a asyncpg junto
con su repo.
"""
from integrations.supabase_client import supabase_admin
from schemas.proyectos import CosteoResumen, ProyectoResponse


def batch_costos(proyecto_ids: list[str]) -> dict[str, float]:
    """SUM(horas × valor_hora_snapshot) por proyecto en una sola query.
    {} con la lista vacía — ahí no dispara ninguna query."""
    if not proyecto_ids:
        return {}
    rows = (supabase_admin.table("horas_proyecto")
            .select("proyecto_id, horas, valor_hora_snapshot")
            .in_("proyecto_id", proyecto_ids).execute().data or [])
    costos: dict[str, float] = {}
    for r in rows:
        pid = r["proyecto_id"]
        costos[pid] = costos.get(pid, 0.0) + float(r["horas"]) * float(r["valor_hora_snapshot"])
    return costos


def enriquecer(rows: list[dict], costo_map: dict[str, float]) -> list[ProyectoResponse]:
    """Mapea filas crudas de proyectos a ProyectoResponse con empresa_nombre y costeo.
    [] si no hay filas — ahí no dispara la query de empresas."""
    if not rows:
        return []
    emp_ids = list({r["empresa_id"] for r in rows})
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", emp_ids).execute().data or [])
    }
    result = []
    for r in rows:
        costo = round(costo_map.get(r["id"], 0.0), 2)
        ppto = float(r.get("presupuesto") or 0)
        restante = round(ppto - costo, 2)
        pct = round(costo / ppto * 100, 1) if ppto > 0 else None
        result.append(ProyectoResponse.model_validate({
            **r,
            "empresa_nombre": empresa_map.get(r["empresa_id"]),
            "costeo": CosteoResumen(
                costo_acumulado=costo,
                presupuesto_restante=restante,
                pct_consumido=pct,
            ),
        }))
    return result
