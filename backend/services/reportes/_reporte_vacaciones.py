"""
R9 listado_vac_aus: listado plano de vacaciones + ausencias del período (reporte "crudo").

El área vive en empleados (las solicitudes no la tienen) → filtro de área por JOIN inner por
empleado (empleados!inner(area_id)), igual que rotacion/onboarding. Con tablas vacías las listas
salen vacías y los totales en 0 (empty state coherente, no error).

⚠️ R11 (saldos_vacaciones) VIVÍA ACÁ y se mudó a `_reporte_saldos.py`. No fue por líneas: pasó
a calcularse con el mismo núcleo que la pantalla de vacaciones y dejó de parecerse a esto. Lo
único que compartían de verdad —`_nombre` y `_area`— está ahora en `_common.py`. Si volvés a
necesitar un "saldo" acá, importalo de `_reporte_saldos`: una segunda definición de saldo es
exactamente el bug que la unificación vino a cerrar (RRHH veía un número en la ficha y otro en
el reporte, y ninguno de los dos daba error).
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import EMBED_AREA_DE_EMPLEADO as _AREA
from services.reportes._common import _area, _eid, _nombre, periodo_str, rango_mes


def _fecha(s) -> str:
    """ISO 'YYYY-MM-DD' → 'DD/MM/YYYY'; '' si es None/vacío. Supabase devuelve fechas como string."""
    p = str(s)[:10].split("-") if s else []
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else (str(s) if s else "")


def generate_listado_vac_aus(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                             area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Listado plano de vacaciones y ausencias del período (dos secciones). Filtra por empresa_id
    y/o area_id (join inner por empleado)."""
    ini, fin = rango_mes(mes, anio)
    eid, aid = _eid(empresa_id), _eid(area_id)
    db = supabase_admin
    emb = (f"empleados!inner(nombre, apellido, {_AREA})" if aid
           else f"empleados(nombre, apellido, {_AREA})")

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
