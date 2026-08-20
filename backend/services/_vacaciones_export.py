"""
Helper del export de vacaciones: proyecta las solicitudes a columnas legibles (sin
UUIDs crudos), con fechas dd/mm/aaaa y cancelada Sí/No. Los headers del Excel son las
keys de cada dict (el motor genérico las capitaliza); por eso las keys YA son el
header legible.

El resolver de empleado_ids (ownership∩área∩empleado) se movió a
services/_ownership_filter.py para que lo compartan todos los módulos.
"""
from typing import List

from schemas.vacaciones import SolicitudVacacionesResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[SolicitudVacacionesResponse]) -> List[dict]:
    """Proyecta las solicitudes a las columnas legibles del export (sin UUIDs crudos)."""
    return [
        {
            "Empresa": s.empresa_nombre,
            "Colaborador": s.empleado_nombre,
            "Área": s.area_nombre,
            "Fecha desde": _fecha(s.fecha_desde),
            "Fecha hasta": _fecha(s.fecha_hasta),
            "Días": s.dias,
            "Tipo": s.tipo,
            "Comentario": s.comentario,
            "Estado": s.estado,
            "Cancelada": "Sí" if s.cancelada else "No",
            "Creada": _fecha(s.created_at),
        }
        for s in items
    ]
