"""
Write path del repositorio de vacaciones (extraído: el repo estaba en 100/100, su límite
exacto, y las columnas `periodo`/`liquidada` no entraban sin dividir primero).

Funciones libres que reciben los colaboradores — mismo molde que `_empleado_write_repo.py`
en esta capa y que `_vacaciones_write.py` en services. `VacacionesRepo` las delega en una
línea, así que los call sites no cambian. La lógica se movió VERBATIM: el payload, el
chequeo de insert vacío y los mensajes de error son idénticos a antes.

Las dos reciben `find_by_id` como parámetro porque devuelven el registro ENRIQUECIDO
(empresa_nombre, empleado_nombre, area_id, area_nombre), que el insert/update de Supabase no
trae — los resuelve `build_responses` del repo de lectura. Es el mismo motivo por el que
`_empleado_write_repo.actualizar` recibe el suyo: sin eso habría que duplicar esa lectura acá.
"""
from datetime import date
from typing import Callable, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._vacaciones_utils import TABLE
from schemas.vacaciones import SolicitudVacacionesResponse
from utils.errors import AppError
from utils.logger import logger


def guardar(
    empleado_id: str, empresa_id: str, fecha_desde: date, fecha_hasta: date,
    dias: int, tipo: str, comentario: Optional[str],
    find_by_id: Callable[..., Optional[SolicitudVacacionesResponse]],
    periodo: Optional[int] = None, dias_liquidados: int = 0,
) -> SolicitudVacacionesResponse:
    """Inserta una solicitud y devuelve el registro enriquecido.

    `periodo` va aunque sea None: es el año DEVENGADO y no se deriva de fecha_desde (una
    licencia tomada en 2026 puede ser del período 2025). Ver migrations/083.
    """
    payload = {
        "empleado_id": empleado_id, "empresa_id": empresa_id,
        "fecha_desde": str(fecha_desde), "fecha_hasta": str(fecha_hasta),
        "dias": dias, "tipo": tipo, "comentario": comentario, "cancelada": False,
        "periodo": periodo, "dias_liquidados": dias_liquidados,
    }
    res = supabase_admin.table(TABLE).insert(payload).execute()
    if not res.data:
        logger.error("Supabase insert vacío en solicitudes_vacaciones")
        raise AppError("Error al registrar vacaciones", "DB_ERROR", 500)
    return find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]


def actualizar(
    id: str, patch: dict, empresa_id: Optional[UUID],
    find_by_id: Callable[..., Optional[SolicitudVacacionesResponse]],
) -> Optional[SolicitudVacacionesResponse]:
    """Actualiza los campos provistos con la empresa EN EL WHERE (Forma A). Patch vacío → la fila."""
    if not patch:
        return find_by_id(id, empresa_id)
    q = supabase_admin.table(TABLE).update(patch).eq("id", id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    return find_by_id(id, empresa_id) if res.data else None


def cancelar(
    id: str, empresa_id: Optional[UUID],
    find_by_id: Callable[..., Optional[SolicitudVacacionesResponse]],
) -> Optional[SolicitudVacacionesResponse]:
    """Setea cancelada=True. Si empresa_id se provee, restringe el WHERE por empresa."""
    q = supabase_admin.table(TABLE).update({"cancelada": True}).eq("id", id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    return find_by_id(id, empresa_id) if res.data else None
