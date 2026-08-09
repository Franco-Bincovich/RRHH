"""
Proyección de columnas legibles para el export de vacantes.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`empresa_id`, `area_id` y `linkedin_post_id`). Los headers del Excel son las keys de cada dict.

QUÉ SALE Y QUÉ NO. `VacanteResponse` tiene 22 campos y la mitad no entra en una planilla:

  · **Los bloques de texto libre** (`descripcion`, `requisitos`, `funciones`, `formacion`,
    `copy_publicacion`) quedan afuera. Son párrafos enteros: en una celda de Excel empujan el
    ancho de la fila hasta volver ilegible todo lo demás, y no son el dato que se compara
    cuando alguien mira varias búsquedas juntas. Viven en la ficha de la vacante.
  · **Lo de LinkedIn** (`linkedin_post_id`, `hashtags`) tampoco: el post_id es un identificador
    interno de otra plataforma, del mismo tipo que los UUIDs que este archivo no emite.
  · **Sí salen** las condiciones de la búsqueda —contrato, modalidad, jornada, ubicación—:
    son los campos cortos por los que RRHH compara vacantes entre sí, y los que alguien
    necesita para armar un aviso o responderle a un candidato.

El `estado` sale con el MISMO texto que muestra la pantalla (`ESTADO_LABELS` del front): el
enum crudo `con_candidatos` es un valor de base, no algo que se le muestre a nadie.
"""
from typing import List

from schemas.vacante import VacanteResponse

_ESTADO_LABEL = {
    "nueva": "Nueva",
    "en_proceso": "En proceso",
    "con_candidatos": "Con candidatos",
    "cerrada": "Cerrada",
}


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def _estado(valor) -> str:
    """Traduce el estado al texto de la pantalla. Cae al valor crudo si aparece uno nuevo:
    un archivo que dice `estado_futuro` es raro, pero mucho mejor que uno que dice '' y
    esconde que la vacante está en un estado que nadie contempló."""
    return _ESTADO_LABEL.get(valor, valor or "")


def construir_filas_export(items: List[VacanteResponse]) -> List[dict]:
    """Proyecta las vacantes a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            # Primera columna a propósito: es el token que RRHH pega en el aviso y con el que
            # después identifica de qué búsqueda le está hablando un candidato. En una planilla
            # de varias vacantes es la columna por la que se busca, no un dato de relleno.
            "Código": v.codigo,
            "Empresa": v.empresa_nombre,
            "Título": v.titulo,
            "Área": v.area_nombre,
            "Estado": _estado(v.estado),
            "Tipo de contrato": v.tipo_contrato,
            "Modalidad": v.modalidad,
            "Jornada": v.jornada,
            "Ubicación": v.ubicacion,
            "Email de contacto": v.email_contacto,
            "Fecha de apertura": _fecha(v.fecha_apertura),
            "Creada": _fecha(v.created_at),
        }
        for v in items
    ]
