"""
Schemas Pydantic para el módulo de inventario.
Items: catálogo por empresa — empresa_id explícito en Create.
Asignaciones: empresa_id heredado del ítem al crear (no lo provee el usuario).
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Ítems de inventario ────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    empresa_id: UUID
    nombre: str
    tipo: str
    descripcion: Optional[str] = None
    numero_serie: Optional[str] = None
    fecha_alta: Optional[date] = None
    costo: Optional[float] = None
    notas: Optional[str] = None


class ItemUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    numero_serie: Optional[str] = None
    costo: Optional[float] = None
    notas: Optional[str] = None
    estado: Optional[str] = None


class ItemResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    nombre: str
    tipo: str
    descripcion: Optional[str] = None
    numero_serie: Optional[str] = None
    estado: str
    fecha_alta: date
    costo: Optional[float] = None
    notas: Optional[str] = None
    asignado_a: Optional[str] = None  # nombre del empleado que lo tiene actualmente
    created_at: datetime


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    # 🔴 HOY `total == len(items)` PORQUE EL CATÁLOGO NO PAGINA: `inventario_items_repo.find_all`
    # devuelve todas las filas de la empresa, así que "las que mandé" y "las que hay" coinciden.
    # 🔴 EL DÍA QUE PAGINE, `total` TIENE QUE SALIR DE `count="exact"` DE LA MISMA QUERY. Agregar
    # `.range(...)` al repo sin tocar esto deja a `total` valiendo el largo de la página: la barra
    # dice "1 de 1", el export cree que trajo todo, y no hay error que lo delate. Es exactamente
    # el bug que ya tuvo la pantalla de horas de un proyecto ("9 h" sobre un proyecto de 400).
    # Los tres pasos de la migración están en `services/_paginacion.py`.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0


# ── Asignaciones ───────────────────────────────────────────────────────────────

class AsignacionCreate(BaseModel):
    item_id: UUID
    empleado_id: UUID


class DevolucionRequest(BaseModel):
    estado_devolucion: str  # "ok" | "con_daño"
    notas: Optional[str] = None


class AsignacionResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: Optional[str] = None
    item_id: str
    item_nombre: Optional[str] = None
    item_tipo: Optional[str] = None
    item_numero_serie: Optional[str] = None
    empleado_id: str
    empleado_nombre: Optional[str] = None
    fecha_asignacion: date
    fecha_devolucion: Optional[date] = None
    estado_devolucion: Optional[str] = None
    notas: Optional[str] = None
    created_at: datetime


class AsignacionListResponse(BaseModel):
    items: List[AsignacionResponse]
    # 🔴 HOY `total == len(items)` PORQUE ESTE LISTADO NO PAGINA: `find_all` trae todas las
    # asignaciones ACTIVAS de la empresa (`fecha_devolucion IS NULL`) sin recortar.
    # 🔴 EL DÍA QUE PAGINE, `total` SALE DE `count="exact"` DE LA MISMA QUERY, no de `len(items)`.
    # ⚠️ Y ojo con el otro caller: `get_historial` usa este MISMO wrapper para el historial de un
    # ítem, que no se pagina nunca. Al paginar el listado hay que dejar el historial como está —
    # si los dos comparten el cálculo del total, el que no pagina va a heredar un `page_size` que
    # no significa nada. Los tres pasos, en `services/_paginacion.py`.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0
