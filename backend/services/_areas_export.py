"""
Proyección de columnas legibles para el export de áreas.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`empresa_id` y `responsable_id`). Los headers del Excel son las keys de cada dict.

⚠️ NO HAY COLUMNA "Empresa", y es una carencia conocida, no una decisión: `AreaResponse` no
trae `empresa_nombre` —solo `empresa_id`, que es un UUID y no puede salir— y agregarlo obliga a
tocar el SELECT del repo, el schema y el mapper. Consecuencia práctica: en modo consolidado el
archivo mezcla áreas de las dos empresas sin forma de distinguirlas, y **dos empresas pueden
tener un "Sistemas" cada una** (es justo el caso que `etiquetaArea` resuelve en el front). El
workaround es exportar con el filtro `empresa_id`, que el endpoint acepta. Cerrarlo de verdad es
sumar `empresa_nombre` al SELECT de `area_repo` — cambio propio, no de esta tanda.
"""
from typing import List

from schemas.area import AreaResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[AreaResponse]) -> List[dict]:
    """Proyecta las áreas a columnas legibles (sin UUIDs crudos).

    🔴 NO deduplica ni agrupa por nombre. En producción hay dos áreas distintas que se llaman
    casi igual ("GESTION DE DEUDA" y "GD - GESTION DE DEUDA"), y nada impide que dos se llamen
    EXACTAMENTE igual: el nombre no es único ni en el schema ni en la práctica. Una fila por
    área, siempre — colapsarlas escondería una de las dos y su dotación.
    """
    return [
        {
            "Área": a.nombre,
            "Descripción": a.descripcion,
            "Responsable": a.responsable_nombre,
            "Empleados": a.cantidad_empleados,
            "Creada": _fecha(a.created_at),
        }
        for a in items
    ]
