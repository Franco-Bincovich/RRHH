"""
Schemas Pydantic para el módulo de vacaciones.
SolicitudVacacionesCreate → Update → Response → ListResponse

El campo `estado` en Response es DERIVADO (calculado en el service, no en la DB):
  - "cancelada"   si cancelada=True
  - "planificada" si hoy < fecha_desde
  - "tomada"      en cualquier otro caso (en curso o pasada)

Tipos de solicitud: vacaciones | semana_free | dia_free | permiso_especial
Solo 'vacaciones' descuenta del saldo anual del empleado.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

TIPOS_VALIDOS = {"vacaciones", "semana_free", "dia_free", "permiso_especial"}


class SolicitudVacacionesCreate(BaseModel):
    empleado_id: UUID
    fecha_desde: date
    fecha_hasta: date
    comentario: Optional[str] = None
    tipo: str = "vacaciones"
    # Año al que CORRESPONDE la licencia, que puede diferir del año de fecha_desde: una
    # licencia tomada en 2026 puede ser del período 2025. Opcional — las filas previas a la
    # migración 083 no lo tienen y no se puede derivar (ver el encabezado de esa migración).
    periodo: Optional[int] = None
    dias_liquidados: int = 0

    @field_validator("periodo")
    @classmethod
    def validate_periodo(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (2000 <= v <= 2100):
            raise ValueError(f"periodo inválido '{v}'. Rango: 2000–2100")
        return v

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        if v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido '{v}'. Valores válidos: {sorted(TIPOS_VALIDOS)}")
        return v


class SolicitudVacacionesUpdate(BaseModel):
    comentario: Optional[str] = None
    tipo: Optional[str] = None
    periodo: Optional[int] = None
    dias_liquidados: Optional[int] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido '{v}'. Valores válidos: {sorted(TIPOS_VALIDOS)}")
        return v


class SolicitudVacacionesResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    empleado_id: str
    empleado_nombre: Optional[str] = None
    area_id: Optional[str] = None
    area_nombre: Optional[str] = None
    fecha_desde: date
    fecha_hasta: date
    dias: int
    tipo: str
    comentario: Optional[str] = None
    cancelada: bool
    estado: str  # "planificada" | "tomada" | "cancelada"
    periodo: Optional[int] = None      # año devengado; None en las filas previas a la mig. 083
    dias_liquidados: int = 0
    created_at: datetime


class SolicitudVacacionesListResponse(BaseModel):
    items: List[SolicitudVacacionesResponse]
    total: int


class SaldoVacacionesResponse(BaseModel):
    empleado_id: str
    asignados: int
    gozados: int   # tomadas (estado="tomada", tipo="vacaciones")
    pedidos: int   # planificadas (estado="planificada", tipo="vacaciones")
    disponibles: int  # asignados − gozados − pedidos
