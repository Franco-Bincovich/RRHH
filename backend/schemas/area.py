"""
Schemas Pydantic para el módulo de áreas.
AreaCreate → AreaUpdate → AreaResponse
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AreaCreate(BaseModel):
    # 🔴 UUID, no str. Un `str` mueve la validación de la frontera al motor de base de datos: el
    # front mandaba `empresa_id: ""` con el sidebar en consolidado, Pydantic lo aceptaba, y
    # Postgres lo rechazaba con 22P02 → 500. Tipado UUID, el mismo body sale como 422 y el
    # handler de validación lo traduce a "Revisá los datos del formulario: empresa (falta)".
    # Base 4 del proyecto: los ids externos SIEMPRE como UUID tipado.
    empresa_id: UUID
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    # `UUID | None` y no `UUID`: el responsable es OPCIONAL (un área puede no tener). Tipado, un
    # `""` del front sale como 422 en vez de morir en Postgres — mismo criterio que `empresa_id`.
    responsable_id: Optional[UUID] = None


class AreaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    descripcion: Optional[str] = None
    responsable_id: Optional[UUID] = None


class AreaResponse(BaseModel):
    id: str
    empresa_id: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    responsable_id: Optional[str] = None
    responsable_nombre: Optional[str] = None
    cantidad_empleados: int
    created_at: datetime
