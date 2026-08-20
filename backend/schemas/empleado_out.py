"""
Schemas de SALIDA del módulo de empleados: lo que el backend devuelve.

Separado de schemas/empleado.py, que estaba en 199/200 y no admitía los campos nuevos del
domicilio desglosado. El corte es entrada/actualización (allá) vs salida (acá), que es la
línea natural: los de entrada validan lo que llega, estos describen lo que sale.

⚠️ `schemas/empleado.py` los RE-EXPORTA, así que `from schemas.empleado import EmpleadoResponse`
sigue funcionando en los 20+ call sites (13 de ellos tests). Importar de acá o de allá es
equivalente; lo nuevo conviene que importe de acá.
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel

from schemas._provincias import Provincia


class EmpleadoResponse(BaseModel):
    id: str
    nombre: str
    apellido: str
    email_corporativo: Optional[str] = None  # nullable: import de nómina permite crear sin email
    empresa_id: Optional[str] = None
    empresa_nombre: Optional[str] = None
    area_id: str
    area_nombre: Optional[str] = None
    roles: List[str]                  # multi-valor; roles[0] es el principal
    modalidad_trabajo: str
    tipo_contrato: str
    fecha_ingreso: date
    # 🔴 EL DATO DE LA BAJA, y hasta el 20/8/2026 la columna existía y NO SALÍA POR LA API.
    # La escribe `_empleado_write_repo.dar_de_baja` (offboarding e import de nómina) desde
    # siempre, la leen tres agregados —`bajas_mes` del dashboard, `generate_headcount` y el
    # listado nominal de `_reporte_movimientos`—, y ningún consumidor de `EmpleadoResponse`
    # podía verla: ni la ficha, ni el listado, ni el export. Una pantalla de Bajas no podía
    # decir CUÁNDO se fue cada persona teniendo el dato guardado.
    #
    # `Optional` porque la columna es nullable y lo normal es que esté vacía: la trae cargada
    # solo quien está de baja. NO es un campo que el alta ni el PUT escriban — el único camino
    # que la setea es `dar_de_baja`, junto con `estado='baja'`, en un solo UPDATE.
    fecha_egreso: Optional[date] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    dni: Optional[str] = None
    cuil: Optional[str] = None
    legajo: Optional[str] = None
    manager_id: Optional[str] = None      # superior inmediato (id)
    manager_nombre: Optional[str] = None  # "Apellido, Nombre" resuelto por join
    cargo: Optional[str] = None       # DEPRECADO (se dropea en S6)
    rol: Optional[str] = None         # DEPRECADO (se dropea en S6)
    estado: str
    # 🔴 Optional DESDE LA MIGRACIÓN 090, y el orden de deploy NO se puede invertir: este
    # Optional va ANTES de correr la migración. Era `int = 14` (no opcional), así que un NULL
    # contra este tipo levanta ValidationError → 500 del handler global, y NO solo en
    # vacaciones: este schema es el de salida de TODA lectura de empleado (listado, ficha,
    # export, dashboard). Con el código nuevo desplegado el NULL es un valor esperado.
    # NULL = se aplica la regla por antigüedad (config/reglas_vacaciones.py) · un entero =
    # override permanente de esa persona, que gana sobre la regla.
    dias_vacaciones_asignados: Optional[int] = None
    # Legajo ampliado (A1.1, migración 060) — todos opcionales.
    email_personal: Optional[str] = None
    tipo_documento: Optional[str] = None
    sexo: Optional[str] = None
    telefono_alternativo: Optional[str] = None
    domicilio: Optional[str] = None
    estudios: Optional[str] = None
    ubicacion: Optional[str] = None
    turno: Optional[str] = None
    horas_contrato: Optional[int] = None
    organismo: Optional[str] = None
    gerencia: Optional[str] = None
    sector: Optional[str] = None
    seniority: Optional[str] = None
    perfil: Optional[str] = None
    categoria: Optional[str] = None
    referido: Optional[str] = None
    es_lider: bool = False
    # Domicilio desglosado (C4, migración 081). `domicilio` de arriba se conserva como texto
    # libre: es el destino de lo que no encaje acá y la referencia para completar estos.
    domicilio_calle: Optional[str] = None
    domicilio_numero: Optional[str] = None       # texto: existen "S/N", "1234 bis", "KM 4"
    domicilio_piso_depto: Optional[str] = None
    domicilio_localidad: Optional[str] = None
    domicilio_provincia: Optional[Provincia] = None  # lista cerrada → fuera de la lista = 422
    domicilio_cp: Optional[str] = None
    created_at: datetime


class EmpleadoListResponse(BaseModel):
    items: List[EmpleadoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmpleadoSeleccionable(BaseModel):
    """Proyección liviana de un empleado para poblar selects (ej. superior inmediato)."""
    id: str
    nombre: str
    apellido: str
