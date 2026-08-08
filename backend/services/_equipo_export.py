"""
Proyección de columnas legibles para el export del roster "mi equipo".

🔴 SON TRES COLUMNAS Y ESO ES TODO LO QUE HAY, a propósito. `EquipoMiembroResponse` expone
identidad mínima + empresa legible porque el punto de /equipo es dar el universo de ownership
**sin abrir la sección empleados**: un `mandos_medios` llega acá y NO tiene permiso de EMPLEADOS.
Sumarle cargo, área, fecha de ingreso o cualquier otro campo convertiría este export en la puerta
de atrás a la ficha del empleado — exactamente lo que el módulo evita. Si alguna vez hace falta
más, la decisión es de permisos, no de esta proyección.

El `id` queda afuera por la regla de siempre: es un UUID y no le dice nada a quien abre el Excel.
"""
from typing import List

from schemas.equipo import EquipoMiembroResponse


def construir_filas_export(items: List[EquipoMiembroResponse]) -> List[dict]:
    """Proyecta el roster a columnas legibles (sin UUIDs crudos).

    El orden de las columnas sigue al del listado, que el repo ya devuelve ordenado por
    apellido y después nombre.
    """
    return [
        {
            "Apellido": m.apellido,
            "Nombre": m.nombre,
            # Puede venir en None: el join a empresas es to-one y un empleado sin empresa
            # cargada existe. Y la empresa PUEDE ser distinta de la del jefe — ver el service.
            "Empresa": m.empresa,
        }
        for m in items
    ]
