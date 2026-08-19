"""
Proyección de columnas legibles para el export del CATÁLOGO de capacitaciones.

🔴 NO CONFUNDIR CON `_capacitaciones_export.py`, que es el export de ASIGNACIONES (quién hizo
cuál). Son dos listados distintos, con dos pantallas distintas —la pestaña "Capacitaciones" y la
pestaña "Asignaciones"— y dos endpoints distintos. El nombre de este archivo lleva `_catalogo`
justamente para que no se pisen: el otro ya existía.

Las columnas son las de la tabla en pantalla: Nombre · Categoría · Duración · Empresa ·
Obligatoria · Estado.

🔴 LOS BOOLEANOS SE TRADUCEN. `obligatoria` y `activo` salen como "Sí"/"No" y "Activa"/"Inactiva",
no como True/False: el archivo lo abre alguien de RRHH en Excel, y `True` en una celda es jerga
de programa. Mismo criterio que el "Certificado: Sí/No" del export de asignaciones.
"""
from typing import List

from schemas.capacitacion import CapacitacionResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[CapacitacionResponse]) -> List[dict]:
    """Proyecta el catálogo a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": c.empresa_nombre,
            "Nombre": c.nombre,
            "Descripción": c.descripcion,
            "Categoría": c.categoria,
            # Las tres de la mig 116, tal cual la base las guarda (text libre, sin vocabulario).
            "Entidad capacitadora": c.entidad_capacitadora,
            "Modalidad": c.modalidad,
            "Tipo": c.tipo,
            "Duración (horas)": c.duracion_horas,
            "Obligatoria": "Sí" if c.obligatoria else "No",
            "Estado": "Activa" if c.activo else "Inactiva",
            "Creada": _fecha(c.created_at),
        }
        for c in items
    ]
