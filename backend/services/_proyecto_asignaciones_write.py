"""
Las dos escrituras de `proyecto_asignaciones` que no son el alta: editar y quitar.

Salió de `asignaciones_service.py`, que estaba en 149/150 —o sea sin margen para una sola línea—
cuando le tocó sumar los eventos de auditoría de la tanda del 25/8/2026. Molde: `_areas_write.py`
y `_objetivos_write.py`.

🔴 POR QUÉ SALIERON ESTAS DOS Y NO EL ALTA, QUE ES LA MÁS LARGA.
`_asignar_uno` es lo único del módulo que orquesta: resuelve la empresa del empleado por lookup
(para permitir el cruce multiempresa), decide con `ESTADOS_EN_PLANTILLA` en vez de con `== "baja"`
—la guarda que impide imputarle horas a alguien que todavía no ingresó, que es dato falso en lo
que se factura— y distingue el rechazo de preingreso del de baja con un code propio, porque los
dos se arreglan distinto. Ese orden es load-bearing y leerlo de corrido es lo que hace evidente
que está bien. Estas dos, en cambio, validan ownership, escriben y auditan.

⚠️ LAS DOS REPITEN LA MISMA VALIDACIÓN DE OWNERSHIP EN DOS PASOS y no se centralizó en un helper:
la asignación se busca SIN filtro de empresa (se alcanza por su id) y la barrera se aplica sobre
el PROYECTO padre. Los dos fallos devuelven el MISMO 404 —nunca un 403— para no confirmar que el
recurso existe en otra empresa. Un `asignacion_visible()` compartido ahorraría cuatro líneas y
escondería justamente el paso que hay que poder leer.
"""
from typing import Optional
from uuid import UUID

from schemas.proyectos import AsignacionResponse, AsignacionUpdate
from services._audit_payloads_proyectos import (
    payload_baja_asignacion_proyecto, payload_update_asignacion_proyecto,
)
from utils.errors import AppError
from utils.logger import logger

_NO_ENCONTRADA = ("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)


def _empresa_del_evento(asig) -> Optional[str]:
    """La empresa con la que se etiqueta el evento: la del EMPLEADO, no la del proyecto.

    Está en la fila, así que no cuesta una query. El porqué está en el encabezado de
    `_audit_payloads_proyectos`.
    """
    return str(asig.empleado_empresa_id) if asig.empleado_empresa_id else None


def actualizar(repo, proyectos_repo, audit, asignacion_id: UUID, data: AsignacionUpdate,
               empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> AsignacionResponse:
    """Actualiza rol, valor_hora o fechas de la asignación.

    🔑 El `asig` que valida el ownership ES el "antes" del diff: no hace falta releerlo. Volver a
    consultarlo después del update daría el estado NUEVO dos veces y el diff diría "rol → rol".

    Args:
        repo: AsignacionesRepo (o doble).
        proyectos_repo: ProyectosRepo (o doble) — aplica la barrera de empresa sobre el padre.
        audit: AuditService (o doble).
        asignacion_id: Asignación a editar.
        data: Campos a actualizar.
        empresa_id: Empresa del request. None = consolidado.
        usuario_id: Operador, para la trazabilidad del evento.

    Raises:
        AppError: ASIGNACION_NOT_FOUND (404) si no existe o su proyecto es de otra empresa.
    """
    asig = repo.find_by_id(str(asignacion_id))
    if not asig:
        raise AppError(*_NO_ENCONTRADA)
    # 404 (no 403) — no revelar que el recurso existe en otra empresa
    if not proyectos_repo.find_by_id(str(asig.proyecto_id), empresa_id):
        raise AppError(*_NO_ENCONTRADA)
    patch = {k: (str(v) if hasattr(v, "isoformat") else v)
             for k, v in data.model_dump(exclude_none=True).items()}
    updated = repo.update(str(asignacion_id), patch)
    audit.registrar(**payload_update_asignacion_proyecto(
        asig, updated, usuario_id, _empresa_del_evento(asig)))
    logger.info("Asignación actualizada", extra={"asignacion_id": str(asignacion_id)})
    return updated


def eliminar(repo, proyectos_repo, audit, asignacion_id: UUID,
             empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> None:
    """Quita a un colaborador del proyecto. Rechaza si tiene horas registradas.

    🔴 BORRADO FÍSICO: la fila se va y con ella el rol y el `valor_hora` pactados. La guarda de
    `has_horas` protege la plata ya imputada, no la condición — volver a asignar a la persona no
    la recupera. El evento se arma con la fila viva (que ya está en memoria por el ownership) y se
    registra DESPUÉS del delete, porque uno emitido antes afirmaría una baja que todavía puede
    fallar. Mismo orden que `_objetivos_write.eliminar`.

    Args:
        repo: AsignacionesRepo (o doble).
        proyectos_repo: ProyectosRepo (o doble) — aplica la barrera de empresa sobre el padre.
        audit: AuditService (o doble).
        asignacion_id: Asignación a quitar.
        empresa_id: Empresa del request. None = consolidado.
        usuario_id: Operador, para la trazabilidad del evento.

    Raises:
        AppError: ASIGNACION_NOT_FOUND (404), ASIGNACION_CON_HORAS (409).
    """
    asig = repo.find_by_id(str(asignacion_id))
    if not asig:
        raise AppError(*_NO_ENCONTRADA)
    # 404 (no 403) — no revelar que el recurso existe en otra empresa
    if not proyectos_repo.find_by_id(str(asig.proyecto_id), empresa_id):
        raise AppError(*_NO_ENCONTRADA)
    if repo.has_horas(str(asignacion_id)):
        raise AppError("No se puede quitar un colaborador con horas registradas",
                       "ASIGNACION_CON_HORAS", 409)
    repo.delete(str(asignacion_id))
    audit.registrar(**payload_baja_asignacion_proyecto(
        asig, usuario_id, _empresa_del_evento(asig)))
    logger.info("Asignación eliminada", extra={"asignacion_id": str(asignacion_id)})
