"""
Servicio de asignaciones de proyecto.
Flujo: router → service → repository → DB

Reglas:
  - empleado_empresa_id se deriva de empleados.empresa_id (NO del proyecto).
  - Un empleado puede pertenecer a una empresa distinta a la dueña del proyecto → permitido.
  - UNIQUE(proyecto_id, empleado_id) → ASIGNACION_DUPLICADA 409.
  - Empleado en estado 'baja' no se puede asignar.
"""
from typing import Optional
from uuid import UUID

from repositories.proyecto_asignaciones_repo import (
    AsignacionesRepo, find_empresa_for_empleado, get_estado_empleado,
)
from repositories.area_repo import AreaRepo
from repositories.proyectos_repo import ProyectosRepo
from services import _asignaciones_bulk as bulk
from services._asignacion_precargada import AsignacionPrecargada
from schemas.proyectos import (
    AsignacionAreaCreate, AsignacionBulkCreate, AsignacionBulkResult,
    AsignacionCreate, AsignacionListResponse, AsignacionResponse, AsignacionUpdate,
)
from utils.errors import AppError
from utils.estados_empleado import ESTADO_PREINGRESO, ESTADOS_EN_PLANTILLA
from utils.logger import logger


class AsignacionesService:
    def __init__(
        self,
        repo: Optional[AsignacionesRepo] = None,
        proyectos_repo: Optional[ProyectosRepo] = None,
        areas_repo: Optional[AreaRepo] = None,
    ) -> None:
        self._repo = repo or AsignacionesRepo()
        self._proyectos = proyectos_repo or ProyectosRepo()
        self._areas = areas_repo or AreaRepo()

    def get_by_proyecto(self, proyecto_id: UUID, empresa_id: Optional[UUID] = None) -> AsignacionListResponse:
        """Lista asignaciones del proyecto. Valida que el proyecto exista y pertenezca a la empresa."""
        if not self._proyectos.find_by_id(str(proyecto_id), empresa_id):
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        items = self._repo.find_by_proyecto(str(proyecto_id))
        return AsignacionListResponse(items=items, total=len(items))

    def asignar(self, proyecto_id: UUID, data: AsignacionCreate, empresa_id: Optional[UUID] = None,
                *, precargado: Optional[AsignacionPrecargada] = None) -> AsignacionResponse:
        """
        Asigna un empleado al proyecto (alta individual). Valida el proyecto y delega en _asignar_uno.

        `precargado` (ver AsignacionPrecargada) evita las 3 queries de validación cuando el caller
        ya tiene esos datos. None (default) = comportamiento idéntico al de siempre.

        Raises:
            AppError: PROYECTO_NOT_FOUND (404), EMPLEADO_NOT_FOUND (404),
                      EMPLEADO_INACTIVO (422), ASIGNACION_DUPLICADA (409).
        """
        if precargado is None:
            if not self._proyectos.find_by_id(str(proyecto_id), empresa_id):
                raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        elif not precargado.proyecto_existe_en_empresa:
            raise AppError("Proyecto no encontrado", "PROYECTO_NOT_FOUND", 404)
        return self._asignar_uno(proyecto_id, data.empleado_id, data.rol, data.valor_hora,
                                 data.fecha_desde, data.fecha_hasta, precargado)

    def _asignar_uno(self, proyecto_id: UUID, empleado_id, rol, valor_hora, fecha_desde, fecha_hasta,
                     precargado: Optional[AsignacionPrecargada] = None) -> AsignacionResponse:
        """
        Inserta UNA asignación (empresa del empleado por lookup — permite cruce multi-empresa).
        NO valida el proyecto (lo hace el caller una sola vez). El duplicado lo detecta el UNIQUE
        uq_proyecto_empleado, no un check previo.

        Con `precargado`, la empresa y el estado del empleado vienen del caller en vez de dos
        queries. Los DOS chequeos se siguen haciendo, sobre los valores provistos.

        Raises: EMPLEADO_NOT_FOUND (404), EMPLEADO_INACTIVO (422), ASIGNACION_DUPLICADA (409).
        """
        if precargado is None:
            empleado_empresa_id = find_empresa_for_empleado(str(empleado_id))
            estado = get_estado_empleado(str(empleado_id))
        else:
            empleado_empresa_id, estado = precargado.empleado_empresa_id, precargado.empleado_estado
        if not empleado_empresa_id:
            raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
        # 🔴 LA PREGUNTA PASÓ DE "¿es baja?" A "¿está en plantilla?" (18/8/2026). Con el `== "baja"`
        # anterior, un PREINGRESO se podía asignar a un proyecto y, por lo tanto, imputarle horas
        # ANTES de haber entrado: eso no es una ficha rara en una pantalla, es **dato falso en el
        # reporte de horas por cliente**, que es lo que se factura. Preguntar por el conjunto y no
        # por un valor es además lo que deja la guarda correcta ante el próximo estado que se
        # agregue al CHECK, en vez de tener que acordarse de sumarlo acá.
        if estado not in ESTADOS_EN_PLANTILLA:
            if estado == ESTADO_PREINGRESO:
                # Código PROPIO y no el genérico de baja: los dos rechazos se arreglan distinto
                # —a un preingreso se lo activa, a una baja no— y la pantalla necesita poder
                # decir cuál de los dos es sin adivinar por el texto del mensaje.
                raise AppError(
                    "Este empleado todavía no ingresó: activalo desde su legajo antes de "
                    "asignarlo a un proyecto.", "EMPLEADO_PREINGRESO", 422)
            raise AppError("No se puede asignar un empleado dado de baja", "EMPLEADO_INACTIVO", 422)
        try:
            row = self._repo.save(str(proyecto_id), str(empleado_id), empleado_empresa_id, rol, valor_hora, fecha_desde, fecha_hasta)
        except Exception as exc:
            if "uq_proyecto_empleado" in str(exc):
                raise AppError("El empleado ya está asignado a este proyecto", "ASIGNACION_DUPLICADA", 409)
            raise AppError("Error al crear la asignación", "DB_ERROR", 500) from exc
        logger.info("Empleado asignado al proyecto", extra={"proyecto_id": str(proyecto_id), "empleado_id": str(empleado_id)})
        return row

    def asignar_bulk(self, proyecto_id: UUID, data: AsignacionBulkCreate, empresa_id: Optional[UUID] = None) -> AsignacionBulkResult:
        """Alta multi-selección. Delegado a `_asignaciones_bulk.asignar_bulk`, donde vive también
        la clasificación del resultado — compartida con el alta por área."""
        return bulk.asignar_bulk(self._asignar_uno, self._proyectos, proyecto_id, data, empresa_id)

    def asignar_area(self, proyecto_id: UUID, data: AsignacionAreaCreate, empresa_id: Optional[UUID] = None) -> AsignacionBulkResult:
        """Alta de un área entera (FOTO, no vínculo vivo). Delegado a `_asignaciones_bulk`, donde
        está escrito por qué la barrera va en dos pasos y por qué al segundo NO le falta un filtro."""
        return bulk.asignar_area(self._asignar_uno, self._proyectos, self._areas, proyecto_id, data, empresa_id)

    def update(self, asignacion_id: UUID, data: AsignacionUpdate, empresa_id: Optional[UUID] = None) -> AsignacionResponse:
        """Actualiza rol, valor_hora o fechas de la asignación. Valida ownership: proyecto dueño debe coincidir con empresa_id."""
        asig = self._repo.find_by_id(str(asignacion_id))
        if not asig:
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        # 404 (no 403) — no revelar que el recurso existe en otra empresa
        if not self._proyectos.find_by_id(str(asig.proyecto_id), empresa_id):
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        patch = {k: (str(v) if hasattr(v, "isoformat") else v)
                 for k, v in data.model_dump(exclude_none=True).items()}
        updated = self._repo.update(str(asignacion_id), patch)
        logger.info("Asignación actualizada", extra={"asignacion_id": str(asignacion_id)})
        return updated  # type: ignore[return-value]

    def delete(self, asignacion_id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """Elimina asignación. Rechaza si tiene horas registradas. Valida ownership: proyecto dueño debe coincidir con empresa_id."""
        asig = self._repo.find_by_id(str(asignacion_id))
        if not asig:
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        # 404 (no 403) — no revelar que el recurso existe en otra empresa
        if not self._proyectos.find_by_id(str(asig.proyecto_id), empresa_id):
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        if self._repo.has_horas(str(asignacion_id)):
            raise AppError(
                "No se puede quitar un empleado con horas registradas",
                "ASIGNACION_CON_HORAS", 409,
            )
        self._repo.delete(str(asignacion_id))
        logger.info("Asignación eliminada", extra={"asignacion_id": str(asignacion_id)})
