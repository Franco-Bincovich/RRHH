"""
Proyección de columnas legibles para el export de la nómina de un período.

Mismo molde que los otros exports: no vuelca model_dump() crudo (que incluiría los UUIDs de
empleado y empresa). El período no va como columna repetida en cada fila — es el mismo para
todas y ya viaja en el nombre del reporte.

Los tres montos salen como número, no como texto formateado: el archivo se abre para sumar y
filtrar, y un "$ 1.234,56" convierte la columna en strings y rompe cualquier fórmula.
"""
from typing import List

from schemas.costo import NominaResponse


def construir_filas_export(items: List[NominaResponse]) -> List[dict]:
    """Proyecta la nómina del período a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": n.empresa_nombre,
            "Empleado": n.empleado_nombre,
            "Área": n.area_nombre,
            "Mes": n.mes,
            "Año": n.anio,
            "Bruto": n.monto_bruto,
            "Neto": n.monto_neto,
            "Costo total": n.total,
        }
        for n in items
    ]
