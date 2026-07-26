"""
Reportes de selección/ingreso: pipeline de vacantes activas y progreso de onboarding.
Movidos verbatim desde reporte_generators.py.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid


def generate_vacantes(empresa_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales del pipeline de vacantes activas, agrupados por estado y área.
    Filtra por empresa_id si se provee.
    """
    eid = _eid(empresa_id)
    q = supabase_admin.table("vacantes").select("id, titulo, estado, areas(nombre)").neq("estado", "cerrada").order("created_at", desc=True)
    if eid:
        q = q.eq("empresa_id", eid)
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


def generate_onboarding(empresa_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Genera datos reales del progreso de onboardings activos.
    Filtra por empresa_id si se provee.
    """
    eid = _eid(empresa_id)
    q = (supabase_admin.table("onboarding_instancias")
         .select("id, progreso, created_at, empleados(nombre, apellido)")
         .eq("estado", "en_progreso").order("created_at", desc=True))
    if eid:
        q = q.eq("empresa_id", eid)
    rows = q.execute().data or []

    detalle = []
    total_progreso = 0
    for row in rows:
        emp = row.get("empleados") or {}
        nombre = f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip()
        progreso = int(row.get("progreso") or 0)
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
