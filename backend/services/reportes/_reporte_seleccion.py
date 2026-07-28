"""
Reportes de selección/ingreso: pipeline de vacantes activas y progreso de onboarding.
Movidos verbatim desde reporte_generators.py.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid


def generate_vacantes(empresa_id: Optional[UUID] = None,
                      area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales del pipeline de vacantes activas, agrupados por estado y área.
    Filtra por empresa_id y/o area_id (vacantes.area_id, directo).
    """
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    q = supabase_admin.table("vacantes").select("id, titulo, estado, areas(nombre)").neq("estado", "cerrada").order("created_at", desc=True)
    if eid:
        q = q.eq("empresa_id", eid)
    if aid:
        q = q.eq("area_id", aid)
    rows = q.execute().data or []

    por_estado: dict[str, int] = {}
    por_area: dict[str, int] = {}
    detalle = []
    for v in rows:
        estado = v.get("estado", "desconocido")
        area = (v.get("areas") or {}).get("nombre") or "Sin área"
        por_estado[estado] = por_estado.get(estado, 0) + 1
        por_area[area] = por_area.get(area, 0) + 1
        detalle.append({"titulo": v.get("titulo", ""), "estado": estado, "area": area})

    return {
        "titulo": "Pipeline de Vacantes",
        "total_activas": len(rows),
        "por_estado": por_estado,
        "por_area": por_area,
        "detalle": detalle,
    }


def _progreso(tareas: list) -> int:
    """% de tareas completadas sobre el total. Misma fórmula que onboarding_repo._inst_row —
    si un día cambia el criterio de "completado", tienen que cambiar los dos."""
    total = len(tareas)
    done = sum(1 for t in tareas if t.get("estado") == "completado")
    return round(done / total * 100) if total else 0


def generate_onboarding(empresa_id: Optional[UUID] = None,
                        area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales del progreso de onboardings activos.
    Filtra por empresa_id; y por area_id vía join inner por empleado (onboarding_instancias
    no tiene area_id).
    """
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    # onboarding_instancias tiene DOS FKs a empleados → nombrar la FK o PostgREST da PGRST201.
    fk = "empleados!onboarding_instancias_empleado_id_fkey"
    emb = f"{fk}!inner(nombre, apellido)" if aid else f"{fk}(nombre, apellido)"
    # El progreso NO es una columna: se deriva de las tareas completadas sobre el total, igual
    # que en onboarding_repo._inst_row. Se trae la lista de estados embebida (una sola query,
    # sin N+1) nombrando la FK, que acá también es doble.
    q = (supabase_admin.table("onboarding_instancias")
         .select(f"id, created_at, onboarding_progreso!onb_prog_instancia_emp_fkey(estado), {emb}")
         .eq("estado", "en_progreso").order("created_at", desc=True))
    if eid:
        q = q.eq("empresa_id", eid)
    if aid:
        q = q.eq("empleados.area_id", aid)
    rows = q.execute().data or []

    detalle = []
    total_progreso = 0
    for row in rows:
        emp = row.get("empleados") or {}
        nombre = f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip()
        progreso = _progreso(row.get("onboarding_progreso") or [])
        total_progreso += progreso
        detalle.append({
            "empleado": nombre,
            "progreso": progreso,
            "fecha_inicio": str(row.get("created_at", ""))[:10],
        })

    return {
        "titulo": "Progreso de Onboarding",
        "total_activos": len(rows),
        "progreso_promedio": round(total_progreso / len(rows)) if rows else 0,
        "detalle": detalle,
    }
