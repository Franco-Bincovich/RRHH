"""
Bajas de empleado (soft delete) — extraído de `_empleado_write_repo.py`.

POR QUÉ SE PARTIÓ ACÁ Y NO EN OTRO LADO: `_empleado_write_repo` llegó a 96/100 y el soporte
de null explícito para `dias_vacaciones_asignados` (migración 085) no entraba. De las cuatro
funciones que tenía, estas dos son las únicas que no arman un patch a partir de un schema
Pydantic: escriben un dict fijo. El corte separa "traducir lo que mandó el usuario" de
"marcar la baja", que además es la frontera por la que crecen: las altas/ediciones ganan
campos con cada migración de legajo, las bajas no cambiaron desde la 001.

Mismo molde que el resto del write path: funciones libres, `EmpleadoRepo` las delega en una
línea, los call sites no cambian. La lógica se movió VERBATIM.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._empleado_row import TABLE, with_empresa


def baja_logica(id: str, empresa_id: Optional[UUID] = None) -> bool:
    """Marca el empleado como baja sin eliminar el registro. Si empresa_id se provee, restringe el WHERE."""
    stmt = with_empresa(supabase_admin.table(TABLE).update({"estado": "baja"}).eq("id", id), empresa_id)
    return bool(stmt.execute().data)


def dar_de_baja(empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None) -> bool:
    """Da de baja a un empleado: setea estado='baja' y fecha_egreso en un solo UPDATE.

    Usado al iniciar un offboarding. A diferencia de baja_logica, registra también
    la fecha de egreso, como exige MODELO_DATOS.md (baja = estado + fecha_egreso).

    Args:
        empleado_id: UUID (str) del empleado a dar de baja.
        fecha_egreso: fecha de egreso a registrar.
        empresa_id: si se provee, restringe el WHERE a esa empresa.

    Returns:
        True si se actualizó alguna fila; False si el empleado no existe o no pertenece a la empresa.
    """
    stmt = with_empresa(
        supabase_admin.table(TABLE)
        .update({"estado": "baja", "fecha_egreso": str(fecha_egreso)})
        .eq("id", empleado_id),
        empresa_id,
    )
    return bool(stmt.execute().data)
