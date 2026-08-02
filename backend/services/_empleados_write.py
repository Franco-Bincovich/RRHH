"""
Write path del módulo de Empleados (extraído para mantener el service ≤150 líneas).

Funciones libres que reciben los colaboradores (repo, audit) — mismo molde que
_ausencias_write y _vacaciones_saldo. El service las delega en una línea. La lógica se movió
VERBATIM desde EmpleadoService: validaciones, auditoría y logs son idénticos a antes.
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from services._audit_payloads_rrhh import (
    payload_alta_empleado, payload_baja_empleado, payload_update_empleado,
)
from services._empleados_manager import ensure_manager_valido, ensure_no_ciclo_manager
from services._empleados_utils import (
    empleado_or_404, ensure_area_valida, ensure_legajo_unico,
)
from utils.errors import AppError
from utils.logger import logger


def crear(repo: EmpleadoRepo, audit, areas, data: EmpleadoCreate, created_by: str,
          empresa_id: UUID, *, areas_validadas: frozenset = frozenset(),
          auditar: bool = True) -> EmpleadoResponse:
    """
    Crea un nuevo empleado en el sistema y registra el evento de auditoría.

    Args:
        repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        areas: AreaRepo (o doble de test) — para validar que el área sea de la misma empresa.
        data: Datos del empleado a crear (validados por Pydantic).
        created_by: ID del usuario que realiza la operación (para trazabilidad y audit).
        empresa_id: UUID de la empresa a la que pertenecerá el empleado (obligatorio).
        areas_validadas: ids de área ya probados de `empresa_id` en esta operación — ver
            `ensure_area_valida`. Vacío (default) = validar contra la base, como siempre.
        auditar: False solo para el import de nómina, que consolida las altas en UN evento de
            lote (regla del repo: "al auditar una importación, un evento por lote"). El registro
            creado es su propia evidencia, y el evento de lote lleva la lista de ids. El default
            True deja el alta manual exactamente igual.

    Returns:
        EmpleadoResponse con los datos del empleado creado, incluyendo su ID generado.

    Raises:
        AppError: MANAGER_NOT_FOUND (404) si el superior no existe (puede ser de otra empresa).
        AppError: AREA_NOT_FOUND (404) si el área no es de la misma empresa.
    """
    ensure_legajo_unico(repo, data.legajo, empresa_id)
    ensure_area_valida(areas, data.area_id, empresa_id, areas_validadas)
    # Sin chequeo de ciclos: un empleado que aún no existe no está en la cadena de nadie. Vale
    # también para el import de nómina: los superiores NO se escriben en el alta, sino en una
    # segunda pasada por `update_empleado` (ver `_nomina_superiores`), que sí los chequea.
    ensure_manager_valido(repo, data.manager_id)
    empleado = repo.save(data, empresa_id)
    if auditar:
        audit.registrar(**payload_alta_empleado(empleado, created_by, empleado.empresa_id))
    logger.info("Empleado creado", extra={"empleado_id": empleado.id, "created_by": created_by, "empresa_id": str(empresa_id)})
    return empleado


def actualizar(repo: EmpleadoRepo, audit, areas, id: UUID, data: EmpleadoUpdate,
               empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, *,
               areas_validadas: frozenset = frozenset(),
               prior: Optional[EmpleadoResponse] = None) -> EmpleadoResponse:
    """
    Actualiza los datos de un empleado existente (actualización parcial).
    Lee el estado anterior (read-before) para registrar el diff de auditoría.

    Args:
        repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        areas: AreaRepo (o doble de test) — para validar que el área sea de la misma empresa.
        id: UUID del empleado a actualizar.
        data: Campos a actualizar — solo los no-None se aplican.
        empresa_id: Si se provee, el UPDATE solo afecta empleados de esa empresa.
        usuario_id: ID del operador (trazabilidad de audit).
        areas_validadas: ids de área ya probados de `empresa_id` — ver `ensure_area_valida`.
        prior: la fila ANTERIOR, si el caller ya la leyó en esta misma operación. El import de
            nómina la trae de `find_by_dni` (es la fila que usó para decidir alta vs. update),
            así que sin esto se lee dos veces la MISMA fila, una vez por CSV.
            🔴 Tiene que venir del MISMO select con joins que `find_by_id` — los dos usan el
            `SELECT` de `_empleado_row`, así que la forma coincide. Una fila con otra forma
            generaría un diff fantasma (campos de join en null), que es el bug que
            `sin_derivados` vino a cerrar. None (default) = leer, como siempre.

    Returns:
        EmpleadoResponse con los datos actualizados.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
        AppError: MANAGER_NOT_FOUND (404) si el superior no existe (puede ser de otra empresa).
        AppError: AREA_NOT_FOUND (404) si el área no es de la misma empresa.
    """
    ensure_legajo_unico(repo, data.legajo, empresa_id, str(id))
    # Las tres cortan solas si su campo es None (un update parcial no toca lo que no manda).
    ensure_area_valida(areas, data.area_id, empresa_id, areas_validadas)
    # Las dos de manager van SIN empresa_id a propósito: el superior puede ser de otra empresa
    # del grupo, y el recorrido de ciclos tiene que cruzarla para poder detectarlos. Ver los
    # docstrings de las dos en `_empleados_utils` antes de "restaurar" la barrera.
    ensure_manager_valido(repo, data.manager_id)
    ensure_no_ciclo_manager(repo, id, data.manager_id)
    if prior is None:
        prior = repo.find_by_id(str(id), empresa_id)
    empleado = empleado_or_404(repo.update(str(id), data, empresa_id))
    audit.registrar(**payload_update_empleado(prior, empleado, usuario_id, empleado.empresa_id))
    logger.info("Empleado actualizado", extra={"empleado_id": str(id)})
    return empleado


def desactivar(repo: EmpleadoRepo, audit, id: UUID, empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> bool:
    """
    Da de baja lógica al empleado (soft delete). No elimina el registro.
    Lee el estado anterior antes del soft-delete para registrar el evento de auditoría.

    Args:
        repo: EmpleadoRepo (o doble de test).
        audit: AuditService (o doble de test).
        id: UUID del empleado a desactivar.
        empresa_id: Si se provee, el soft-delete solo afecta empleados de esa empresa.
        usuario_id: ID del operador (trazabilidad de audit).

    Returns:
        True si la operación fue exitosa.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
    """
    prior = repo.find_by_id(str(id), empresa_id)
    if not repo.soft_delete(str(id), empresa_id):
        raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
    if prior:
        audit.registrar(**payload_baja_empleado(prior, usuario_id, prior.empresa_id))
    logger.info("Empleado dado de baja", extra={"empleado_id": str(id)})
    return True
