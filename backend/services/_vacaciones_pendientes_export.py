"""
Proyección de columnas legibles para el export de días de vacaciones PENDIENTES.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`empresa_id`, `empleado_id` y `area_id`). Los headers del Excel son las keys de cada dict.

🔴 "Sin liquidar" ES LA COLUMNA POR LA QUE SE ABRE ESTE ARCHIVO, y es la única derivada:
`dias` son los días no tomados de ese período y `dias_liquidados` los que ya se pagaron, así
que lo que la empresa todavía debe es la resta. La pantalla la muestra como el badge
"N de M" —que se lee de un vistazo pero no se puede sumar—; en una planilla lo que se hace con
esta información es justamente sumarla por empleado o por área. Sin la columna, quien reciba
el archivo la calcula a mano y se equivoca.

Se conservan `Días` y `Liquidados` además de la resta: sin los dos originales no se puede
distinguir "10 pendientes, 10 liquidados" de "0 pendientes" — los dos darían 0 sin liquidar,
y significan cosas distintas.
"""
from typing import List

from schemas.vacaciones_pendientes import VacacionPendienteResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[VacacionPendienteResponse]) -> List[dict]:
    """Proyecta los días pendientes a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": p.empresa_nombre,
            "Empleado": p.empleado_nombre,
            "Área": p.area_nombre,
            "Período": p.periodo,
            "Días": p.dias,
            "Liquidados": p.dias_liquidados,
            "Sin liquidar": p.dias - p.dias_liquidados,
            "Comentario": p.comentario,
            "Cargado": _fecha(p.created_at),
        }
        for p in items
    ]
