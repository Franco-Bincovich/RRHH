"""
Alta MÚLTIPLE de empleados a un proyecto: valida el proyecto una vez y clasifica el resultado.

Extraído de `asignaciones_service.py`, que estaba en 139 contra un límite de 150 y no admitía el
alta por área. Molde: `_vacaciones_write.crear(repo, periodos, ownership, data, ...)` — función
libre que recibe los colaboradores por parámetro; el service la delega en una línea. La lógica se
movió VERBATIM: mismo orden de validación, mismo éxito parcial, mismo log.

🔴 `asignar_uno` LLEGA POR PARÁMETRO y no se mudó acá. Lo usan el alta SINGLE y este bulk: si
viviera en este módulo, `asignaciones_service` tendría que importar del módulo al que delega —
un ciclo de lectura que no compra nada. Pasarlo como colaborador es el mismo patrón con el que
`_vacaciones_write` recibe el repo.
"""
from typing import Callable, List, Optional, Union
from uuid import UUID

from repositories._scope_filtros import empleados_de_area
from schemas.proyectos import (
    AsignacionAreaCreate, AsignacionBulkCreate, AsignacionBulkError, AsignacionBulkResult,
    AsignacionResponse,
)
from services._empleados_utils import ensure_area_valida
from utils.errors import AppError
from utils.logger import logger


def asignar_bulk(asignar_uno: Callable, proyectos_repo, proyecto_id: UUID,
                 data: AsignacionBulkCreate, empresa_id: Optional[UUID] = None) -> AsignacionBulkResult:
    """
    Alta multi-selección: valida el proyecto UNA vez y asigna empleado por empleado.
    Éxito parcial (patrón nómina): no aborta; clasifica en asignados / errores por empleado.

    Args:
        asignar_uno: `AsignacionesService._asignar_uno` (o un doble). Ver el encabezado.
        proyectos_repo: ProyectosRepo, para la barrera de empresa sobre el proyecto.
        proyecto_id · data · empresa_id: como en el service.

    Raises: PROYECTO_NOT_FOUND (404) si el proyecto no existe o no es de la empresa.
    """
    if not proyectos_repo.find_by_id(str(proyecto_id), empresa_id):
        raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
    return clasificar(asignar_uno, proyecto_id, data.empleado_ids, data)


def clasificar(asignar_uno: Callable, proyecto_id: UUID, empleado_ids: List[UUID],
               data: Union[AsignacionBulkCreate, AsignacionAreaCreate]) -> AsignacionBulkResult:
    """Asigna cada empleado y agrupa el resultado. NO valida el proyecto: lo hace el caller.

    🔴 ES LA ÚNICA CLASIFICACIÓN DEL MÓDULO, y por eso está separada de `asignar_bulk`: la
    comparten el alta manual (una selección de checkboxes) y el alta por área. Si cada una
    clasificara por su cuenta, el día que aparezca un motivo nuevo quedaría en una sola — la
    misma regla escrita dos veces, que en este repo ya se pagó con los filtros front/back.

    `data` es la union de los dos schemas de alta: de ella solo se leen los campos COMPARTIDOS
    (rol, valor_hora, fechas). La lista de empleados llega aparte justamente porque es lo único
    que difiere entre los dos caminos — uno la trae del body, el otro la resuelve del área.
    """
    asignados: List[AsignacionResponse] = []
    ya_asignados: List[AsignacionBulkError] = []
    errores: List[AsignacionBulkError] = []
    for eid in empleado_ids:
        try:
            asignados.append(asignar_uno(proyecto_id, eid, data.rol, data.valor_hora,
                                         data.fecha_desde, data.fecha_hasta))
        except AppError as exc:
            # 🔴 El duplicado NO es un error: es la operación siendo idempotente. Se distingue
            # por el CODE y no por el texto del mensaje — un mensaje se reescribe y nadie se
            # entera de que la clasificación se rompió. Ver el docstring de AsignacionBulkResult.
            destino = ya_asignados if exc.code == "ASIGNACION_DUPLICADA" else errores
            destino.append(AsignacionBulkError(empleado_id=eid, motivo=exc.message))
    logger.info("Asignación múltiple", extra={
        "proyecto_id": str(proyecto_id), "asignados": len(asignados),
        "ya_asignados": len(ya_asignados), "errores": len(errores)})
    return AsignacionBulkResult(asignados=asignados, ya_asignados=ya_asignados, errores=errores)


