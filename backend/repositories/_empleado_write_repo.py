"""
Write path del repositorio de empleados (extraído: el repo estaba en 174 líneas contra un
límite de 100, el peor over-limit del backend).

Funciones libres que reciben los colaboradores — mismo molde que _empleados_write.py en la
capa de services y que _vacaciones_write.py. EmpleadoRepo las delega en una línea, así que
los call sites no cambian. La lógica se movió VERBATIM: payloads, el manejo de manager_id
nulo y los mensajes de error son idénticos a antes.

`actualizar` recibe `find_by_id` como parámetro porque su rama de patch vacío devuelve el
registro tal como está. Sin eso habría que duplicar esa lectura acá — o, peor, cambiarla por
un `None` y romper en silencio el update que no toca ningún campo.
"""
from collections.abc import Callable
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._empleado_row import TABLE, row, with_empresa
from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from utils.errors import AppError
from utils.logger import logger


def guardar(data: EmpleadoCreate, empresa_id: UUID) -> EmpleadoResponse:
    """Inserta un nuevo empleado en la empresa indicada y devuelve el registro creado."""
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    payload["area_id"] = str(data.area_id)
    payload["empresa_id"] = str(empresa_id)
    payload["fecha_ingreso"] = str(data.fecha_ingreso)
    if data.fecha_nacimiento:
        payload["fecha_nacimiento"] = str(data.fecha_nacimiento)
    if data.manager_id:
        payload["manager_id"] = str(data.manager_id)
    payload["estado"] = "activo"

    result = supabase_admin.table(TABLE).insert(payload).execute()
    if not result.data:
        logger.error("Supabase insert vacío en empleados")
        raise AppError("Error al crear empleado", "DB_ERROR", 500)
    return row(result.data[0])


def actualizar(
    id: str, data: EmpleadoUpdate, empresa_id: Optional[UUID],
    find_by_id: Callable[[str, Optional[UUID]], Optional[EmpleadoResponse]],
) -> Optional[EmpleadoResponse]:
    """Actualiza solo los campos no-None y devuelve el registro actualizado. Si empresa_id se provee, restringe el WHERE."""
    patch = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    # manager_id: null explícito = limpiar (exclude_none lo descarta; exclude_unset lo detecta).
    if "manager_id" in data.model_dump(exclude_unset=True):
        patch["manager_id"] = str(data.manager_id) if data.manager_id else None
    if not patch:
        return find_by_id(id, empresa_id)
    if "area_id" in patch:
        patch["area_id"] = str(patch["area_id"])
    if "fecha_ingreso" in patch:
        patch["fecha_ingreso"] = str(patch["fecha_ingreso"])
    if "fecha_nacimiento" in patch and patch["fecha_nacimiento"]:
        patch["fecha_nacimiento"] = str(patch["fecha_nacimiento"])

    stmt = with_empresa(supabase_admin.table(TABLE).update(patch).eq("id", id), empresa_id)
    result = stmt.execute()
    if not result.data:
        return None
    return row(result.data[0])


def baja_logica(id: str, empresa_id: Optional[UUID] = None) -> bool:
    """Marca el empleado como baja sin eliminar el registro. Si empresa_id se provee, restringe el WHERE."""
    stmt = with_empresa(supabase_admin.table(TABLE).update({"estado": "baja"}).eq("id", id), empresa_id)
    return bool(stmt.execute().data)


def dar_de_baja(empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None) -> bool:
    """Da de baja a un empleado: setea estado='baja' y fecha_egreso en un solo UPDATE.

    Usado al iniciar un offboarding. A diferencia de baja_logica, registra también
    la fecha de egreso: la baja es lógica (estado + fecha_egreso), nunca física — así el histórico
    de costos sigue incluyendo a los que ya no están.

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
