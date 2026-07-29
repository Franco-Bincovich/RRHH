"""
Write path del módulo de Vacaciones (extraído para mantener el service ≤150 líneas).

Función libre que recibe los colaboradores (repo, periodos, ownership) — mismo molde que
_ausencias_write.crear(...) y _vacaciones_saldo.calcular_saldo(repo, ...). El service la delega
en una línea. La lógica se movió VERBATIM desde VacacionesService.create: ownership, resolución
de empresa, bloqueo por período, solapamiento y cálculo de días son idénticos a antes.

Simétrico con _ausencias_write.py, que es por qué ausencias tenía margen de líneas para sumar
filtros y vacaciones no. Esta división le devuelve ese margen a vacaciones, que es lo que las
tandas de filtros del bloque B necesitan.

⚠️ REGLA DEL BLOQUE B: todo filtro que acote EMPLEADOS entra por services/_ownership_filter,
nunca por un `.eq()` nuevo en el repo — en este módulo el ownership de mandos_medios viaja por
ese mismo canal, y esquivarlo no da error: devuelve filas de empleados ajenos. La composición
es por INTERSECCIÓN (ownership ∩ área ∩ empleado), nunca reemplazo.
"""
from datetime import date

from schemas.vacaciones import SolicitudVacacionesCreate, SolicitudVacacionesResponse
from services._periodo_utils import verificar_periodo_abierto
from services._vacaciones_utils import derive_estado
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError
from utils.logger import logger


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
        raise AppError("No autorizado para gestionar este empleado", "OWNERSHIP_DENIED", 403)
    empresa_id = repo.find_empresa_for_empleado(str(data.empleado_id))
    if not empresa_id:
        raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
    verificar_periodo_abierto(empresa_id, "vacaciones", rol, desde=data.fecha_desde, hasta=data.fecha_hasta, repo=periodos)

    overlapping = repo.find_overlapping(
        str(data.empleado_id), data.fecha_desde, data.fecha_hasta, data.tipo
    )
    if overlapping:
        raise AppError(
            "El empleado ya tiene una solicitud del mismo tipo en ese período",
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
