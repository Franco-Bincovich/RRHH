"""
Write path de `vacantes`: alta, edición, cambio de estado, datos de LinkedIn y baja física.

SALIÓ DE `vacante_repo.py`, que estaba en 100/100 cuando le tocaba sumar la paginación del
listado. Es el mismo corte que ya tienen `_empleado_write_repo.py` y `_vacaciones_write_repo.py`:
el listado crece con cada filtro nuevo, las escrituras no se mueven, y juntos no entran.

🔑 LAS CINCO RECIBEN `find_by_id` COMO PARÁMETRO en vez de importarlo. Devuelven la fila
enriquecida con joins, y ésa la sabe armar el repo de lectura: importarlo desde acá crearía un
ciclo (el repo importa este módulo para delegar). Molde exacto: `_empleado_write_repo`.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.vacante import VacanteCreate, VacanteResponse, VacanteUpdate
from utils.errors import AppError
from utils.logger import logger

TABLE = "vacantes"


def guardar(data: VacanteCreate, find_by_id) -> VacanteResponse:
    """Inserta una vacante con estado='nueva' y devuelve el registro con joins."""
    payload = data.model_dump()
    payload["area_id"] = str(payload["area_id"])
    payload["empresa_id"] = str(payload["empresa_id"])
    payload["estado"] = "nueva"
    res = supabase_admin.table(TABLE).insert(payload).execute()
    if not res.data:
        logger.error("Supabase insert vacío en vacantes")
        raise AppError("Error al crear vacante", "DB_ERROR", 500)
    return find_by_id(str(res.data[0]["id"]))


def actualizar(id: str, data: VacanteUpdate, empresa_id: Optional[UUID], find_by_id) -> Optional[VacanteResponse]:
    """Actualiza campos no-None. Si empresa_id se provee, restringe el WHERE."""
    patch = data.model_dump(exclude_none=True)
    if not patch:
        return find_by_id(id, empresa_id)
    if "area_id" in patch:
        patch["area_id"] = str(patch["area_id"])
    q = supabase_admin.table(TABLE).update(patch).eq("id", id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    return find_by_id(id, empresa_id) if res.data else None


def cambiar_estado(id: str, estado: str, find_by_id) -> Optional[VacanteResponse]:
    """Actualiza el estado de una vacante (sin filtro de empresa — uso interno)."""
    res = supabase_admin.table(TABLE).update({"estado": estado}).eq("id", id).execute()
    return find_by_id(id) if res.data else None


def guardar_linkedin(id: str, post_id: str, url: str, email_contacto: str) -> None:
    """Guarda los datos de publicación en LinkedIn en la vacante."""
    supabase_admin.table(TABLE).update(
        {"linkedin_post_id": post_id, "linkedin_url": url, "email_contacto": email_contacto}
    ).eq("id", id).execute()


def borrar(id: str, empresa_id: Optional[UUID] = None) -> None:
    """Borra FÍSICAMENTE la fila de la vacante (filtra por empresa si se provee).
    Los candidatos sobreviven por la FK ON DELETE SET NULL (migración 071)."""
    q = supabase_admin.table(TABLE).delete().eq("id", id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    q.execute()
