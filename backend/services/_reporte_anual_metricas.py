"""
Las mediciones del informe anual que NO entran en `_count_rango`.

Separadas de `reporte_anual.py` porque ese archivo había llegado a 154 líneas contra el límite de
150. El corte es "medir" (acá) vs. "armar el informe" (allá): el generador queda con el rango del
año, las llamadas a estas tres funciones y la estructura de salida, que es lo que se lee cuando
alguien pregunta qué trae el informe.

⚠️ `_count_rango` NO se movió, a propósito. Es el único `select` del módulo que un barrido
estático no puede resolver (recibe la tabla por parámetro) y por eso tiene una excepción declarada
en `tests/test_selects_repos.py` apuntando a `services/reporte_anual.py`. Mover la función habría
dejado esa excepción apuntando al vacío — que es exactamente lo que ese test detecta como ruido.
Los selects de ESTE archivo son todos literales y el barrido los valida solo, sin declarar nada.
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin


def movimientos(eid: Optional[str], ini: str, fin: str, ini_ts: str, fin_ts: str) -> tuple[int, int]:
    """Ingresos y egresos del año.

    Los ingresos salen de `empleados.fecha_ingreso` (una `date`) y los egresos del `created_at`
    de la instancia de offboarding (un `timestamp`): por eso cada uno usa su propio par de bordes.
    """
    ing_q = supabase_admin.table("empleados").select("id", count="exact").gte("fecha_ingreso", ini).lte("fecha_ingreso", fin)
    if eid:
        ing_q = ing_q.eq("empresa_id", eid)
    egr_q = supabase_admin.table("offboarding_instancias").select("id", count="exact").gte("created_at", ini_ts).lte("created_at", fin_ts)
    if eid:
        egr_q = egr_q.eq("empresa_id", eid)
    return (ing_q.execute().count or 0, egr_q.execute().count or 0)


def headcount_por_area(eid: Optional[str]) -> tuple[int, List[dict]]:
    """Total de activos y su reparto por área, de mayor a menor.

    Es una FOTO de HOY, no del año: cuenta empleados en estado activo al momento de generar el
    informe. Un empleado sin área, o con un área inactiva, suma al total y no aparece en el
    reparto — el total no es la suma de la lista, y está bien que no lo sea.
    """
    areas_q = supabase_admin.table("areas").select("id, nombre").eq("activo", True)
    if eid:
        areas_q = areas_q.eq("empresa_id", eid)
    area_map: dict[str, str] = {a["id"]: a["nombre"] for a in (areas_q.execute().data or [])}

    emp_q = supabase_admin.table("empleados").select("area_id").eq("estado", "activo")
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    emp_rows = emp_q.execute().data or []

    conteo: dict[str, int] = {}
    for r in emp_rows:
        aid = r.get("area_id")
        if aid and aid in area_map:
            conteo[aid] = conteo.get(aid, 0) + 1
    lista = sorted([{"area": area_map[k], "total": v} for k, v in conteo.items()],
                   key=lambda x: x["total"], reverse=True)
    return (len(emp_rows), lista)


def actividad(eid: Optional[str], ini: str, fin: str, ini_ts: str, fin_ts: str) -> dict:
    """Vacaciones, capacitaciones, objetivos y evaluaciones del año.

    Solo `tipo="vacaciones"` y sin canceladas: es la misma definición que usa el reporte de saldos
    — una licencia por enfermedad no descuenta días de vacaciones.

    `ev_instancias.fecha_evaluacion` es la fecha en que se finalizó y es NULL mientras no se
    finalice, así que las instancias abiertas no se cuentan en ningún año.
    """
    vac_q = supabase_admin.table("solicitudes_vacaciones").select("dias").eq("tipo", "vacaciones").eq("cancelada", False).gte("fecha_desde", ini).lte("fecha_desde", fin)
    if eid:
        vac_q = vac_q.eq("empresa_id", eid)
    vac_data = vac_q.execute().data or []

    cap_q = supabase_admin.table("empleado_capacitacion").select("id", count="exact").eq("estado", "completado").gte("fecha_completado", ini).lte("fecha_completado", fin)
    if eid:
        cap_q = cap_q.eq("empresa_id", eid)

    # 🔴 SOLO RAÍCES: los subobjetivos son filas de la misma tabla desde la 095. Sin el filtro,
    # "objetivos cumplidos en el año" pasaría a contar también las subtareas y el número del
    # reporte anual dejaría de ser comparable con el del año pasado.
    obj_q = supabase_admin.table("objetivos").select("id", count="exact").eq("estado", "terminado").is_("parent_id", "null").gte("updated_at", ini_ts).lte("updated_at", fin_ts)
    if eid:
        obj_q = obj_q.eq("empresa_id", eid)

    ev_q = supabase_admin.table("ev_instancias").select("id", count="exact").eq("estado", "finalizada").gte("fecha_evaluacion", ini).lte("fecha_evaluacion", fin)
    if eid:
        ev_q = ev_q.eq("empresa_id", eid)

    return {
        "solicitudes_vacaciones": len(vac_data),
        "dias_vacaciones": sum(int(r.get("dias") or 0) for r in vac_data),
        "cap_completadas": cap_q.execute().count or 0,
        "obj_terminados": obj_q.execute().count or 0,
        "ev_finalizadas": ev_q.execute().count or 0,
    }
