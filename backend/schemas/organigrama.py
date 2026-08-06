"""Schemas de respuesta para el módulo de Organigrama (vistas empresa y proyecto)."""
from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Vista por empresa: Empresa → Área → Empleado ──────────────────────────────

class EmpleadoNodoResponse(BaseModel):
    id: UUID
    nombre: str
    apellido: str
    cargo: Optional[str] = None
    avatar_url: Optional[str] = None


class AreaNodoResponse(BaseModel):
    id: UUID
    nombre: str
    responsable: Optional[EmpleadoNodoResponse] = None
    empleados: List[EmpleadoNodoResponse] = []
    total_empleados: int


class EmpresaNodoResponse(BaseModel):
    id: UUID
    nombre: str
    total_empleados: int
    areas: List[AreaNodoResponse] = []


# ── Vista por proyecto: Empresa(dueña) → Proyectos → Empleados ───────────────

class EmpleadoProyectoNodoResponse(BaseModel):
    id: UUID
    nombre: str
    apellido: str
    iniciales: str
    cargo: Optional[str] = None
    rol: str
    empleado_empresa_id: UUID
    empleado_empresa_nombre: Optional[str] = None
    total_proyectos: int   # cuántos proyectos activos tiene este empleado
    # Contrato de la asignación (proyecto_asignaciones). Los tres viajan "vacíos" hoy: las 31
    # asignaciones de producción tienen valor_hora=0 y las dos fechas en NULL.
    # ⚠️ `valor_hora` sale TAL CUAL, incluido el 0. Que un 0 signifique "no está cargado" y no
    # "cobra cero" es una decisión de PRESENTACIÓN y vive en el front: el schema describe la
    # fila, no cómo se lee. Traducirlo a None acá le sacaría al front la posibilidad de
    # distinguir —el día que exista— un 0 deliberado.
    valor_hora: float = 0.0
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None


class ProyectoOrgNodoResponse(BaseModel):
    id: UUID
    nombre: str
    estado: str
    empresa_id: UUID
    empresa_nombre: Optional[str] = None
    total_asignados: int
    empleados: List[EmpleadoProyectoNodoResponse] = []


class EmpresaLeyendaResponse(BaseModel):
    """Entrada de leyenda de colores — todas las empresas activas ordenadas por nombre."""
    id: UUID
    nombre: str


class OrgProyectosResponse(BaseModel):
    proyectos: List[ProyectoOrgNodoResponse]
    empresas_orden: List[EmpresaLeyendaResponse]   # paleta de colores: índice → color
