"""
Helper del export de ausencias (extraído para mantener el service ≤150 líneas).

- construir_filas_export: proyecta las ausencias a las columnas legibles del export
  (sin los UUIDs crudos), con fechas dd/mm/aaaa y justificada Sí/No. Los headers del
  Excel son las keys de cada dict (el motor genérico las capitaliza); por eso las keys
  YA son el header legible. Mismo molde que _vacaciones_export.construir_filas_export.
"""

from typing import List

from schemas.ausencias import AusenciaResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[AusenciaResponse]) -> List[dict]:
    """Proyecta las ausencias a las columnas legibles del export (sin UUIDs crudos)."""
    return [
        {
            "Empresa": a.empresa_nombre,
            "Colaborador": a.empleado_nombre,
            "Área": a.area_nombre,
            "Tipo": a.tipo_nombre,
            "Fecha desde": _fecha(a.fecha_desde),
            "Fecha hasta": _fecha(a.fecha_hasta),
            "Días": a.dias,
            "Justificada": "Sí" if a.justificada else "No",
            "Motivo": a.motivo,
            "Creada": _fecha(a.created_at),
        }
        for a in items
    ]
