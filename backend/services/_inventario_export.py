"""
Proyección de columnas legibles para el export de asignaciones de inventario.

Extraído del service para no volcar model_dump() crudo (que incluía UUIDs). Los
headers del Excel son las keys de cada dict (el motor genérico las capitaliza);
por eso las keys YA son el header legible. No toca el motor de export.
"""
from typing import List

from schemas.inventario import AsignacionResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[AsignacionResponse]) -> List[dict]:
    """Proyecta las asignaciones a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": a.empresa_nombre,
            "Colaborador": a.empleado_nombre,
            "Equipo": a.item_nombre,
            "Tipo": a.item_tipo,
            "N° serie": a.item_numero_serie,
            "Estado devolución": a.estado_devolucion,
            "Notas": a.notas,
            "Fecha asignación": _fecha(a.fecha_asignacion),
            "Fecha devolución": _fecha(a.fecha_devolucion),
            "Creada": _fecha(a.created_at),
        }
        for a in items
    ]
