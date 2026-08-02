"""
Schemas de respuesta para el módulo de Dashboard Ejecutivo.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel


class KPIResponse(BaseModel):
    empleados_activos: int
    ingresos_mes: int
    bajas_mes: int
    costo_nomina: float
    onboardings_activos: int
    vacantes_activas: int


class AlertaResponse(BaseModel):
    tipo: str
    mensaje: str
    nivel: Literal["info", "warning", "error"]
    # Ruta del front a la que lleva la alerta, o None si no lleva a ninguna parte.
    #
    # 🔴 Reemplaza al `entidad_id` anterior, que el front convertía SIEMPRE en
    # `/empleados/{id}`: la primera alerta de otro tipo con id habría linkeado a una ficha de
    # empleado inexistente. El molde de adjuntos (entidad + entidad_id) tampoco alcanzaba —
    # una alerta agregada lleva a un LISTADO FILTRADO (`/empleados?sin_manager=true`), que no
    # es un par (entidad, id).
    #
    # La ruta la arma el backend a propósito: quien sabe a dónde lleva una alerta es quien la
    # genera. Un mapa `tipo → ruta` en el front sería otro espejo manual que puede divergir,
    # como `permisos.ts` vs `permisos.py`.
    href: Optional[str] = None


class HeadcountAreaResponse(BaseModel):
    area_id: str
    area: str
    total: int


class DistribItem(BaseModel):
    categoria: str
    total: int


class PersonaFecha(BaseModel):
    empleado: str
    fecha: str  # dd/mm del cumpleaños o aniversario


class KPIsExtraResponse(BaseModel):
    """KPIs agregados en Sesión 5 (23/26/27/28/30). Empty state: 0 / listas vacías, no rompe."""
    ausencias_activas_hoy: int
    ausentismo_mes_pct: float
    ausentismo_nota: str
    masa_salarial_actual: float
    masa_salarial_anterior: float
    masa_salarial_variacion_pct: float
    distribucion_seniority: List[DistribItem]
    distribucion_modalidad: List[DistribItem]
    cumpleanos_mes: List[PersonaFecha]
    aniversarios_mes: List[PersonaFecha]
    errores: List[str] = []  # KPIs que fallaron (fail-safe por KPI): quedaron en vacío/0


class DashboardResponse(BaseModel):
    kpis: KPIResponse
    headcount_por_area: List[HeadcountAreaResponse]
    alertas: List[AlertaResponse]
    kpis_extra: KPIsExtraResponse
