"""
Write path del módulo de Ausencias (extraído para mantener el service ≤150 líneas).

Funciones libres que reciben los colaboradores (repo, audit, periodos, ownership) —
mismo molde que _vacaciones_saldo.calcular_saldo(repo, ...). El service las delega en
una línea. La lógica se movió VERBATIM desde AusenciasService: ownership, bloqueo por
período y auditoría son idénticos a antes de la división.
"""
from typing import Optional
from uuid import UUID

from schemas.ausencias import AusenciaCreate, AusenciaResponse, AusenciaUpdate
from services._audit_payloads import (
    payload_alta_ausencia, payload_baja_ausencia, payload_update_ausencia,
)
from services._periodo_utils import verificar_periodo_abierto
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError
from utils.logger import logger


def crear(repo, audit, periodos, ownership, data: AusenciaCreate, created_by: str, rol: Optional[str] = None) -> AusenciaResponse:
    """
    Registra una ausencia. empresa_id se resuelve del empleado.

    Ownership: se valida ANTES de resolver la empresa (403 uniforme para un mando que
    intenta crear a nombre de un empleado que no es su subordinado).

    Args:
        data: Campos del formulario (sin empresa_id — se hereda del empleado).
        created_by: ID del operador que registra (trazabilidad y sujeto del ownership).
        rol: Rol del operador (para el chequeo de ownership).

    Raises:
        AppError: OWNERSHIP_DENIED (403) si el rol no puede gestionar a ese empleado.
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe.
    """
    if not puede_gestionar_empleado(created_by, rol, data.empleado_id, ownership):
        raise AppError("No autorizado para gestionar este colaborador", "OWNERSHIP_DENIED", 403)
    empresa_id = repo.find_empresa_for_empleado(str(data.empleado_id))
    if not empresa_id:
        raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)
    verificar_periodo_abierto(empresa_id, "ausencias", rol, desde=data.fecha_desde, hasta=data.fecha_hasta, repo=periodos)
    dias = (data.fecha_hasta - data.fecha_desde).days + 1
    row = repo.save(
        str(data.empleado_id), empresa_id, str(data.tipo_id),
        data.fecha_desde, data.fecha_hasta, dias, data.justificada, data.motivo,
    )
    audit.registrar(**payload_alta_ausencia(row, created_by, row.empresa_id))
    logger.info("Ausencia registrada", extra={"ausencia_id": row.id, "empleado_id": str(data.empleado_id), "created_by": created_by})
    return row


def actualizar(repo, audit, periodos, ownership, id: UUID, data: AusenciaUpdate, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> AusenciaResponse:
    """
    Actualiza una ausencia. Recalcula dias si cambian las fechas.
    Registra el evento de auditoría con el diff antes/después (usuario_id = operador).

    Ownership: un registro ajeno a un mando responde 404 (igual que inexistente).

    Raises:
        AppError: AUSENCIA_NOT_FOUND (404) si no existe o no es gestionable por el rol.
    """
    existing = repo.find_by_id(str(id), empresa_id)
    if not existing or not puede_gestionar_empleado(usuario_id, rol, existing.empleado_id, ownership):
        raise AppError("Ausencia no encontrada", "AUSENCIA_NOT_FOUND", 404)
    # Bloqueo por período: no se puede sacar de un período cerrado (fechas viejas) ni meter en uno (nuevas).
    verificar_periodo_abierto(existing.empresa_id, "ausencias", rol, desde=existing.fecha_desde, hasta=existing.fecha_hasta, repo=periodos)
    verificar_periodo_abierto(existing.empresa_id, "ausencias", rol, desde=data.fecha_desde or existing.fecha_desde, hasta=data.fecha_hasta or existing.fecha_hasta, repo=periodos)
    payload: dict = {}
    if data.tipo_id is not None:
        payload["tipo_id"] = str(data.tipo_id)
    if data.fecha_desde is not None:
        payload["fecha_desde"] = str(data.fecha_desde)
    if data.fecha_hasta is not None:
        payload["fecha_hasta"] = str(data.fecha_hasta)
    if data.fecha_desde is not None or data.fecha_hasta is not None:
        fd = data.fecha_desde or existing.fecha_desde
        fh = data.fecha_hasta or existing.fecha_hasta
        payload["dias"] = (fh - fd).days + 1
    if data.justificada is not None:
        payload["justificada"] = data.justificada
    if data.motivo is not None:
        payload["motivo"] = data.motivo or None
    updated = repo.update(str(id), empresa_id, payload)
    if not updated:
        raise AppError("Ausencia no encontrada", "AUSENCIA_NOT_FOUND", 404)
    audit.registrar(**payload_update_ausencia(existing, updated, usuario_id, existing.empresa_id))
    logger.info("Ausencia actualizada", extra={"ausencia_id": str(id)})
    return updated


def eliminar(repo, audit, periodos, ownership, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> None:
    """
    Elimina una ausencia permanentemente.
    Lee la fila ANTES de borrar: para el ownership, el 404 de inexistente y para el audit.

    Ownership: un registro ajeno a un mando responde 404 (igual que inexistente) y NO se borra.

    Raises:
        AppError: AUSENCIA_NOT_FOUND (404) si no existe o no es gestionable por el rol.
    """
    prior = repo.find_by_id(str(id), empresa_id)
    if not prior or not puede_gestionar_empleado(usuario_id, rol, prior.empleado_id, ownership):
        raise AppError("Ausencia no encontrada", "AUSENCIA_NOT_FOUND", 404)
    verificar_periodo_abierto(prior.empresa_id, "ausencias", rol, desde=prior.fecha_desde, hasta=prior.fecha_hasta, repo=periodos)
    if not repo.delete(str(id), empresa_id):
        raise AppError("Ausencia no encontrada", "AUSENCIA_NOT_FOUND", 404)
    audit.registrar(**payload_baja_ausencia(prior, usuario_id, prior.empresa_id))
    logger.info("Ausencia eliminada", extra={"ausencia_id": str(id)})
