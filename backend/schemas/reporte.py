"""
Schemas Pydantic para el módulo de Reportes.
"""
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

TipoReporte = Literal[
    "headcount", "rotacion", "altas_bajas", "distribucion",
    "costos", "vacantes", "onboarding", "adhoc", "anual_consolidado",
    "saldos_vacaciones", "ausentismo", "listado_vac_aus",
    "presupuesto", "capacitacion", "auditoria",
]

VistaAusentismo = Literal["total", "injustificado", "ambos"]


class ReporteGenerarRequest(BaseModel):
    tipo: TipoReporte
    mes: Optional[int] = None
    anio: Optional[int] = None
    prompt: Optional[str] = None
    # Armado manual: empresa y área salen del FORM (no del header X-Empresa-Id del sidebar).
    empresa_id: Optional[UUID] = None  # None = consolidado (todas las empresas)
    area_id: Optional[UUID] = None     # None = todas las áreas de la empresa
    vista: Optional[VistaAusentismo] = None  # solo ausentismo: total | injustificado | ambos


class ReporteResponse(BaseModel):
    id: UUID
    nombre: str
    tipo: str
    datos: Dict[str, Any]
    generado_por: str
    created_at: datetime
    empresa_id: Optional[UUID] = None  # null = consolidado (visible para todas las empresas)


class HistorialItem(BaseModel):
    id: UUID
    nombre: str
    tipo: str
    generado_por: str
    created_at: datetime
    empresa_id: Optional[UUID] = None
    empresa_nombre: Optional[str] = None
