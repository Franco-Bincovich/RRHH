"""
Schemas Pydantic para el módulo de importación masiva de NÓMINA de sueldos (costos_nomina).
El import de empleados (roster) vive en schemas/importacion_nomina_empleados.py.
"""
from typing import List
from uuid import UUID

from pydantic import BaseModel


# ─── Comunes ─────────────────────────────────────────────────────────────────

class FilaError(BaseModel):
    fila: int
    campo: str
    error: str


class ConfirmarError(BaseModel):
    fila: int
    error: str


# ─── Nómina (sueldos → costos_nomina) ────────────────────────────────────────

class FilaNominaPreview(BaseModel):
    fila: int
    dni: str
    nombre_empleado: str   # resuelto via DNI→empleado en el preview
    # 🔴 Este campo VIAJA DE IDA Y DE VUELTA: sale en el preview y el cliente lo devuelve en el
    # confirmar. Tiparlo UUID no cambia el contrato de red —JSON lo lleva como string en las dos
    # direcciones, y el front reenvía las filas TAL CUAL las recibió, sin tocarlas— pero sí hace
    # que un id mal formado muera en el 422 del confirmar en vez de llegar a la query.
    empleado_id: UUID      # UUID del empleado, necesario para el confirmar
    anio: int
    mes: int
    salario_bruto: float
    neto: float
    es_actualizacion: bool = False  # True si ya existe nómina para (empleado_id, anio, mes)


class ImportacionNominaPreviewResponse(BaseModel):
    filas_validas: List[FilaNominaPreview]
    errores: List[FilaError]


class ImportacionNominaConfirmarRequest(BaseModel):
    # solo para trazabilidad; el empresa_id que se persiste se hereda del empleado en el repo
    empresa_id: UUID
    filas: List[FilaNominaPreview]


class ImportacionNominaConfirmarResponse(BaseModel):
    importados: int
    actualizados: int
    errores: List[ConfirmarError]
