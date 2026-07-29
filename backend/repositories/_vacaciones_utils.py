"""Helpers internos del módulo de vacaciones. No importar desde fuera de repositories/."""
from datetime import date
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from schemas.vacaciones import SolicitudVacacionesResponse

# Nombre de la tabla, acá para que el repo de lectura y el de escritura lo compartan sin
# que ninguno de los dos lo redefina (mismo criterio que _empleado_row.TABLE).
TABLE = "solicitudes_vacaciones"


def aplicar_filtro_estado(q, estado: Optional[str], today: Optional[date]):
    """Traduce el estado DERIVADO al filtro SQL equivalente sobre cancelada + fecha_desde.

    Espejo exacto de services._vacaciones_utils.derive_estado:
      cancelada   → cancelada=True
      planificada → cancelada=False AND fecha_desde > hoy
      tomada      → cancelada=False AND fecha_desde <= hoy
    estado vacío/desconocido (o today None) → sin filtro (idéntico a "todos").
    """
    if estado == "cancelada":
        return q.eq("cancelada", True)
    if estado in ("planificada", "tomada") and today is not None:
        q = q.eq("cancelada", False)
        return q.gt("fecha_desde", str(today)) if estado == "planificada" else q.lte("fecha_desde", str(today))
    return q


def enriquecer(rows: List[dict]) -> List[dict]:
    """Agrega empresa_nombre, empleado_nombre, area_id y area_nombre a cada fila (batch, sin N+1).

    Compartido por solicitudes_vacaciones y vacaciones_pendientes: las dos cuelgan de un empleado
    y resuelven exactamente los mismos derivados. Una sola implementación para que las dos
    pantallas no puedan mostrar el área de formas distintas.
    """
    if not rows:
        return []

    empresa_ids = list({r["empresa_id"] for r in rows})
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre").in_("id", empresa_ids).execute().data or [])
    }

    emp_ids = list({r["empleado_id"] for r in rows})
    emp_data = supabase_admin.table("empleados").select("id, nombre, apellido, area_id").in_("id", emp_ids).execute().data or []
    emp_map = {e["id"]: {"nombre": f"{e['nombre']} {e['apellido']}", "area_id": e.get("area_id")} for e in emp_data}

    area_ids = list({e["area_id"] for e in emp_data if e.get("area_id")})
    area_map: dict = {}
    if area_ids:
        area_map = {
            a["id"]: a["nombre"]
            for a in (supabase_admin.table("areas").select("id, nombre").in_("id", area_ids).execute().data or [])
        }

    result = []
    for r in rows:
        emp = emp_map.get(r["empleado_id"]) or {}
        aid = emp.get("area_id")
        result.append({
            **r,
            "empresa_nombre": empresa_map.get(r["empresa_id"]),
            "empleado_nombre": emp.get("nombre"),
            "area_id": aid,
            "area_nombre": area_map.get(aid) if aid else None,
        })
    return result


def build_responses(rows: List[dict]) -> List[SolicitudVacacionesResponse]:
    """Filas de solicitudes_vacaciones enriquecidas → responses. `estado` lo deriva el service."""
    return [SolicitudVacacionesResponse.model_validate({**r, "estado": ""}) for r in enriquecer(rows)]
