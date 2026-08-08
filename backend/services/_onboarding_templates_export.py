"""
Proyección de columnas legibles para el export de plantillas de onboarding.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`empresa_id` y `created_by`). Los headers del Excel son las keys de cada dict.

🔴 `tareas` NO SE VUELCA. `TemplateResponse.tareas` es una lista de objetos anidados, y el
motor de export renderiza escalares: la celda saldría con el `repr` de Python. Lo que sirve en
una planilla es CUÁNTAS tareas tiene cada plantilla —que es lo que se usa para decidir si una
plantilla está armada o quedó a medias—, y eso ya viene contado en `tareas_total`. El detalle
tarea por tarea es la pantalla del template, no un renglón de Excel.

⚠️ Sobre "Visibilidad": el listado del que sale este archivo YA está filtrado por visibilidad
(cada usuario ve las públicas de su empresa más las privadas propias). La columna no habilita
nada; dice si la plantilla que estoy viendo la ven también los demás.
"""
from typing import List

from schemas.onboarding import TemplateResponse


def construir_filas_export(items: List[TemplateResponse]) -> List[dict]:
    """Proyecta las plantillas a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": t.empresa_nombre,
            "Plantilla": t.nombre,
            "Descripción": t.descripcion,
            "Autor": t.created_by_nombre,
            # "Pública"/"Privada" y no True/False: un booleano crudo en Excel sale como
            # VERDADERO/FALSO según el idioma de quien lo abre.
            "Visibilidad": "Pública" if t.es_publica else "Privada",
            "Tareas": t.tareas_total,
        }
        for t in items
    ]
