"""Schemas del botón "resolver pendientes" de superiores (migración 086)."""
from typing import List

from pydantic import BaseModel


class SuperiorPendienteItem(BaseModel):
    """Un empleado cuyo superior el import no pudo resolver.

    `superior` es el texto CRUDO del CSV: es lo que un humano necesita ver para entender a quién
    apuntaba la fila. `empleado` se resuelve por embed contra `empleados`, no se guarda duplicado
    (si al empleado lo renombran, el pendiente muestra el nombre nuevo)."""
    empleado_id: str
    empleado: str
    superior: str
    motivo: str


class SuperioresPendientesListResponse(BaseModel):
    items: List[SuperiorPendienteItem]
    total: int


class ResolucionPendientesResult(BaseModel):
    """Resultado de un reintento. `pendientes` son los que SIGUEN sin resolverse, con el motivo
    de AHORA — que puede no ser el del import (dar de alta a un homónimo convierte un
    'no hay ningún empleado con ese nombre' en un 'hay 2, elegí cuál')."""
    resueltos: int
    pendientes: List[SuperiorPendienteItem]
