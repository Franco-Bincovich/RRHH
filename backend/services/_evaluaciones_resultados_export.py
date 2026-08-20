"""
Proyección legible del listado de evaluados de un lote para export (cero UUIDs; molde
_ausencias_export). Las claves del dict YA son el header. Tipos separados por coma; sin nota → 'Sin nota'.
"""
from typing import List

from schemas.evaluacion_reportes import EvaluadoListadoItem


def construir_filas_export(items: List[EvaluadoListadoItem]) -> List[dict]:
    """Cada evaluado del listado → fila legible. Mismo contrato que _ausencias_export."""
    return [
        {
            "Evaluado": f"{i.apellido} {i.nombre}".strip(),
            "Sector": i.sector or "",
            "Superior": i.superior or "",
            "Perfil": "Líder" if i.perfil == "lider" else "General",
            "Tipos de evaluador": ", ".join(i.tipos),
            "Nota final": i.nota_final if i.nota_final is not None else "Sin nota",
            "Colaborador asignado": "Sí" if i.asignado else "No",
        }
        for i in items
    ]
