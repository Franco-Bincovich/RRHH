"""
Schemas del clasificador de CVs (migración 100): el criterio configurable y el resultado del lote.

El criterio resuelve por COALESCE(fila de mi empresa, fila global), igual que `parametros_empresa`
(085), así que la salida lleva `es_propia`: la pantalla necesita poder decir si estás mirando lo
tuyo o lo heredado, porque guardar mientras heredás CREA tu fila propia y te desengancha.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# El mismo tope que el CHECK `ps_largos_check` de la migración 100 y que `_clasificador_prompt`.
# Duplicado a propósito: Pydantic devuelve 422 señalando el campo, la base un 500 genérico.
_MAX = 2_000


class ScreeningCriterioUpdate(BaseModel):
    """
    Las tres definiciones y las instrucciones opcionales. PUT, no PATCH: el form manda el juego
    completo, así no se puede guardar media definición y dejar el resto heredado sin que nadie
    lo note.

    ⚠️ Estos textos se INSERTAN COMO DATO dentro de la estructura fija del prompt. NO la
    reemplazan ni la extienden: no pueden cambiar las tres categorías, ni el formato de salida,
    ni la regla de "ante la duda, dudoso". Ver `services/_clasificador_prompt.py`.
    """

    def_relevante: str = Field(min_length=1, max_length=_MAX)
    def_dudoso: str = Field(min_length=1, max_length=_MAX)
    def_no_relevante: str = Field(min_length=1, max_length=_MAX)
    instrucciones: str = Field(default="", max_length=_MAX)


class ScreeningCriterioResponse(ScreeningCriterioUpdate):
    """
    El criterio vigente más de dónde salió.

    `es_propia=False` = la empresa NO tiene fila propia y está usando la global. La UI lo dice,
    porque editar y guardar en ese estado crea la fila propia y a partir de ahí la empresa deja
    de seguir a la global. "Restaurar defaults" es exactamente volver a ese estado.
    """

    es_propia: bool


class ClasificacionUpdate(BaseModel):
    """
    La corrección manual de UN candidato. PUT: el humano fija el veredicto vigente entero.

    🔴 `motivo` es OBLIGATORIO y no opcional. La clasificación que se pisa ya venía con el suyo
    ("Perfil en gastronomía, la búsqueda es contable"); dejar cambiar la etiqueta sin escribir
    por qué produciría una fila que dice `relevante` con el motivo del `no_relevante` anterior,
    que es peor que no tener motivo. Y la corrección es justamente el dato que después se lee
    para saber en qué se equivoca el filtro: sin el porqué, no se puede leer.

    ⚠️ NO se puede volver a "sin clasificar": las tres categorías son el conjunto cerrado. Un
    cuarto estado "revertido" haría indistinguible al candidato que un humano vació del que
    nunca pasó por el clasificador — que es exactamente el bug que esta tanda vino a cerrar.
    """

    clasificacion: Literal["relevante", "dudoso", "no_relevante"]
    motivo: str = Field(min_length=1, max_length=400)


class CandidatoClasificado(BaseModel):
    """Una línea del resultado del lote, para que la pantalla diga qué pasó con cada uno."""

    candidato_id: str
    nombre: str
    clasificacion: Optional[str] = None
    motivo: Optional[str] = None
    error: Optional[str] = None


class ScreeningLoteResponse(BaseModel):
    """
    Resultado NO BINARIO del botón: qué se clasificó, qué se salteó y qué quedó pendiente.

    Los tres números son distintos y ninguno se deduce de los otros:
      · `clasificados`   — llegaron al modelo y volvieron con una de las tres categorías.
      · `sin_texto`      — tenían `screening_warning`: NO se clasifican y NO gastan llamada.
                           Van a revisión manual; no son un error del lote.
      · `errores`        — el modelo devolvió algo inválido, o la llamada falló. Quedan en NULL.
      · `sin_procesar`   — se acabó el presupuesto de tiempo antes de llegar a ellos. Reintentable:
                           volver a apretar el botón los toma, porque solo se piden los que
                           siguen sin clasificar.
    """

    clasificados: int
    sin_texto: int
    errores: int
    sin_procesar: int
    parcial: bool
    tope_alcanzado: bool
    #: La descripción de la búsqueda pasó el tope del prompt y el modelo vio solo una parte.
    #: Lo tiene que ver RRHH: es quien puede acortarla, y no lee el prompt.
    busqueda_truncada: bool = False
    segundos: float
    detalle: List[CandidatoClasificado]
