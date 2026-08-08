"""
Proyección de columnas legibles para el export de períodos cerrados.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo. Las columnas son las de la
tabla en pantalla (Módulo · Desde · Hasta · Estado) más las dos fechas de la traza.

🔴 `cerrado_por` y `reabierto_por` NO SALEN, y no es una omisión: son UUIDs de `users`, o sea
exactamente lo que la regla de este molde prohíbe. Poner el UUID no dice quién fue, y resolver el
nombre obliga a un join que el repo hoy no hace — cambio propio, no de esta tanda. El "quién"
está en `auditoria`, que sí resuelve el usuario al renderizar.

⚠️ Tampoco hay columna "Empresa": `PeriodoResponse` trae `empresa_id` (UUID) y no
`empresa_nombre`. Misma carencia que en áreas, con el mismo workaround: el listado ya viene
acotado por la empresa del header.
"""
from typing import List

from schemas.periodo import PeriodoResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[PeriodoResponse]) -> List[dict]:
    """Proyecta los períodos a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            # `modulo` es NULL cuando el cierre aplica a TODOS los módulos. Se dice, en vez de
            # dejar la celda vacía: un blanco se lee como un dato que falta, y acá significa algo.
            "Módulo": p.modulo or "Todos",
            "Desde": _fecha(p.desde),
            "Hasta": _fecha(p.hasta),
            "Estado": p.estado,
            "Cerrado el": _fecha(p.cerrado_at),
            "Reabierto el": _fecha(p.reabierto_at),
        }
        for p in items
    ]
