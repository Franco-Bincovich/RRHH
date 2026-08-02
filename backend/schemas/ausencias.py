"""
Schemas Pydantic para el módulo de ausencias.
TipoAusencia: catálogo global (sin empresa_id).
Ausencia: Create → Update → Response → ListResponse.
empresa_id en Response es HEREDADO del empleado al crear, nunca lo provee el usuario.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TipoAusenciaCreate(BaseModel):
    nombre: str


class TipoAusenciaResponse(BaseModel):
    id: str
    nombre: str
    es_base: bool
    activo: bool
    # Migración 085. `empresa_id` None = tipo global (las 4 filas base lo son).
    # `cuenta_ausentismo` es POLÍTICA del tipo y no reemplaza a AusenciaResponse.justificada,
    # que es un HECHO de la instancia: una licencia por maternidad puede estar justificada y
    # aun así no computar como ausentismo.
    empresa_id: Optional[str] = None
    cuenta_ausentismo: bool = True


class TipoAusenciaListResponse(BaseModel):
    items: List[TipoAusenciaResponse]
    total: int


class AusenciaCreate(BaseModel):
    empleado_id: UUID
    tipo_id: UUID
    fecha_desde: date
    fecha_hasta: date
    justificada: bool = False
    motivo: Optional[str] = None


class AusenciaUpdate(BaseModel):
    tipo_id: Optional[UUID] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    justificada: Optional[bool] = None
    motivo: Optional[str] = None


class AusenciaResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    empleado_id: str
    empleado_nombre: Optional[str] = None
    area_id: Optional[str] = None
    area_nombre: Optional[str] = None
    tipo_id: str
    tipo_nombre: Optional[str] = None
    fecha_desde: date
    fecha_hasta: date
    dias: int
    justificada: bool
    motivo: Optional[str] = None
    created_at: datetime


class AusenciaListResponse(BaseModel):
    items: List[AusenciaResponse]
    total: int
