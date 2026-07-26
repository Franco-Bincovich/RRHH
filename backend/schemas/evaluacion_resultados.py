"""
Schemas Pydantic del modelo de resultados de evaluaciones IMPORTADOS (fase 1).
Lote (raíz, empresa_id) → Evaluado (una por persona, ancla del matcheo) → Resultado
(uno por tipo de evaluador × competencia). NO es el motor ev_* (que evalúa DENTRO del
sistema): acá solo se guardan resultados ya calculados afuera. Ver migración 078.
"""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

TipoEvaluador = Literal[
    "AUTOEVALUACION", "AUTOEVALUACION_LIDER", "SUPERIOR_INMEDIATO",
    "PAR", "COLABORADOR", "LIBRES",
]
Perfil = Literal["lider", "general"]


# ── Lotes ─────────────────────────────────────────────────────────────────────

class LoteCreate(BaseModel):
    empresa_id: UUID
    periodo: str
    importado_por: Optional[UUID] = None


class LoteResponse(BaseModel):
    id: UUID
    empresa_id: UUID
    periodo: str
    importado_por: Optional[UUID] = None
    created_at: datetime
    # Campos derivados del historial (los puebla find_lotes con lookups batch; en las lecturas
    # por id quedan en su default, que no exponen conteo/nombres).
    empresa_nombre: Optional[str] = None
    importado_por_nombre: Optional[str] = None
    evaluados: int = 0


class LoteListResponse(BaseModel):
    items: List[LoteResponse]
    total: int


class LotesBulkDelete(BaseModel):
    """Baja múltiple: ids de los lotes a eliminar (multi-selección del historial)."""
    lote_ids: List[UUID]


class LoteBulkError(BaseModel):
    id: UUID
    motivo: str  # mensaje legible del AppError (no encontrado / error de DB)


class LotesBulkResult(BaseModel):
    eliminados: List[UUID]
    fallidos: List[LoteBulkError]


# ── Evaluados ─────────────────────────────────────────────────────────────────

class EvaluadoCreate(BaseModel):
    empleado_id: Optional[UUID] = None   # null = no matcheó (los CSV traen solo nombre)
    nota_final: Optional[float] = None   # null = evaluado sin nota final
    perfil: Perfil
    organismo: Optional[str] = None
    gerencia: Optional[str] = None
    sector: Optional[str] = None
    apellido_evaluado: str
    nombre_evaluado: str
    apellido_superior: Optional[str] = None
    nombre_superior: Optional[str] = None


class EvaluadoResponse(EvaluadoCreate):
    id: UUID
    lote_id: UUID
    created_at: datetime


class EvaluadoListResponse(BaseModel):
    items: List[EvaluadoResponse]
    total: int


# ── Resultados ────────────────────────────────────────────────────────────────

class ResultadoCreate(BaseModel):
    tipo_evaluador: TipoEvaluador
    competencia: str
    orden: int
    nota: float


class ResultadoResponse(ResultadoCreate):
    id: UUID
    evaluado_id: UUID
    created_at: datetime


class ResultadoListResponse(BaseModel):
    items: List[ResultadoResponse]
    total: int
