"""
Proyección de columnas legibles para el export de proyectos.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría UUIDs).
Los headers del Excel son las keys de cada dict. No toca el motor de export.

🔴 `costeo` SE APLANA en tres columnas. `ProyectoResponse.costeo` es un objeto anidado
(`CosteoResumen`), y el motor de export renderiza escalares y listas de dicts: un objeto adentro
de una celda sale como el `repr` de Python. Además, "costo acumulado" y "presupuesto restante"
son justo las dos columnas que alguien abre el Excel para mirar — enterrarlas en un anidado las
haría inútiles.
"""
from typing import List

from schemas.proyectos import ProyectoResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def _pct(v) -> str:
    """El % consumido es None cuando el presupuesto es 0 (no hay contra qué medir). Se emite ''
    y no '0%': cero por ciento consumido y "no se puede calcular" son cosas distintas."""
    return f"{v:.1f}%" if v is not None else ""


def construir_filas_export(items: List[ProyectoResponse]) -> List[dict]:
    """Proyecta los proyectos a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": p.empresa_nombre,
            "Proyecto": p.nombre,
            "Descripción": p.descripcion,
            "Estado": p.estado,
            "Fecha inicio": _fecha(p.fecha_inicio),
            "Fecha fin": _fecha(p.fecha_fin),
            "Presupuesto": p.presupuesto,
            "Costo acumulado": p.costeo.costo_acumulado,
            "Presupuesto restante": p.costeo.presupuesto_restante,
            "% consumido": _pct(p.costeo.pct_consumido),
            "Creado": _fecha(p.created_at),
        }
        for p in items
    ]
