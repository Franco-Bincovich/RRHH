"""
Write path del módulo de Vacaciones (extraído para mantener el service ≤150 líneas).

Las TRES escrituras: `crear`, `cancel` y `actualizar`. `cancel` y `actualizar` bajaron acá
cuando el service llegó a 152/150 al sumarle el repo de pendientes al saldo — el corte se
eligió por dominio y no por tamaño: son las dos mutaciones de una solicitud QUE YA EXISTE, y
comparten literalmente el mismo prólogo (resolver empresa efectiva, buscar por id, y el 404
único de "no existe o no la gestionás"). Tenerlas separadas era la única forma de que ese
prólogo se pudiera desincronizar entre ellas.

Funciones libres que reciben los colaboradores (repo, periodos, ownership, audit) — mismo molde
que _ausencias_write.crear(...) y _vacaciones_saldo.calcular_saldo(repo, ...). El service las
delega en una línea. La lógica se movió VERBATIM desde VacacionesService: ownership, resolución
de empresa, bloqueo por período, solapamiento y cálculo de días son idénticos a antes.

⚠️ `empresa_efectiva(empresa_id, rol)` la aplica EL SERVICE antes de llamar acá, igual que
antes. No se movió: es el eje de alcance del rol, vive junto a los otros gates del service, y
duplicarlo acá dejaría dos lugares decidiendo lo mismo (ver services/_alcance_mandos.py, que es
la ÚNICA excepción a la barrera de empresa y por eso no se reparte).

Simétrico con _ausencias_write.py, que es por qué ausencias tenía margen de líneas para sumar
filtros y vacaciones no. Esta división le devuelve ese margen a vacaciones, que es lo que las
tandas de filtros del bloque B necesitan.

⚠️ REGLA DEL BLOQUE B: todo filtro que acote EMPLEADOS entra por services/_ownership_filter,
nunca por un `.eq()` nuevo en el repo — en este módulo el ownership de mandos_medios viaja por
ese mismo canal, y esquivarlo no da error: devuelve filas de empleados ajenos. La composición
es por INTERSECCIÓN (ownership ∩ área ∩ empleado), nunca reemplazo.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from schemas.vacaciones import SolicitudVacacionesCreate, SolicitudVacacionesResponse, SolicitudVacacionesUpdate
from services._audit_payloads import payload_cancelacion_vacacion
from services._audit_payloads_vacaciones import payload_update_vacacion
from services._periodo_utils import verificar_periodo_abierto
from services._vacaciones_utils import derive_estado
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError
from utils.logger import logger


def _gestionable(repo, ownership, id: UUID, empresa_id, usuario_id, rol):
    """La solicitud, si existe Y el rol la gestiona. El 404 es el MISMO en los dos casos: un
    código distinto para "es de otro" confirmaría que existe (oráculo de enumeración).

    Es el prólogo compartido de `cancel` y `actualizar`. Devuelve la fila —no un bool— para que
    el caller la reuse en vez de leerla dos veces."""
    row = repo.find_by_id(str(id), empresa_id)
    if not row or not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, ownership):
        raise AppError("Solicitud de vacaciones no encontrada", "VACACION_NOT_FOUND", 404)
    return row


def crear(repo, periodos, ownership, data: SolicitudVacacionesCreate, created_by: str,
          rol: str | None = None) -> SolicitudVacacionesResponse:
    """
    Registra un período de vacaciones para un empleado.
    empresa_id se resuelve del empleado — no lo provee el usuario.

    Ownership: se valida ANTES de resolver la empresa (403 uniforme para un mando que
    intenta crear a nombre de un empleado que no es su subordinado — exista o no).

    Args:
        repo: VacacionesRepo.
        periodos: PeriodoRepo para el bloqueo por período cerrado.
        ownership: EmpleadoOwnershipRepo para el chequeo de alcance del rol.
        data: Campos del formulario (empleado_id, fecha_desde, fecha_hasta, tipo, comentario).
        created_by: ID del operador que registra (trazabilidad y sujeto del ownership).
        rol: Rol del operador (para el chequeo de ownership).

    Raises:
        AppError: OWNERSHIP_DENIED (403) si el rol no puede gestionar a ese empleado.
        AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe.
        AppError: VACACIONES_SOLAPAMIENTO (422) si hay fechas solapadas del mismo tipo para el mismo empleado.
    """
    if not puede_gestionar_empleado(created_by, rol, data.empleado_id, ownership):
        raise AppError("No autorizado para gestionar este colaborador", "OWNERSHIP_DENIED", 403)
    empresa_id = repo.find_empresa_for_empleado(str(data.empleado_id))
    if not empresa_id:
        raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)
    verificar_periodo_abierto(empresa_id, "vacaciones", rol, desde=data.fecha_desde, hasta=data.fecha_hasta, repo=periodos)

    overlapping = repo.find_overlapping(
        str(data.empleado_id), data.fecha_desde, data.fecha_hasta, data.tipo
    )
    if overlapping:
        raise AppError(
            "El colaborador ya tiene una solicitud del mismo tipo en ese período",
            "VACACIONES_SOLAPAMIENTO",
            422,
        )

    dias = (data.fecha_hasta - data.fecha_desde).days + 1
    if data.dias_liquidados > dias:
        raise AppError("Los días liquidados no pueden superar los días de la licencia",
                       "DIAS_LIQUIDADOS_INVALIDOS", 422)
    row = repo.save(
        str(data.empleado_id), empresa_id,
        data.fecha_desde, data.fecha_hasta,
        dias, data.tipo, data.comentario,
        data.periodo, data.dias_liquidados,
    )
    logger.info(
        "Vacaciones registradas",
        extra={"solicitud_id": row.id, "empleado_id": str(data.empleado_id), "tipo": data.tipo, "created_by": created_by},
    )
    return derive_estado(row, date.today())


def cancel(repo, periodos, ownership, audit, id: UUID, empresa_id: Optional[UUID] = None,
           usuario_id: Optional[str] = None, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
    """
    Cancela una solicitud seteando cancelada=True (no borra la fila — preserva historial).
    Registra el evento de auditoría tras la cancelación exitosa (usuario_id = operador).

    Ownership: un registro ajeno a un mando responde 404 (igual que inexistente), para no
    confirmar la existencia de solicitudes de empleados que no gestiona.

    Raises:
        AppError: VACACION_NOT_FOUND (404) si el ID no existe o no es gestionable por el rol.
        AppError: YA_CANCELADA (422) si ya estaba cancelada.
    """
    row = _gestionable(repo, ownership, id, empresa_id, usuario_id, rol)
    verificar_periodo_abierto(row.empresa_id, "vacaciones", rol, desde=row.fecha_desde, hasta=row.fecha_hasta, repo=periodos)
    if row.cancelada:
        raise AppError("La solicitud ya está cancelada", "YA_CANCELADA", 422)
    updated = repo.cancel(str(id), empresa_id)
    audit.registrar(**payload_cancelacion_vacacion(row, updated, usuario_id, row.empresa_id))
    logger.info("Vacaciones canceladas", extra={"solicitud_id": str(id)})
    return derive_estado(updated, date.today())  # type: ignore[arg-type]


def actualizar(repo, ownership, audit, id: UUID, data: SolicitudVacacionesUpdate,
               empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None,
               rol: Optional[str] = None) -> SolicitudVacacionesResponse:
    """Edita una solicitud (hoy: período, días liquidados, comentario y tipo). NO toca fechas:
    cambiarlas movería `dias` y el solapamiento, que es otra operación.
    Mismo gate empresa ∩ ownership y mismo 404 único que get_by_id/cancel."""
    row = _gestionable(repo, ownership, id, empresa_id, usuario_id, rol)
    patch = data.model_dump(exclude_unset=True, exclude_none=True)
    if patch.get("dias_liquidados", 0) > row.dias:
        raise AppError("Los días liquidados no pueden superar los días de la licencia",
                       "DIAS_LIQUIDADOS_INVALIDOS", 422)
    nuevo = repo.update(str(id), patch, empresa_id)
    if not nuevo:
        raise AppError("Solicitud de vacaciones no encontrada", "VACACION_NOT_FOUND", 404)
    audit.registrar(**payload_update_vacacion(row, nuevo, usuario_id))
    return derive_estado(nuevo, date.today())
