"""
Schemas Pydantic para onboarding — templates, tareas e instancias.
"""
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class TareaCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    semana: Literal[1, 2, 3, 4]
    orden: int
    responsable_tipo: Literal["rrhh", "manager", "empleado", "ti", "administracion"] = "rrhh"
    dias_limite: int = 1


class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    semana: Optional[Literal[1, 2, 3, 4]] = None
    orden: Optional[int] = None


class TareaResponse(BaseModel):
    id: UUID
    template_id: UUID
    titulo: str
    descripcion: Optional[str] = None
    semana: int
    orden: int


class TemplateCreate(BaseModel):
    nombre: str
    empresa_id: UUID  # root entity — empresa explícita obligatoria
    descripcion: Optional[str] = None


class TemplateUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    # Visibilidad. Solo la puede cambiar quien alcanza la plantilla, y a una privada ajena no
    # se llega (404 antes de escribir) — el gate es el mismo que el del resto de las ediciones.
    es_publica: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: UUID
    nombre: str
    empresa_id: Optional[UUID] = None
    empresa_nombre: Optional[str] = None
    descripcion: Optional[str] = None
    # Autor. `created_by` es NULL en los templates anteriores al cableado del autor y en
    # aquellos cuyo usuario se borró (FK ON DELETE SET NULL). `created_by_nombre` es derivado
    # de un join: NUNCA debe entrar en un diff de auditoría (ver _audit_payloads.py).
    created_by: Optional[UUID] = None
    created_by_nombre: Optional[str] = None
    # true = la ven todos los usuarios de la empresa; false = solo su autor. Un created_by NULL
    # se trata como pública (migración 082, regla de huérfanas).
    es_publica: bool = True
    tareas: List[TareaResponse] = []
    tareas_total: int = 0


class IniciarOnboardingRequest(BaseModel):
    template_id: Optional[UUID] = None


class TareaProgresoResponse(BaseModel):
    progreso_id: UUID
    tarea_id: UUID
    titulo: str
    descripcion: Optional[str] = None
    semana: int
    orden: int
    completada: bool


class InstanciaResponse(BaseModel):
    id: UUID
    empleado_id: UUID
    empresa_id: Optional[UUID] = None
    empresa_nombre: Optional[str] = None
    empleado_nombre: str
    empleado_cargo: Optional[str] = None
    empleado_area: Optional[str] = None
    template_id: UUID
    estado: str
    fecha_inicio: str
    progreso: int
    tareas_completadas: int
    tareas_total: int


class InstanciaDetalleResponse(InstanciaResponse):
    tareas: List[TareaProgresoResponse] = []
