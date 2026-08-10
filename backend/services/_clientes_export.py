"""
Proyección de columnas legibles para el export de clientes.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id` y
`empresa_id`, dos UUIDs que no le dicen nada a nadie). Los headers del Excel son las keys de
cada dict. No toca el motor de export.

⚠️ TAMPOCO HAY COLUMNA "Empresa", y por el mismo motivo que en `_areas_export.py`:
`ClienteResponse` trae `empresa_id` (UUID) y no `empresa_nombre`. En modo consolidado el archivo
mezcla los clientes de las dos empresas sin forma de distinguirlos — y con un catálogo por
empresa, dos sociedades del grupo pueden tener un cliente con el mismo nombre cada una (el
índice único es POR empresa justamente porque eso es legítimo). El workaround es el mismo:
exportar con el filtro `empresa_id`, que el endpoint acepta. Cerrarlo de verdad es sumar
`empresa_nombre` al SELECT del repo y al schema — cambio propio, no de esta tanda.
"""
from typing import List

from schemas.cliente import ClienteResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[ClienteResponse]) -> List[dict]:
    """Proyecta los clientes a columnas legibles (sin UUIDs crudos).

    🔴 "Activo" se emite como Sí/No y NO como el booleano crudo. El motor renderiza `True`/
    `False` en inglés, que en una planilla que abre alguien de RRHH es ruido. Y la columna NO se
    puede omitir: el export acepta `incluir_inactivos`, así que sin ella un archivo con bajas
    adentro es indistinguible de uno sin ellas.
    """
    return [
        {
            "Cliente": c.nombre,
            "Activo": "Sí" if c.activo else "No",
            "Creado": _fecha(c.created_at),
        }
        for c in items
    ]
