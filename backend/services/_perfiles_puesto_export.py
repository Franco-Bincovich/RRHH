"""
Proyección de columnas legibles para el export de perfiles de puesto.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id` y
`created_by`, dos UUIDs que no le dicen nada a nadie). Los headers del Excel son las keys de
cada dict. No toca el motor de export.

🔴 LOS CUATRO CAMPOS DEL BLOQUE "REQUISITOS" SALEN COMO CUATRO COLUMNAS SEPARADAS, en el mismo
orden que el formulario: Experiencia · Formación · Conocimientos técnicos · Otros requisitos.
Concatenarlos en una sola columna "Requisitos" ahorraría ancho y desharía en el archivo la
única separación que este módulo existe para sostener — y encima el archivo es lo que alguien
abre para revisar si los perfiles están bien cargados, o sea el lugar donde la mezcla se tiene
que notar. Ver `schemas/_perfil_puesto_campos.NOTA_REQUISITOS`.

⚠️ NO HAY COLUMNA "EMPRESA", y no es un olvido: un perfil de puesto es del GRUPO y no tiene
empresa que declarar. Es la misma ausencia que en `_clientes_export.py`, pero por un motivo más
fuerte: allá la columna existía en la tabla y no se resolvía a nombre; acá directamente no hay
`empresa_id`.
"""
from typing import List

from schemas.perfil_puesto import PerfilPuestoResponse

# Etiqueta legible de los tres vocabularios cerrados. Se derivan del catálogo de campos para no
# escribir los labels dos veces: si mañana "Semi Senior" pasa a llamarse distinto, se cambia en
# `_perfil_puesto_campos` y el Excel lo sigue solo.
from schemas._perfil_puesto_campos import MODALIDADES, NIVELES, TIPOS_CONTRATO

_ETIQUETAS = {o["value"]: o["label"] for o in (*MODALIDADES, *TIPOS_CONTRATO, *NIVELES)}


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def _label(v) -> str:
    """Traduce un valor de vocabulario cerrado a su etiqueta; '' si es None.

    Cae al valor crudo si no está en el catálogo: un perfil guardado con un valor que después
    se sacó del vocabulario tiene que salir en el archivo igual, no como una celda vacía que
    parece un dato faltante.
    """
    return _ETIQUETAS.get(v, v or "") if v else ""


def construir_filas_export(items: List[PerfilPuestoResponse]) -> List[dict]:
    """Proyecta los perfiles a columnas legibles (sin UUIDs crudos). None → celda vacía.

    🔴 "Activo" se emite como Sí/No y NO como el booleano crudo. El motor renderiza `True`/
    `False` en inglés, que en una planilla que abre alguien de Capital Humano es ruido. Y la
    columna NO se puede omitir: el export acepta `incluir_inactivos`, así que sin ella un
    archivo con bajas adentro es indistinguible de uno sin ellas.
    """
    return [
        {
            "Perfil": p.nombre,
            "Nivel": _label(p.nivel),
            "Modalidad": _label(p.modalidad),
            "Tipo de contrato": _label(p.tipo_contrato),
            "Jornada": p.jornada,
            "Descripción": p.descripcion,
            "Responsabilidades": p.funciones,
            "Experiencia": p.experiencia,
            "Formación": p.formacion,
            "Conocimientos técnicos": p.conocimientos_tecnicos,
            "Otros requisitos": p.requisitos,
            "Ofrecemos": p.ofrecemos,
            "Activo": "Sí" if p.activo else "No",
            "Creado": _fecha(p.created_at),
        }
        for p in items
    ]
