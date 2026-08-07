"""
Borrado masivo de adjuntos por entidad (extraído para hacerle lugar al service).

Función libre que recibe los colaboradores (repo, audit, gate) — mismo molde que
_ausencias_write.crear(repo, audit, ...). AdjuntoService la delega en una línea. La lógica se
movió VERBATIM: el orden gate → remove físico → soft delete → auditoría, y el criterio de que un
fallo de Storage no deja la fila colgada, son idénticos a antes de la división.

El `gate` viaja como callable en vez de reimplementarse acá: el permiso de un adjunto depende de
su ENTIDAD, y esa resolución vive en el service junto con el mapeo _ENTIDAD_SECCION. Duplicarla
sería tener dos criterios de permiso sobre lo mismo.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services._audit_payloads_adjuntos import payload_baja_adjunto
from utils.logger import logger
from utils.permisos import Accion


def eliminar_todos(
    repo, audit, gate, entidad: str, entidad_id: str, empresa_id: Optional[UUID],
    rol: Optional[str], usuario_id: Optional[str],
) -> None:
    """Borra FÍSICAMENTE del Storage + soft-delete de TODOS los adjuntos activos de una entidad
    (al eliminar la entidad dueña, ej. vacante). Si el remove físico falla → log y sigue: nunca
    deja la fila colgada por un fallo de Storage. Raises FORBIDDEN (403)."""
    gate(rol, entidad, Accion.WRITE)
    for adj in repo.find_by_entidad(entidad, entidad_id, empresa_id):
        if adj.storage_path:  # guard: nunca remove sobre key vacía; usa la key de la DB tal cual
            try:
                supabase_admin.storage.from_(adj.bucket).remove([adj.storage_path])
            except Exception as exc:  # storage falló: se conserva el flujo, objeto huérfano
                logger.error("Storage remove falló (adjunto)", extra={"adjunto_id": adj.id, "error": str(exc)})
        repo.marcar_eliminado(adj.id)
        audit.registrar(**payload_baja_adjunto(adj, usuario_id))