def asignar_area(asignar_uno: Callable, proyectos_repo, areas_repo, proyecto_id: UUID,
                 data: AsignacionAreaCreate, empresa_id: Optional[UUID] = None) -> AsignacionBulkResult:
    """Asigna al proyecto TODOS los empleados de un área, resueltos en este momento (FOTO).

    Reusa `clasificar`, la misma del alta manual: los tres grupos salen idénticos.

    ═══════════════════════════════════════════════════════════════════════════════════════
    🔴 LA BARRERA VA EN DOS PASOS SEPARADOS. NO "le falta el filtro de empresa" — leer esto
    antes de agregárselo, porque es exactamente lo que el próximo lector va a querer hacer.
    ═══════════════════════════════════════════════════════════════════════════════════════

      1. El ÁREA se valida contra el `empresa_id` del request (`ensure_area_valida` → 404).
         Es un id de recurso que llega de afuera, así que le corresponde su barrera de Fase 2.

      2. Los EMPLEADOS se resuelven SIN filtro de empresa: `empleados_de_area(area_id)`.

    Por qué el paso 2 no lleva el `empresa_id`, aunque `empleados_de_area` lo acepte:

      · Sería REDUNDANTE. Los empleados de un área son de la empresa del área por construcción:
        `ensure_area_valida` lo garantiza en toda escritura de empleado.
      · Y redundante-pero-SILENCIOSO es peor que ausente. Si el área fuera de otra empresa, ese
        filtro devolvería LISTA VACÍA y el endpoint respondería "0 asignados, 0 errores" sin
        decir nada. Con la barrera del paso 1, el mismo caso da un 404 que explica qué pasó.
        Es el patrón de filtro que falla en silencio que este repo ya corrigió dos veces
        (`indice_por_nombre` y `proyecto_ids_con_area`).

    ⚠️ En modo consolidado (`empresa_id=None`) el paso 1 no restringe — semántica de
    `get_empresa_id`. Un usuario en "Todas las empresas" PUEDE asignar un área de la empresa B a
    un proyecto de la A, y eso es CORRECTO: es el cruce que `proyecto_asignaciones.empleado_empresa_id`
    existe para soportar (la asignación guarda la empresa del EMPLEADO, no la del proyecto).
    Hoy no se puede probar con datos reales —hay una sola empresa en producción y las 9 áreas son
    todas suyas—, así que ese caso vive en los tests hasta que exista la segunda.

    Raises:
        AppError: PROYECTO_NOT_FOUND (404) si el proyecto no existe o no es de la empresa.
        AppError: AREA_NOT_FOUND (404) si el área no existe o es de otra empresa.
        AppError: AREA_SIN_EMPLEADOS (422) si el área no tiene a nadie — ver abajo.
    """
    if not proyectos_repo.find_by_id(str(proyecto_id), empresa_id):
        raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
    ensure_area_valida(areas_repo, data.area_id, empresa_id)          # paso 1
    empleado_ids = empleados_de_area(data.area_id)                    # paso 2, sin empresa

    if not empleado_ids:
        # 🔴 Mensaje propio y NO un 200 con tres listas vacías. Un resultado mudo se lee como
        # "no hizo nada" —o peor, como que falló en silencio— cuando lo que pasa es un dato
        # faltante que el usuario puede arreglar. Con 6 de las 9 áreas teniendo una sola
        # persona, un área vacía es un escenario real, no teórico.
        raise AppError(
            "El área no tiene empleados para asignar. Revisá que tengan el área cargada en su ficha.",
            "AREA_SIN_EMPLEADOS", 422)

    return clasificar(asignar_uno, proyecto_id, [UUID(e) for e in empleado_ids], data)
