"""
Schemas Pydantic para el módulo de Reportes.
"""
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

TipoReporte = Literal["headcount", "rotacion", "costos", "vacantes", "onboarding", "adhoc"]


class ReporteGenerarRequest(BaseModel):
    tipo: TipoReporte
    mes: Optional[int] = None
    anio: Optional[int] = None
    prompt: Optional[str] = None


class ReporteResponse(BaseModel):
    id: UUID
    nombre: str
    tipo: str
    datos: Dict[str, Any]
    generado_por: str
    created_at: datetime
    empresa_id: Optional[UUID] = None  # null = consolidado (visible para todas las empresas)


class HistorialItem(BaseModel):
    id: UUID
    nombre: str
    tipo: str
    generado_por: str
    created_at: datetime
    empresa_id: Optional[UUID] = None
    empresa_nombre: Optional[str] = None
