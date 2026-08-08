"""
Proyección de columnas legibles para el export de onboardings activos.

Las columnas son las que la tarjeta muestra en pantalla (`app/(dashboard)/onboarding/page.tsx`):
empleado, cargo · área, "Inicio: …" y el porcentaje de progreso. Se agregan las dos que la barra
resume visualmente —tareas completadas y totales—, porque un porcentaje sin denominador en una
planilla no se puede auditar: "50%" son 1 de 2 o 6 de 12, y no es lo mismo.

🔴 `fecha_inicio` ES UN `str`, NO UN `date`. `InstanciaResponse` lo declara así (viene tal cual
de la base), así que el `_fecha` de los otros exports —que llama a `.strftime`— reventaría con
AttributeError. Acá se parsea el ISO y se cae al valor crudo si no matchea: un export no puede
tumbarse por el formato de una fecha, y mostrar el ISO es peor que nada pero mucho mejor que un
500 sobre un archivo que alguien está esperando.
"""
from datetime import date
from typing import List

from schemas.onboarding import InstanciaResponse


def _fecha_iso(v) -> str:
    """`'2026-01-15'` → `'15/01/2026'`. '' si es None; el crudo si no se puede parsear."""
    if not v:
        return ""
    try:
        return date.fromisoformat(str(v)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(v)


def construir_filas_export(items: List[InstanciaResponse]) -> List[dict]:
    """Proyecta los onboardings a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": o.empresa_nombre,
            "Empleado": o.empleado_nombre,
            "Cargo": o.empleado_cargo,
            "Área": o.empleado_area,
            "Estado": o.estado,
            "Inicio": _fecha_iso(o.fecha_inicio),
            "Progreso": f"{o.progreso}%",
            "Tareas completadas": o.tareas_completadas,
            "Tareas totales": o.tareas_total,
        }
        for o in items
    ]
