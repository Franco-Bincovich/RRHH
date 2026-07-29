"""
Schemas del módulo de días de vacaciones PENDIENTES (los que NO se tomaron).
Create → Update → Response → ListResponse.

`empresa_id` en Response es HEREDADO del empleado al crear, nunca lo provee el usuario
(mismo criterio que vacaciones y ausencias).

Esta entidad NO tiene fechas: un día no tomado no tiene fecha porque nadie faltó ningún día.
Por eso vive en su propia tabla y no como una fila sin fechas en solicitudes_vacaciones —
el porqué completo está en migrations/083_vacaciones_periodo_y_pendientes.sql.

`dias_liquidados` es un ENTERO y no un bool `liquidada`: admite liquidación PARCIAL en una
sola fila (5 de 10 días pagados), sin romper la UNIQUE (empleado_id, periodo) que le da al
import su idempotencia. La UI lo maneja como un tilde: tildado → dias_liquidados = dias.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

PERIODO_MIN, PERIODO_MAX = 2000, 2100


def _validar_periodo(v: Optional[int]) -> Optional[int]:
    """Rango del CHECK vp_periodo_check. Mismo criterio que costos_nomina.anio."""
    if v is not None and not (PERIODO_MIN <= v <= PERIODO_MAX):
        raise ValueError(f"periodo inválido '{v}'. Rango: {PERIODO_MIN}–{PERIODO_MAX}")
    return v


class VacacionPendienteCreate(BaseModel):
    empleado_id: UUID
    periodo: int
    dias: int
    dias_liquidados: int = 0
    comentario: Optional[str] = None

    _periodo = field_validator("periodo")(_validar_periodo)

    @field_validator("dias")
    @classmethod
    def validate_dias(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("dias debe ser mayor a 0")
        return v


class VacacionPendienteUpdate(BaseModel):
    """Patch parcial. `dias_liquidados` es el campo que se edita después de creada."""
    periodo: Optional[int] = None
    dias: Optional[int] = None
    dias_liquidados: Optional[int] = None
    comentario: Optional[str] = None

    _periodo = field_validator("periodo")(_validar_periodo)


class VacacionPendienteResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    empleado_id: str
    empleado_nombre: Optional[str] = None
    area_id: Optional[str] = None
    area_nombre: Optional[str] = None
    periodo: int
    dias: int
    dias_liquidados: int
    comentario: Optional[str] = None
    created_at: datetime


class VacacionPendienteListResponse(BaseModel):
    items: List[VacacionPendienteResponse]
    total: int
