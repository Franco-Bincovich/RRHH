"""
Schemas de la vista interna "Horas por cliente" (solo RRHH).

Archivo propio y no `schemas/horas.py`: ahí viven los schemas del REGISTRO (una fila de
`horas_proyecto`) y acá los de una VISTA AGREGADA, que es otra forma — árbol con totales, no
filas. Mezclarlos haría que agregar una métrica a la pantalla toque el schema del registro.
"""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from schemas.horas import HoraResponse, Modalidad


class KPIsHoras(BaseModel):
    """Los cuatro del encabezado. Se calculan sobre el MISMO conjunto que la tabla de abajo."""
    horas_totales: float
    # Clientes REALES: el grupo "Sin cliente" (las cargas del camino viejo) no suma acá.
    clientes_con_carga: int
    empleados_que_cargaron: int
    registros: int


class LineaEmpleado(BaseModel):
    """Una línea del detalle de un cliente: empleado + proyecto + tarea + modalidad, agregados."""
    empleado_id: Optional[UUID] = None
    empleado_nombre: Optional[str] = None
    proyecto_texto: Optional[str] = None
    tarea_texto: Optional[str] = None
    modalidad: Optional[Modalidad] = None
    horas: float
    registros: int


class ClienteConHoras(BaseModel):
    """Un cliente colapsable. `cliente_id` es None en el grupo "Sin cliente"."""
    cliente_id: Optional[UUID] = None
    cliente_nombre: str
    horas: float
    registros: int
    lineas: List[LineaEmpleado]


class HorasPorClienteResponse(BaseModel):
    mes: int
    anio: int
    kpis: KPIsHoras
    clientes: List[ClienteConHoras]


class DetalleEmpleadoResponse(BaseModel):
    """El "ver detalle": las cargas DÍA POR DÍA de un empleado en el período.

    Devuelve `HoraResponse` completo —con el `id`— porque la pantalla necesita el id para poder
    BORRAR. Editar no está: `HorasService` declara los registros inmutables por decisión escrita
    (hay delete y no hay update), y revocarla es una decisión de producto, no una feature.
    """
    items: List[HoraResponse]
    total_horas: float
