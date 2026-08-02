"""Schemas de plantillas de mail y de envío (migración 087)."""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PlantillaBase(BaseModel):
    clave: str
    contexto: str
    asunto: str
    cuerpo: str          # Markdown mínimo, NO HTML — ver services/mailer/_markdown.py
    activa: bool = True


class PlantillaUpsert(PlantillaBase):
    """Alta o edición. `id` presente = edición."""
    id: Optional[UUID] = None


class PlantillaResponse(PlantillaBase):
    id: UUID
    empresa_id: Optional[UUID] = None
    # True = es la plantilla GLOBAL, no una propia de la empresa. El front lo usa para avisar
    # que editarla crea una copia de la empresa en vez de pisar la que ven todas.
    es_global: bool = False


class PlantillasListResponse(BaseModel):
    items: List[PlantillaResponse]
    # El catálogo de contextos y sus variables, para que la UI ofrezca solo las válidas y RRHH
    # no las escriba a mano. Viaja con el listado para no pagar un request más.
    contextos: dict


class PreviewRequest(BaseModel):
    contexto: str
    asunto: str
    cuerpo: str
    # None = usar datos de ejemplo. Con datos REALES se ven los huecos reales, que es el punto.
    empleado_id: Optional[UUID] = None


class PreviewResponse(BaseModel):
    asunto: str
    cuerpo_html: str
    # Variables válidas que quedaron SIN VALOR con estos datos. La UI las marca en amarillo:
    # es el momento (3) de los tres, donde RRHH se entera ANTES de mandar.
    faltantes: List[str]
    con_datos_reales: bool


class EnvioRequest(BaseModel):
    plantilla_clave: str
    empleado_ids: List[UUID]


class EnvioResponse(BaseModel):
    enviados: int
    omitidos: int         # ya se les había mandado hoy (idempotencia)
    fallidos: List[dict]
    parcial: bool = False  # se agotó el presupuesto de tiempo
    sin_procesar: int = 0
    segundos: Optional[float] = None
