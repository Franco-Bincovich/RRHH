"""
Las dos ESCRITURAS sobre un candidato suelto: darlo de baja y asignarle una vacante.

Extraído de `candidato_service.py`, que estaba en **150/150 exacto** y no admitía el filtro por
clasificación del screening. El corte es por naturaleza de la operación —lecturas y export de un
lado, escrituras del otro—, no por tamaño: son las dos únicas que auditan y las dos únicas que
tocan Storage.

El movimiento fue VERBATIM: los cuerpos, sus comentarios y los mensajes de error son idénticos a
los que estaban embebidos en `candidato_service.py`. Molde: `_empleados_write.py`.
"""
from typing import Optional
from uuid import UUID

from integrations import storage
from schemas.vacante import CandidatoResponse
from utils.errors import AppError
from utils.logger import logger



def borrar(candidato_repo, audit, candidato_id: str, empresa_id: Optional[UUID] = None,
           usuario_id: Optional[str] = None) -> None:
    """Elimina un candidato HUÉRFANO (sin búsqueda) y su CV del Storage. Solo huérfanos: los de
    búsqueda viva se gestionan desde la vacante. Si el remove físico del CV falla → log y sigue
    con el borrado de la fila. Raises CANDIDATO_NOT_FOUND (404), CANDIDATO_ACTIVO (400)."""
    cand = candidato_repo.find_by_id(candidato_id, empresa_id)
    if not cand:
        raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
    if cand.vacante_id is not None:
        raise AppError("No se puede eliminar un candidato de una búsqueda activa", "CANDIDATO_ACTIVO", 400)
    if cand.cv_storage_path:  # guard: nunca remove sobre key vacía; usa la key de la DB tal cual
        try:
            storage.borrar(storage.CVS, [cand.cv_storage_path])
        except Exception as exc:  # storage falló: se conserva el flujo, objeto huérfano en Storage
            logger.error("Storage remove falló (CV)", extra={"candidato_id": candidato_id, "error": str(exc)})
    candidato_repo.delete(candidato_id, empresa_id)
    # 🔴 La empresa del evento sale del CANDIDATO (leído arriba), no del header: auditar es
    # una ACCIÓN y la empresa sale de la entidad afectada. Con el header, una baja hecha en
    # modo consolidado (empresa_id=None) grababa el evento sin empresa aunque el candidato
    # sí la tuviera — ya pasó una vez en producción. Ver "Vista vs Acción" en CLAUDE.md.
    audit.registrar(
        usuario_id=usuario_id, entidad="candidato", registro_id=candidato_id, accion="DELETE",
        evento="baja_candidato", empresa_id=cand.empresa_id,
        datos_anteriores={"nombre": f"{cand.nombre} {cand.apellido}", "email": cand.email}, datos_nuevos=None,
    )
    logger.info("Candidato eliminado", extra={"candidato_id": candidato_id})


def asignar_vacante(candidato_repo, vacante_repo, audit, candidato_id: str, vacante_id: str,
                    empresa_id: Optional[UUID] = None,
                    usuario_id: Optional[str] = None) -> CandidatoResponse:
    """Asigna una vacante a un candidato huérfano.

    🔴 SON DOS COMPROBACIONES DISTINTAS Y LAS DOS HACEN FALTA: que el CANDIDATO sea
    alcanzable desde el header (el `.eq` del repo), y que la VACANTE sea **de la empresa del
    CANDIDATO** — esto último NO se puede delegar al header: en modo consolidado vale None y
    no restringe nada, así que sin el chequeo se podría mover un candidato de Karstec a una
    búsqueda de Dosuba. Cada fallo sale por el 404 de su propio recurso, sin distinguir "no
    existe" de "es de otra empresa".

    Raises: CANDIDATO_NOT_FOUND · VACANTE_NOT_FOUND (404) · CANDIDATO_YA_ASIGNADO (409)."""
    cand = candidato_repo.find_by_id(candidato_id, empresa_id)
    if not cand:
        raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
    if cand.vacante_id:  # reasignar a alguien que ya está en un pipeline le borra su etapa
        raise AppError("El candidato ya está asignado a una búsqueda", "CANDIDATO_YA_ASIGNADO", 409)
    vacante = vacante_repo.find_by_id(vacante_id, UUID(cand.empresa_id) if cand.empresa_id else None)
    if not vacante:
        raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
    asignado = candidato_repo.asignar_vacante(candidato_id, vacante_id, empresa_id)
    if not asignado:
        raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
    audit.registrar(
        usuario_id=usuario_id, entidad="candidato", registro_id=candidato_id, accion="UPDATE",
        evento="asignacion_vacante_candidato", empresa_id=cand.empresa_id,
        datos_anteriores={"vacante_id": None}, datos_nuevos={"vacante_id": vacante_id})
    logger.info("Candidato asignado a una vacante", extra={"candidato_id": candidato_id})
    return asignado
