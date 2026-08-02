"""
Schemas Pydantic para el módulo de proyectos.
Proyectos: empresa_id explícito en Create (empresa dueña).
Asignaciones: empleado_empresa_id NO en Create — el service lo deriva de empleados.empresa_id.
Horas: valor_hora_snapshot NO en Create — el service lo copia de la asignación al insertar.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Costeo ─────────────────────────────────────────────────────────────────────

class CosteoResumen(BaseModel):
    costo_acumulado: float
    presupuesto_restante: float
    pct_consumido: Optional[float] = None   # None si presupuesto == 0


# ── Proyectos ──────────────────────────────────────────────────────────────────

class ProyectoCreate(BaseModel):
    empresa_id: UUID
    nombre: str
    descripcion: Optional[str] = None
    estado: str = "activo"
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    presupuesto: float = Field(default=0.0, ge=0)


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    presupuesto: Optional[float] = Field(default=None, ge=0)


class ProyectoResponse(BaseModel):
    id: UUID
    empresa_id: UUID
    empresa_nombre: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    estado: str
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    presupuesto: float
    costeo: CosteoResumen
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProyectoListResponse(BaseModel):
    items: List[ProyectoResponse]
    total: int


# ── Asignaciones ───────────────────────────────────────────────────────────────

class AsignacionCreate(BaseModel):
    empleado_id: UUID
    rol: str
    valor_hora: float = Field(default=0.0, ge=0)
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class AsignacionUpdate(BaseModel):
    rol: Optional[str] = None
    valor_hora: Optional[float] = Field(default=None, ge=0)
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    activo: Optional[bool] = None


class AsignacionResponse(BaseModel):
    id: UUID
    proyecto_id: UUID
    empleado_id: UUID
    empleado_nombre: Optional[str] = None
    empleado_empresa_id: UUID
    empleado_empresa_nombre: Optional[str] = None
    rol: str
    valor_hora: float
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    activo: bool
    created_at: datetime


class AsignacionListResponse(BaseModel):
    items: List[AsignacionResponse]
    total: int


class AsignacionBulkCreate(BaseModel):
    """Alta multi-selección: varios empleados con los MISMOS rol/valor_hora/fechas (compartidos)."""
    empleado_ids: List[UUID]
    rol: str
    valor_hora: float = Field(default=0.0, ge=0)
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class AsignacionAreaCreate(BaseModel):
    """Alta de un ÁREA ENTERA a un proyecto: mismos datos compartidos que el bulk manual.

    🔴 ES UNA FOTO, NO UN VÍNCULO VIVO. Se resuelven los empleados del área EN ESE MOMENTO y se
    crean asignaciones individuales; el proyecto NO queda atado al área. Un alta posterior en el
    área no entra sola al proyecto, y —lo que importa— sacar a alguien del área NO le borra una
    asignación. Un vínculo vivo lo haría, y `proyecto_asignaciones` lleva `rol`, `valor_hora` y
    fechas POR PERSONA, además de que `horas_proyecto` cuelga de una asignación concreta: borrarla
    se llevaría horas cargadas, que es justo lo que `ASIGNACION_CON_HORAS` (409) protege hoy.
    """
    area_id: UUID
    rol: str
    valor_hora: float = Field(default=0.0, ge=0)
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class AsignacionBulkError(BaseModel):
    empleado_id: UUID
    motivo: str  # mensaje legible del AppError (ya asignado / inactivo / no encontrado)


class AsignacionBulkResult(BaseModel):
    """Resultado de un alta múltiple, en TRES grupos.

    🔴 `ya_asignados` SE SEPARA DE `errores` A PROPÓSITO, y no es cosmético. Un empleado que ya
    estaba en el proyecto no es un fallo: es la operación siendo idempotente. Mezclarlo con los
    errores reales estaba bien mientras el usuario elegía de a uno y veía la lista; asignando un
    ÁREA ENTERA lo normal es que la mitad ya esté, y "15 errores" se lee como un fallo masivo.

    La prueba de que hacía falta: el modal tenía que aclararlo a mano en el texto —"N no se
    pudieron (ya asignados o inactivos)"— porque el tipo no distinguía las dos cosas.

    En `errores` quedan los fallos DE VERDAD: el empleado no existe, o está dado de baja.
    """
    asignados: List[AsignacionResponse]
    ya_asignados: List[AsignacionBulkError] = []
    errores: List[AsignacionBulkError]


# ── Horas ──────────────────────────────────────────────────────────────────────

class HoraCreate(BaseModel):
    asignacion_id: UUID
    fecha: date
    horas: float = Field(..., gt=0)
    descripcion: Optional[str] = None


class HoraResponse(BaseModel):
    id: UUID
    asignacion_id: UUID
    proyecto_id: UUID
    empleado_nombre: Optional[str] = None
    empleado_empresa_nombre: Optional[str] = None
    fecha: date
    horas: float
    valor_hora_snapshot: float
    costo: float           # horas × valor_hora_snapshot, calculado en _build()
    descripcion: Optional[str] = None
    created_at: datetime


class HoraListResponse(BaseModel):
    items: List[HoraResponse]
    total: int
