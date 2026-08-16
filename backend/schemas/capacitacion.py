"""
Schemas Pydantic para el módulo de capacitaciones.
Capacitacion: catálogo por empresa — empresa_id explícito en Create.
Asignacion: asignación empleado × curso — empresa_id heredado del empleado al crear.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Catálogo de capacitaciones ─────────────────────────────────────────────────

class CapacitacionCreate(BaseModel):
    empresa_id: UUID
    nombre: str
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    duracion_horas: Optional[float] = None
    obligatoria: bool = False


class CapacitacionUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    duracion_horas: Optional[float] = None
    obligatoria: Optional[bool] = None
    activo: Optional[bool] = None


class CapacitacionResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    duracion_horas: Optional[float] = None
    obligatoria: bool
    activo: bool
    created_at: datetime


class CapacitacionListResponse(BaseModel):
    items: List[CapacitacionResponse]
    total: int


# ── Asignaciones empleado × capacitación ─────────────────────────────────────

class AsignacionCreate(BaseModel):
    capacitacion_id: UUID
    empleado_id: UUID
    fecha_asignacion: Optional[date] = None
    fecha_limite: Optional[date] = None


class AsignacionUpdate(BaseModel):
    estado: Optional[str] = None
    fecha_limite: Optional[date] = None
    fecha_completado: Optional[date] = None


class AsignacionResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    capacitacion_id: str
    capacitacion_nombre: Optional[str] = None
    # 🔴 `empleado_id` es OPCIONAL desde la migración 116: una fila de nombre libre no cuelga de
    # ningún colaborador del sistema. Con `str` a secas, Pydantic tira ValidationError al armar
    # la respuesta y el endpoint devuelve 500. `nombre_libre` es el nombre crudo del Excel de
    # formación, y es lo ÚNICO que identifica a esa persona: sin él la fila sale anónima.
    empleado_id: Optional[str] = None
    empleado_nombre: Optional[str] = None
    nombre_libre: Optional[str] = None
    area_id: Optional[str] = None
    area_nombre: Optional[str] = None
    estado: str
    fecha_asignacion: Optional[date] = None
    fecha_limite: Optional[date] = None
    fecha_completado: Optional[date] = None
    certificado_url: Optional[str] = None
    created_at: datetime


class AsignacionListResponse(BaseModel):
    items: List[AsignacionResponse]
    # 🔴 HOY `total == len(items)` PORQUE ESTE LISTADO NO PAGINA: `asignacion_repo.find_all` trae
    # todas las asignaciones del filtro. Es el más grande de los cinco (1.558 filas en la base de
    # escala), o sea el primero al que se le va a notar.
    # 🔴 EL DÍA QUE PAGINE, `total` TIENE QUE SALIR DE `count="exact"` DE LA MISMA QUERY. Con
    # `.range(...)` puesto y esto sin tocar, `total` pasa a ser el largo de la página y miente sin
    # error: el chequeo de límite del export lo lee y va a creer que entra siempre.
    # Los tres pasos de la migración están en `services/_paginacion.py`.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0
