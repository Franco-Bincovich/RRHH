"""
Reportes del dominio vacaciones/ausencias:
- R11 saldos_vacaciones: por empleado, asignados − tomados = saldo (cancelada=false no resta).
- R9  listado_vac_aus: listado plano de vacaciones + ausencias del período (reporte "crudo").
El área vive en empleados (las solicitudes no la tienen) → filtro de área por JOIN inner por
empleado (empleados!inner(area_id)), igual que rotacion/onboarding. Con tablas vacías las listas
salen vacías y los totales en 0 (empty state coherente, no error).
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid, periodo_str, rango_mes


def _fecha(s) -> str:
    """ISO 'YYYY-MM-DD' → 'DD/MM/YYYY'; '' si es None/vacío. Supabase devuelve fechas como string."""
    p = str(s)[:10].split("-") if s else []
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else (str(s) if s else "")


def _nombre(emp: dict) -> str:
    return f"{emp.get('apellido', '')}, {emp.get('nombre', '')}".strip(", ").strip()


def _area(emp: dict) -> str:
    return (emp.get("areas") or {}).get("nombre") or "Sin área"


def generate_saldos_vacaciones(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                               area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Saldo de vacaciones por empleado activo: asignados − tomados (solo cancelada=false cuenta).
    Filtra por empresa_id y/o area_id (empleados.area_id directo). Empleado sin asignados (null) →
    asignados 0 con marca 'Sin asignar'."""
    ini, fin = rango_mes(mes, anio)
    eid, aid = _eid(empresa_id), _eid(area_id)
    db = supabase_admin

    emp_q = (db.table("empleados")
             .select("id, nombre, apellido, dias_vacaciones_asignados, areas(nombre)")
             .eq("estado", "activo"))
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    if aid:
        emp_q = emp_q.eq("area_id", aid)
    empleados = emp_q.execute().data or []

    vac_q = (db.table("solicitudes_vacaciones").select("empleado_id, dias")
             .eq("cancelada", False).gte("fecha_desde", ini).lte("fecha_desde", fin))
    if eid:
        vac_q = vac_q.eq("empresa_id", eid)
    tomados: dict[str, int] = {}
    for v in (vac_q.execute().data or []):
        tomados[v.get("empleado_id")] = tomados.get(v.get("empleado_id"), 0) + int(v.get("dias") or 0)

    filas = []
    for emp in empleados:
        crudo = emp.get("dias_vacaciones_asignados")
        sin_asignar = crudo is None
        asignados = int(crudo or 0)
        tom = tomados.get(emp["id"], 0)
        filas.append({
            "empleado": _nombre(emp),
            "area": _area(emp),
            "asignados": "Sin asignar" if sin_asignar else asignados,
            "tomados": tom,
            "saldo": asignados - tom,
        })

    return {
        "titulo": f"Saldos de vacaciones — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_empleados": len(filas),
        "saldos": sorted(filas, key=lambda x: x["empleado"]),
    }


def generate_listado_vac_aus(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                             area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Listado plano de vacaciones y ausencias del período (dos secciones). Filtra por empresa_id
    y/o area_id (join inner por empleado)."""
    ini, fin = rango_mes(mes, anio)
    eid, aid = _eid(empresa_id), _eid(area_id)
    db = supabase_admin
    emb = "empleados!inner(nombre, apellido, areas(nombre))" if aid else "empleados(nombre, apellido, areas(nombre))"

    vac_q = (db.table("solicitudes_vacaciones")
             .select(f"fecha_desde, fecha_hasta, dias, tipo, cancelada, {emb}")
             .gte("fecha_desde", ini).lte("fecha_desde", fin))
    if eid:
        vac_q = vac_q.eq("empresa_id", eid)
    if aid:
        vac_q = vac_q.eq("empleados.area_id", aid)
    vacaciones = [{
        "empleado": _nombre(r.get("empleados") or {}), "area": _area(r.get("empleados") or {}),
        "tipo": r.get("tipo") or "", "fecha_desde": _fecha(r.get("fecha_desde")),
        "fecha_hasta": _fecha(r.get("fecha_hasta")), "dias": r.get("dias") or 0,
        "cancelada": "Sí" if r.get("cancelada") else "No",
    } for r in (vac_q.execute().data or [])]

    aus_q = (db.table("solicitudes_ausencia")
             .select(f"fecha_desde, fecha_hasta, dias, justificada, motivo, tipos_ausencia(nombre), {emb}")
             .gte("fecha_desde", ini).lte("fecha_desde", fin))
    if eid:
        aus_q = aus_q.eq("empresa_id", eid)
    if aid:
        aus_q = aus_q.eq("empleados.area_id", aid)
    ausencias = [{
        "empleado": _nombre(r.get("empleados") or {}), "area": _area(r.get("empleados") or {}),
        "tipo": (r.get("tipos_ausencia") or {}).get("nombre") or "",
        "fecha_desde": _fecha(r.get("fecha_desde")), "fecha_hasta": _fecha(r.get("fecha_hasta")),
        "dias": r.get("dias") or 0, "justificada": "Sí" if r.get("justificada") else "No",
        "motivo": r.get("motivo") or "",
    } for r in (aus_q.execute().data or [])]

    return {
        "titulo": f"Vacaciones y ausencias — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_vacaciones": len(vacaciones),
        "total_ausencias": len(ausencias),
        "vacaciones": vacaciones,
        "ausencias": ausencias,
    }
