"""
Proyección de columnas legibles para el export de recategorizaciones.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`empleado_id`, `empresa_id` y `registrado_por`, cuatro UUIDs que no le dicen nada a nadie). Los
headers del Excel son las keys de cada dict. No toca el motor de export.

🔴 CADA CAMPO SALE COMO UN PAR "ANTES → DESPUÉS" EN DOS COLUMNAS, no como una sola celda con una
flecha. El archivo es lo que alguien abre para revisar el histórico o para pasárselo a
liquidación: con "Rol anterior" y "Rol nuevo" separados se puede filtrar, ordenar y hacer una
tabla dinámica por rol de destino; con `"ANALISTA → ANALISTA SENIOR"` en una celda, no.

🔴 EL IMPACTO SALARIAL SE OMITE SIN PERMISO DE COSTOS, IGUAL QUE EN LA RESPUESTA JSON — y acá
importa más que en la API: un Excel se reenvía por mail. La columna **se saca entera**, no se
vacía: una columna presente y vacía en un archivo que alguien va a mirar a ojo se lee como "no
había monto", que es una afirmación distinta de "no lo podés ver". En la respuesta JSON, en
cambio, el campo se conserva en `None` porque quitarlo cambiaría la FORMA de la respuesta según
el rol, y eso es un contrato que se rompe.
"""
from typing import List

from schemas.recategorizacion import RecategorizacionResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def _monto(v) -> str:
    """Decimal → texto plano sin símbolo. '' si es None (no se cargó).

    Sin formato de miles ni signo de pesos: el destino es una planilla, y un número con puntos
    entra a Excel como texto y deja de poder sumarse.
    """
    return "" if v is None else str(v)


def construir_filas_export(items: List[RecategorizacionResponse],
                           incluir_impacto: bool) -> List[dict]:
    """Proyecta las recategorizaciones a columnas legibles (sin UUIDs crudos).

    Args:
        items: las filas a exportar, ya filtradas.
        incluir_impacto: si el rol tiene `COSTOS + READ`. False saca la columna del archivo.
    """
    filas = []
    for r in items:
        fila = {
            "Fecha efectiva": _fecha(r.fecha_efectiva),
            "Colaborador": r.empleado_nombre,
            "Empresa": r.empresa_nombre,
            "Rol anterior": r.rol_anterior,
            "Rol nuevo": r.rol_nuevo,
            "Seniority anterior": r.seniority_anterior,
            "Seniority nueva": r.seniority_nueva,
            "Categoría anterior": r.categoria_anterior,
            "Categoría nueva": r.categoria_nueva,
            "Motivo": r.motivo,
        }
        if incluir_impacto:
            fila["Impacto salarial"] = _monto(r.impacto_salarial)
        fila["Registrado por"] = r.registrado_por_nombre
        fila["Registrado el"] = _fecha(r.created_at)
        filas.append(fila)
    return filas
