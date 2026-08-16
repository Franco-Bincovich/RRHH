"""
Schemas de los reportes de un lote de evaluaciones importado (fase 5.2): métricas del ciclo,
listado filtrable de evaluados y ficha individual. Todo se computa en Python (ver
_evaluacion_metricas); acá solo la forma de salida.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel


# ── Métricas del ciclo ────────────────────────────────────────────────────────

class ResumenCiclo(BaseModel):
    evaluados: int
    con_nota_final: int
    promedio: Optional[float] = None
    nota_mas_alta: Optional[float] = None
    nota_mas_baja: Optional[float] = None
    evaluaciones: int                      # pares (evaluado × tipo de evaluador)


class BrechaItem(BaseModel):
    empleado_id: Optional[str] = None
    apellido: str
    nombre: str
    auto: Optional[float] = None           # promedio de sus autoevaluaciones
    terceros: Optional[float] = None       # promedio de los demás tipos
    brecha: Optional[float] = None         # auto − terceros (None si falta un lado)


class SectorItem(BaseModel):
    sector: str
    evaluados: int
    promedio: float
    minima: float
    maxima: float


class CompetenciaItem(BaseModel):
    competencia: str
    promedio: float
    n: int                                 # cantidad de notas promediadas


class CompetenciasReporte(BaseModel):
    # Dos rankings SEPARADOS: líder y general nunca se mezclan (sets de competencias distintos).
    lider: List[CompetenciaItem]
    general: List[CompetenciaItem]
    n_lider: int                           # evaluados de perfil líder
    n_general: int


class MetricasResponse(BaseModel):
    resumen: ResumenCiclo
    brecha: List[BrechaItem]
    sectores: List[SectorItem]
    competencias: CompetenciasReporte


# ── Listado + ficha ───────────────────────────────────────────────────────────

class EvaluadoListadoItem(BaseModel):
    id: str                                # id de la fila (evaluacion_evaluados) — abre la ficha
    empleado_id: Optional[str] = None
    apellido: str
    nombre: str
    sector: Optional[str] = None
    superior: Optional[str] = None
    tipos: List[str]
    perfil: str
    nota_final: Optional[float] = None
    asignado: bool                         # False = no se matcheó a un empleado


class EvaluadoListadoResponse(BaseModel):
    items: List[EvaluadoListadoItem]
    # Total del FILTRO sin paginar (`count="exact"`), no el largo de `items`.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0
    # 🔴 LOS SECTORES DEL LOTE ENTERO, no los de la página. El desplegable de sector se poblaba
    # con `Array.from(new Set(todos.map(e => e.sector)))` sobre lo traído: al paginar, ofrecería
    # sólo los sectores que aparecen en la página 1 y filtrar por cualquier otro sería imposible
    # — el usuario ni siquiera vería la opción. Salen de una query de una columna sobre el lote.
    sectores: List[str] = []


class FichaResponse(BaseModel):
    apellido: str
    nombre: str
    sector: Optional[str] = None
    perfil: str
    nota_final: Optional[float] = None
    competencias: List[str]                          # en el orden del archivo
    tipos: List[str]                                 # solo los presentes, en orden canónico
    celdas: Dict[str, Dict[str, float]]              # competencia → {tipo: nota}; ausente = no aplica
    promedio_terceros: Dict[str, float]              # competencia → promedio de terceros
