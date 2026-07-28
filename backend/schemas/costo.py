"""
Schemas Pydantic para el módulo de Costos de Personal.
NominaCreate → NominaResponse · PresupuestoCreate → PresupuestoResponse · DashboardCostosResponse
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class NominaCreate(BaseModel):
    empleado_id: str
    mes: int = Field(..., ge=1, le=12)
    anio: int = Field(..., ge=2000, le=2100)
    monto_bruto: float = Field(..., ge=0)
    monto_neto: float = Field(..., ge=0)


class NominaResponse(BaseModel):
    id: str
    empleado_id: str
    empresa_id: Optional[str] = None
    empresa_nombre: Optional[str] = None
    empleado_nombre: str
    area_nombre: str
    mes: int
    anio: int
    monto_bruto: float
    monto_neto: float
    total: float


class HistorialSalarialItem(BaseModel):
    """Un período de la serie salarial de un empleado.

    QUÉ MONTOS LLEVA, Y POR QUÉ NO `total`. `costos_nomina` guarda cuatro montos, pero solo
    uno se carga de verdad:
      · `salario_bruto`  → lo escriben los dos caminos (carga manual e import). Es el sueldo.
      · `cargas_sociales`→ también, y de ahí sale el neto (bruto − cargas): NO es una columna.
      · `bonos` / `otros_costos` → ninguno de los dos caminos los escribe nunca. Columnas
        muertas, siempre 0.
      · `total` → columna GENERADA (bruto + cargas + bonos + otros). Como bonos y otros son 0,
        hoy es bruto + cargas, o sea el costo para la empresa, NO lo que cobra la persona.
    En un legajo la pregunta es "cuánto gana", así que la serie muestra bruto y neto. Poner
    `total` al lado invitaría a leerlo como sueldo, que es lo que no es.
    """
    anio: int
    mes: int
    monto_bruto: float
    monto_neto: float


class PresupuestoCreate(BaseModel):
    area_id: str
    mes: int = Field(..., ge=1, le=12)
    anio: int = Field(..., ge=2000, le=2100)
    presupuesto: float = Field(..., ge=0)


class PresupuestoResponse(BaseModel):
    id: str
    area_id: str
    area_nombre: str
    mes: int
    anio: int
    presupuesto: float


class CostoArea(BaseModel):
    empresa_nombre: Optional[str] = None
    area_nombre: str
    empleados: int
    costo_mensual: float
    presupuesto: float


class EvolucionMes(BaseModel):
    mes: int
    anio: int
    total: float


class DashboardCostosResponse(BaseModel):
    total_nomina: float
    costo_promedio: float
    variacion_porcentual: Optional[float]
    costos_por_area: List[CostoArea]
    evolucion_mensual: List[EvolucionMes]
