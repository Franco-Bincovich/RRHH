"""
Schemas Pydantic de la configuración de reglas de negocio (migración 085).

Dos familias: los PARÁMETROS escalares y la ESCALA de vacaciones, que es una lista.
Las dos resuelven por COALESCE(fila de mi empresa, fila global), así que la salida lleva
`es_propia` para que la UI pueda decir si está mirando lo suyo o lo heredado.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ParametrosUpdate(BaseModel):
    """
    Parámetros de la empresa activa. Todos obligatorios: es un PUT, no un PATCH — el form
    manda el juego completo y así no hay forma de guardar medio set y dejar el resto heredado
    sin que nadie lo note.

    Los rangos duplican los CHECK de la base a propósito: Pydantic devuelve un 422 con el
    campo señalado y la base un 500 genérico. El de la base es la red, no la validación.
    """

    base_dias_habiles: int = Field(ge=1, le=31)
    corte_antiguedad_mes: int = Field(ge=1, le=12)
    periodo_vacacional_desde_mes: int = Field(ge=1, le=12)
    periodo_vacacional_hasta_mes: int = Field(ge=1, le=12)
    primer_anio_mes_corte: int = Field(ge=1, le=12)
    primer_anio_dias: int = Field(ge=0)
    vencimiento_anios: int = Field(gt=0)
    # Migración 114. Los dos son de OTRA familia que los cinco de arriba —no son reglas de
    # vacaciones—, y viven en la misma tabla y en el mismo PUT a propósito: `parametros_empresa`
    # ya resuelve el patrón fila-global + fila-por-empresa-que-la-pisa, con sus dos UNIQUE
    # parciales. Una tabla aparte por familia habría duplicado ese mecanismo, y un upsert por
    # familia habría desenganchado a la empresa de las reglas globales de vacaciones al guardar
    # cualquiera de estos dos — que es exactamente el motivo por el que `parametros_screening`
    # sí es tabla propia (ahí el criterio lo escribe otro flujo, no este formulario).
    periodo_prueba_dias: int = Field(ge=1, le=730)
    # Anticipación por DEFECTO del aviso de un evento de agenda. Es el valor que toma un evento
    # nuevo que no trae `dias_aviso` propio; cada evento puede pisarlo. Ver schemas/evento_agenda.
    dias_aviso_evento: int = Field(ge=0, le=365)


class ParametrosResponse(ParametrosUpdate):
    """
    Los mismos valores más de dónde salieron.

    `es_propia=False` significa que la empresa NO tiene fila propia y está usando la global:
    la UI lo dice, porque editar y guardar en ese estado CREA la fila propia y a partir de ahí
    la empresa deja de seguir a la global. Sin ese aviso, el primer guardado desengancharía la
    empresa sin que nadie lo haya decidido.
    """

    es_propia: bool


class TramoEscala(BaseModel):
    """Un escalón: a partir de `antiguedad_anios` cumplidos corresponden `dias`."""

    antiguedad_anios: int = Field(ge=0, le=60)
    dias: int = Field(gt=0, le=365)


class EscalaResponse(BaseModel):
    tramos: List[TramoEscala]
    es_propia: bool


class EscalaUpdate(BaseModel):
    """
    La escala COMPLETA de la empresa activa. Se reemplaza entera, no se parchea tramo a tramo:
    la operación de negocio es "esta es mi escala", y un alta/baja por tramo dejaría estados
    intermedios visibles (una escala sin el tramo de 0 años no aplica a nadie nuevo).
    """

    tramos: List[TramoEscala]


class ConfiguracionResponse(BaseModel):
    """Todo lo que la pantalla de configuración necesita, en una sola ida."""

    parametros: ParametrosResponse
    escala: EscalaResponse


class TipoAusenciaUpdate(BaseModel):
    """
    Edición de un tipo de ausencia. Todo opcional: es un PATCH real, se manda solo lo que
    cambia. `activo=False` es la BAJA — no hay DELETE, ver tipos_ausencia_service.
    """

    nombre: Optional[str] = None
    activo: Optional[bool] = None
    cuenta_ausentismo: Optional[bool] = None
