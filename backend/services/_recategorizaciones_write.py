"""
Write path de recategorizaciones (extraído para mantener el service ≤150 líneas).

Funciones libres que reciben los colaboradores (repo, empleados, empleado_service, audit) —
mismo molde que `_empleados_write.py` y `_vacaciones_write.py`. El service las delega en una
línea.

🔴 ACÁ VIVE LA APLICACIÓN DE LAS DOS REGLAS DE LA FECHA RETROACTIVA. Las reglas en sí, con su
porqué completo, están en `_recategorizacion_anteriores.py` — este archivo solo las orquesta:
  · REGLA 1 → `resolver_anteriores(repo.find_previa(...), empleado)`
  · REGLA 2 → `es_la_mas_reciente(fecha, repo.find_ultima(...))` decide si se pisa al empleado

🔴 EL ORDEN IMPORTA Y NO ES INTERCAMBIABLE: primero se PERSISTE la recategorización, después se
audita, y recién al final se aplica al empleado. Si el update del empleado corriera primero, un
fallo al insertar la fila dejaría al colaborador con el rol nuevo y sin ningún registro de por
qué — que es exactamente el estado que este módulo existe para evitar. Al revés, un fallo del
update deja el histórico completo y al empleado sin actualizar, que es recuperable a mano y
visible en la planilla.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from schemas.empleado import EmpleadoUpdate
from schemas.recategorizacion import (
    RecategorizacionCreate, RecategorizacionResponse, RecategorizacionUpdate,
)
from services._audit_payloads_recategorizaciones import (
    payload_alta_recategorizacion, payload_update_recategorizacion,
)
from services._empleado_scope import ensure_empleado_de_empresa
from services._recategorizacion_anteriores import (
    empresa_de, es_la_mas_reciente, patch_empleado, resolver_anteriores,
)
from utils.errors import AppError
from utils.logger import logger

NO_ENCONTRADO = ("Recategorización no encontrada", "RECATEGORIZACION_NOT_FOUND", 404)
_SIN_CAMBIOS = ("Tenés que indicar al menos un valor nuevo: rol, seniority o categoría.",
                "RECATEGORIZACION_SIN_CAMBIOS", 422)


def ensure_algo_cambia(rol, seniority, categoria) -> None:
    """Espejo del CHECK `recategorizaciones_algo_cambia_check` (migración 117).

    La garantía real es la base; esto existe para devolver un 422 legible en vez del 23514
    crudo, que para quien lo recibe no tiene ninguna relación con lo que hizo.

    Raises:
        AppError: RECATEGORIZACION_SIN_CAMBIOS (422).
    """
    if rol is None and seniority is None and categoria is None:
        raise AppError(*_SIN_CAMBIOS)


def crear(repo, empleados, empleado_service, audit, data: RecategorizacionCreate,
          empresa_id: Optional[UUID], usuario_id: Optional[str]) -> RecategorizacionResponse:
    """Registra una recategorización y, si corresponde, actualiza al colaborador.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa ·
            RECATEGORIZACION_SIN_CAMBIOS (422) si no trae ningún valor nuevo.
    """
    ensure_algo_cambia(data.rol_nuevo, data.seniority_nueva, data.categoria_nueva)
    empleado = ensure_empleado_de_empresa(empleados, data.empleado_id, empresa_id)
    fecha: date = data.fecha_efectiva or date.today()
    eid = str(data.empleado_id)
    anteriores = resolver_anteriores(repo.find_previa(eid, fecha), empleado)
    fila = repo.save(data, empresa_de(empleado), anteriores, fecha, usuario_id)
    audit.registrar(**payload_alta_recategorizacion(fila, usuario_id))
    aplicar_al_empleado(repo, empleado_service, fila, empleado, empresa_id, usuario_id,
                        excepto_id=str(fila.id))
    logger.info("Recategorización registrada", extra={"recategorizacion_id": str(fila.id)})
    return fila


def editar(repo, empleados, empleado_service, audit, id: UUID, data: RecategorizacionUpdate,
           empresa_id: Optional[UUID], usuario_id: Optional[str]) -> RecategorizacionResponse:
    """Edición. Recalcula los `*_anterior` y reevalúa si corresponde pisar al colaborador.

    Los `*_anterior` se recalculan SIEMPRE, no solo si cambió la fecha: mover `fecha_efectiva`
    cambia cuál es la recategorización previa, y dejarlos como estaban dejaría el histórico
    contradiciéndose sin ninguna señal.

    `excepto_id` va en las DOS consultas de cadena: sin él, la fila se tomaría a sí misma de
    previa (copiándose sus propios valores nuevos como anteriores) y nunca sería más reciente
    que sí misma (así que editarla jamás actualizaría al colaborador).
    """
    prior = repo.find_by_id(str(id), empresa_id)
    if not prior:
        raise AppError(*NO_ENCONTRADO)
    ensure_algo_cambia(data.rol_nuevo or prior.rol_nuevo,
                       data.seniority_nueva or prior.seniority_nueva,
                       data.categoria_nueva or prior.categoria_nueva)
    empleado = ensure_empleado_de_empresa(empleados, prior.empleado_id, empresa_id)
    fecha: date = data.fecha_efectiva or prior.fecha_efectiva
    eid = str(prior.empleado_id)
    anteriores = resolver_anteriores(repo.find_previa(eid, fecha, str(id)), empleado)
    nuevo = repo.update(str(id), data, anteriores)
    if not nuevo:
        raise AppError(*NO_ENCONTRADO)
    audit.registrar(**payload_update_recategorizacion(prior, nuevo, usuario_id))
    aplicar_al_empleado(repo, empleado_service, nuevo, empleado, empresa_id, usuario_id,
                        excepto_id=str(id))
    logger.info("Recategorización editada", extra={"recategorizacion_id": str(id)})
    return nuevo


def aplicar_al_empleado(repo, empleado_service, fila, empleado, empresa_id, usuario_id, *,
                        excepto_id: str) -> None:
    """Pisa al colaborador SOLO si `fila` es la más reciente de esa persona. Ver REGLA 2.

    Va por `EmpleadoService.update_empleado` y no por un write path propio: sus tres
    validaciones cortan solas si su campo es None, así que un patch con solo
    `roles`/`seniority`/`categoria` las atraviesa — y de paso hereda el diff de auditoría del
    empleado, que es el registro TÉCNICO del cambio.
    """
    ultima = repo.find_ultima(str(fila.empleado_id), excepto_id)
    if not es_la_mas_reciente(fila.fecha_efectiva, ultima):
        logger.info("Recategorización retroactiva: no se actualiza al empleado",
                    extra={"empleado_id": str(fila.empleado_id),
                           "fecha_efectiva": str(fila.fecha_efectiva)})
        return
    patch = patch_empleado(fila, empleado)
    if patch:
        empleado_service.update_empleado(UUID(str(fila.empleado_id)), EmpleadoUpdate(**patch),
                                         empresa_id, usuario_id)
