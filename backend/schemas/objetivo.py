"""
Schemas Pydantic para el módulo de objetivos.
ObjetivoCreate → Update → Response → ListResponse

responsable_id: FK a users (operadores RRHH), NO empleados.
empresa_id: explícito en Create; heredado por el objeto en lecturas.
estado: no se pide al crear (default 'por_hacer'); se cambia por CambiarEstadoRequest.

JERARQUÍA (migración 095): `parent_id` self-FK, profundidad máxima 2 — un objetivo con padre no
puede ser padre de otro. La guarda vive en services/_objetivos_jerarquia.py, no en un CHECK.

MÚLTIPLES RESPONSABLES (migración 096): `responsable_id` sigue siendo el DUEÑO PRINCIPAL y no se
toca; `responsables` es la lista COMPLETA (incluye al dueño) que arma la tabla puente.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

PRIORIDADES = {"baja", "media", "alta"}
ESTADOS = {"por_hacer", "haciendo", "terminado"}
ORDEN_ESTADOS = ["por_hacer", "haciendo", "terminado"]


class ObjetivoCreate(BaseModel):
    empresa_id:     UUID
    responsable_id: UUID
    titulo:         str
    descripcion:    Optional[str] = None
    prioridad:      str = "media"
    fecha_entrega:  Optional[date] = None
    parent_id:      Optional[UUID] = None       # None = objetivo raíz
    # Responsables ADICIONALES al dueño. El dueño entra siempre a la puente, venga o no acá.
    responsables:   Optional[List[UUID]] = None


class ObjetivoUpdate(BaseModel):
    responsable_id: Optional[UUID] = None
    titulo:         Optional[str] = None
    descripcion:    Optional[str] = None
    prioridad:      Optional[str] = None
    fecha_entrega:  Optional[date] = None
    parent_id:      Optional[UUID] = None
    # `None` = no se toca la lista. `[]` = se deja solo al dueño. Ver services/objetivo_service.
    responsables:   Optional[List[UUID]] = None


class ResponsableItem(BaseModel):
    """Un responsable del objetivo, con el nombre ya resuelto desde `users`."""
    id:     str
    nombre: Optional[str] = None


class CambiarEstadoRequest(BaseModel):
    estado: str


class ObjetivoResponse(BaseModel):
    id:                  str
    empresa_id:          str
    empresa_nombre:      Optional[str] = None
    responsable_id:      str
    responsable_nombre:  Optional[str] = None
    titulo:              str
    descripcion:         Optional[str] = None
    prioridad:           str
    estado:              str
    fecha_entrega:       Optional[date] = None
    created_at:          datetime
    updated_at:          datetime
    parent_id:           Optional[str] = None
    parent_titulo:       Optional[str] = None   # derivado: alimenta la columna del export
    # Lista COMPLETA de responsables (el dueño incluido). Vacía solo si la puente no tiene filas.
    responsables:        List[ResponsableItem] = []
    # Subobjetivos anidados. Siempre vacía en un hijo: la profundidad máxima es 2.
    hijos:               List["ObjetivoResponse"] = []


ObjetivoResponse.model_rebuild()   # `hijos` se referencia a sí misma


class ObjetivoListResponse(BaseModel):
    items: List[ObjetivoResponse]
    # 🔴 HOY `total == len(items)` PORQUE EL TABLERO NO PAGINA: `objetivo_repo.find_all` devuelve
    # todo el árbol del filtro.
    # 🔴 EL DÍA QUE PAGINE, `total` SALE DE `count="exact"` DE LA MISMA QUERY — y acá hay una
    # trampa propia: `items` son las RAÍCES, con los hijos anidados adentro. O sea `len(items)` ya
    # no es la cantidad de objetivos ni cuando NO se pagina. `total` cuenta raíces (es lo que
    # pagina); el conteo aplanado que usa el export es otra cosa y sale de
    # `_objetivos_arbol.contar_con_hijos`. Confundirlos hace que el tope de export deje pasar el
    # doble de filas. Los tres pasos de la migración, en `services/_paginacion.py`.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0
