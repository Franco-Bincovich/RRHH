"""
Alta y movimiento de candidatos de una vacante (extraído para hacerle lugar al service).

Funciones libres que reciben los colaboradores (repo de vacantes, repo de candidatos, cv) —
mismo molde que _ausencias_write.crear(repo, audit, ...). VacanteService las delega en una
línea. La lógica se movió VERBATIM: la herencia de empresa desde la vacante, el orden
validar-CV → crear → subir, y el criterio de no revertir el candidato si Storage falla son
idénticos a antes de la división.

`_ETAPAS` se muda con `mover`: es el vocabulario de esa función y no lo usa nadie más.
"""
from typing import Optional
from uuid import UUID

from schemas.candidato import CandidatoCreate, CandidatoResponse
from utils.errors import AppError
from utils.logger import logger

_ETAPAS = {"postulado", "assessment", "entrevista_rrhh", "entrevista_tecnica", "oferta"}


def agregar(
    repo, candidato_repo, cv, audit, vacante_id: UUID, data: CandidatoCreate,
    empresa_id: Optional[UUID] = None, cv_content: Optional[bytes] = None,
    cv_filename: Optional[str] = None, cv_content_type: Optional[str] = None,
    usuario_id: Optional[str] = None,
) -> CandidatoResponse:
    """Agrega un candidato (etapa 'postulado') con CV opcional; empresa_id se hereda de la vacante.
    CV validado antes de crear; si la subida falla tras crear, conserva el candidato sin CV (no revert).
    Raises: VACANTE_NOT_FOUND (404), INVALID_CV_FORMAT (400), CV_TOO_LARGE (413).

    Emite DOS eventos, no uno: el alta y —solo si el CV llegó a persistirse— el adjunto. Son dos
    mutaciones que fallan por separado (Storage puede caerse después del INSERT), y un evento
    único mentiría en ese camino: diría que se adjuntó un CV que no está."""
    vacante = repo.find_by_id(str(vacante_id), empresa_id)
    if not vacante:
        raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
    if cv_content is not None:
        cv.validar(cv_content, cv_filename or "cv", cv_content_type)
    candidato = candidato_repo.save_candidato(str(vacante_id), data, vacante.empresa_id or "")
    audit.registrar(
        usuario_id=usuario_id, entidad="candidato", registro_id=candidato.id, accion="INSERT",
        evento="alta_candidato", empresa_id=candidato.empresa_id, datos_anteriores=None,
        datos_nuevos={"nombre": f"{candidato.nombre} {candidato.apellido}", "email": candidato.email,
                      "vacante_id": candidato.vacante_id, "etapa_pipeline": candidato.etapa_pipeline},
    )
    if cv_content is not None:
        try:
            path = cv.subir(vacante.empresa_id, candidato.id, cv_content, cv_filename or "cv", cv_content_type)
            candidato_repo.set_cv(candidato.id, path)
            candidato.cv_storage_path = path
            # 🔴 `set_cv` devuelve None: no hay fila de la cual sacar la empresa. Sale del
            # candidato QUE YA TENEMOS, que la heredó de la vacante — nunca del header.
            audit.registrar(
                usuario_id=usuario_id, entidad="candidato", registro_id=candidato.id, accion="UPDATE",
                evento="adjuntar_cv_candidato", empresa_id=candidato.empresa_id,
                datos_anteriores=None, datos_nuevos={"cv_storage_path": path},
            )
        except Exception as exc:  # storage falló: no perder el candidato ya creado
            logger.error("CV no adjuntado tras crear candidato", extra={"candidato_id": candidato.id, "error": str(exc)})
    logger.info("Candidato agregado", extra={"vacante_id": str(vacante_id), "candidato_id": candidato.id})
    return candidato


def mover(candidato_repo, audit, candidato_id: UUID, etapa: str, empresa_id: Optional[UUID] = None,
          usuario_id: Optional[str] = None) -> CandidatoResponse:
    """Mueve un candidato de etapa. Raises ETAPA_INVALIDA (400), CANDIDATO_NOT_FOUND (404).

    🔴 Lee el candidato ANTES de mover. `update_etapa_candidato` devuelve la fila YA actualizada,
    así que sin esta lectura la etapa anterior no existe en ningún lado y el evento solo podría
    decir "cambió" — que no permite auditar nada. El 404 también se adelanta acá; es el mismo
    code y el mismo mensaje que el de abajo, así que no cambia lo que ve el cliente."""
    if etapa not in _ETAPAS:
        raise AppError(f"Etapa inválida. Permitidas: {', '.join(_ETAPAS)}", "ETAPA_INVALIDA", 400)
    previo = candidato_repo.find_by_id(str(candidato_id), empresa_id)
    if not previo:
        raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
    candidato = candidato_repo.update_etapa_candidato(str(candidato_id), etapa, empresa_id)
    if not candidato:
        raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
    audit.registrar(
        usuario_id=usuario_id, entidad="candidato", registro_id=candidato.id, accion="UPDATE",
        evento="cambio_etapa_candidato", empresa_id=candidato.empresa_id,
        datos_anteriores={"etapa_pipeline": previo.etapa_pipeline},
        datos_nuevos={"etapa_pipeline": candidato.etapa_pipeline},
    )
    logger.info("Candidato movido", extra={"candidato_id": str(candidato_id), "etapa": etapa})
    return candidato
