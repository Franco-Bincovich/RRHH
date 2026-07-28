"""
Schemas Pydantic para offboarding — instancias y activos.
"""
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

MotivoEgreso = Literal[
    "renuncia", "despido", "acuerdo_mutuo",
    "fin_contrato", "jubilacion", "fallecimiento", "otro",
]


class OffboardingCreate(BaseModel):
    empleado_id: UUID
    motivo: MotivoEgreso
    fecha_ultimo_dia: Optional[date] = None
    descripcion_motivo: Optional[str] = None


class ActivoUpdate(BaseModel):
    devuelto: bool


class EntrevistaUpdate(BaseModel):
    """Entrevista de salida. Las notas son opcionales: se puede marcar que la entrevista se
    hizo sin dejar constancia escrita, y también guardar notas de una entrevista en curso."""
    entrevista_salida: bool
    notas_entrevista: Optional[str] = None


class ActivoResponse(BaseModel):
    id: UUID
    tipo_activo: str
    descripcion: Optional[str] = None
    estado: str
    devuelto: bool


class AccesoResponse(BaseModel):
    id: UUID
    tipo: str
    descripcion: Optional[str] = None
    revocado: bool


class OffboardingResponse(BaseModel):
    id: UUID
    empleado_id: UUID
    empresa_id: Optional[UUID] = None
    empresa_nombre: Optional[str] = None
    empleado_nombre: str
    motivo: str
    estado: str
    fecha_inicio: str
    progreso: int
    entrevista_salida: bool = False
    notas_entrevista: Optional[str] = None
    activos: List[ActivoResponse] = []
    accesos: List[AccesoResponse] = []
