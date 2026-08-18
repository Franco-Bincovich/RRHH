"""
Schemas Pydantic de ENTRADA del módulo de empleados: EmpleadoBase → EmpleadoCreate →
EmpleadoUpdate.

Los de salida (EmpleadoResponse, EmpleadoListResponse, EmpleadoSeleccionable) viven en
schemas/empleado_out.py y se RE-EXPORTAN acá: `from schemas.empleado import EmpleadoResponse`
sigue andando en todos los call sites que ya existen.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from schemas._provincias import Provincia
# El vocabulario de estados (tipos y constantes) vive en un solo módulo, para que el espejo del
# CHECK exista una vez. Molde: `schemas/usuario.py`, que importa ROLES_VALIDOS de utils.permisos.
from utils.estados_empleado import EstadoAlta, EstadoEmpleado
from schemas.empleado_out import (
    EmpleadoListResponse,
    EmpleadoResponse,
    EmpleadoSeleccionable,
)

# Re-export: el corte de este módulo NO debe obligar a tocar los imports de nadie.
__all__ = [
    "EmpleadoBase", "EmpleadoCreate", "EmpleadoUpdate",
    "EmpleadoListResponse", "EmpleadoResponse", "EmpleadoSeleccionable",
]


def _normalizar_roles(v: object) -> object:
    """Normaliza la lista de roles: trimea, descarta vacíos y deduplica preservando orden.

    Exige al menos un rol no vacío (espejo del CHECK empleados_roles_no_vacio en DB).
    Se aplica en EmpleadoBase y EmpleadoUpdate. Mantiene el orden de carga: el primer
    elemento es el rol principal."""
    if not isinstance(v, list):
        raise ValueError("roles debe ser una lista de strings")
    limpio: List[str] = []
    for item in v:
        if not isinstance(item, str):
            raise ValueError("cada rol debe ser un string")
        texto = item.strip()
        if texto and texto not in limpio:
            limpio.append(texto)
    if not limpio:
        raise ValueError("Se requiere al menos un rol")
    return limpio


class EmpleadoBase(BaseModel):
    nombre: str
    apellido: str
    email_corporativo: str
    area_id: UUID
    roles: List[str]        # multi-valor; roles[0] es el principal (unifica cargo + rol)
    modalidad_trabajo: str  # presencial | remoto | hibrido (enum)
    tipo_contrato: str      # texto libre (migración 065; el CSV de nómina trae valores abiertos)
    fecha_ingreso: date
    cargo: Optional[str] = None  # DEPRECADO (se dropea en S6); lo migran S2/S5
    rol: Optional[str] = None    # DEPRECADO (se dropea en S6); lo migran S2/S5
    # Legajo ampliado (A1.1, migración 060) — todos opcionales, texto libre.
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

    @field_validator("roles")
    @classmethod
    def _validar_roles(cls, v: object) -> object:
        return _normalizar_roles(v)


class EmpleadoCreate(EmpleadoBase):
    empresa_id: UUID  # la empresa de pertenencia viaja en el body, no en el header
    # Default SOLO para altas que no traen modalidad (import de nómina: el CSV no la trae).
    # El alta manual siempre la envía desde el dropdown, así que este default no la afecta.
    modalidad_trabajo: str = "presencial"
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    dni: Optional[str] = None
    cuil: Optional[str] = None
    legajo: Optional[str] = None
    manager_id: Optional[UUID] = None  # superior inmediato (self-FK a empleados)
    dias_vacaciones_asignados: Optional[int] = None  # default 14 en DB si no se provee
    # Solo `activo` o `preingreso`, y el default del alta vive ACÁ (antes estaba hardcodeado en
    # `_empleado_write_repo.guardar`). El porqué de la lista corta, en `utils/estados_empleado`.
    estado: EstadoAlta = "activo"


class EmpleadoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email_corporativo: Optional[str] = None
    area_id: Optional[UUID] = None
    cargo: Optional[str] = None
    modalidad_trabajo: Optional[str] = None
    tipo_contrato: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    dni: Optional[str] = None
    cuil: Optional[str] = None
    legajo: Optional[str] = None
    manager_id: Optional[UUID] = None  # superior inmediato (self-FK a empleados)
    # Espejo del CHECK: los cinco valores. Tipado y no `str` para que un valor inválido salga
    # 422 en la frontera y no 500 desde Postgres. El porqué, en `utils/estados_empleado`.
    estado: Optional[EstadoEmpleado] = None
    roles: Optional[List[str]] = None  # si se provee, reemplaza la lista completa
    rol: Optional[str] = None          # DEPRECADO (se dropea en S6)
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
    es_lider: Optional[bool] = None
    # Domicilio desglosado (C4, migración 081). `domicilio` de arriba se conserva como texto
    # libre: es el destino de lo que no encaje acá y la referencia para completar estos.
    domicilio_calle: Optional[str] = None
    domicilio_numero: Optional[str] = None       # texto: existen "S/N", "1234 bis", "KM 4"
    domicilio_piso_depto: Optional[str] = None
    domicilio_localidad: Optional[str] = None
    domicilio_provincia: Optional[Provincia] = None  # lista cerrada → fuera de la lista = 422
    domicilio_cp: Optional[str] = None

    @field_validator("roles")
    @classmethod
    def _validar_roles(cls, v: object) -> object:
        return _normalizar_roles(v) if v is not None else None

    @field_validator("fecha_ingreso", "fecha_nacimiento", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        return None if v == "" else v

    @field_validator("dias_vacaciones_asignados", mode="before")
    @classmethod
    def coerce_dias(cls, v: object) -> object:
        """Convierte string numérico a int (el modal del frontend envía strings)."""
        if isinstance(v, str):
            return int(v) if v.strip() else None
        return v
