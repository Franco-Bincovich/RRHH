"""
Servicio de onboarding. Lógica de negocio del módulo de Onboarding.
Flujo: router → service → repository → DB
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.onboarding_repo import OnboardingRepo
from repositories.onboarding_templates_repo import OnboardingTemplatesRepo
from schemas.onboarding import InstanciaDetalleResponse, InstanciaResponse
from services._onboarding_iniciar import iniciar
from utils.errors import AppError
from utils.logger import logger


class OnboardingService:
    def __init__(
        self,
        repo: Optional[OnboardingRepo] = None,
        templates_repo: Optional[OnboardingTemplatesRepo] = None,
        empleado_repo: Optional[EmpleadoRepo] = None,
    ) -> None:
        self._repo = repo or OnboardingRepo()
        self._templates_repo = templates_repo or OnboardingTemplatesRepo()
        self._empleado_repo = empleado_repo or EmpleadoRepo()

    def get_onboardings_activos(self, empresa_id: Optional[UUID] = None) -> list[InstanciaResponse]:
        """
        Retorna todos los onboardings activos filtrados por empresa (None = todas).

        Returns:
            Lista de InstanciaResponse con progreso calculado por empleado.
        """
        return self._repo.find_instancias_activas(empresa_id)

    def get_onboarding_empleado(self, empleado_id: UUID, empresa_id: Optional[UUID] = None) -> InstanciaDetalleResponse:
        """
        Retorna el detalle completo del onboarding activo de un empleado, incluidas
        las tareas con su estado de completado, agrupables por semana.

        Args:
            empleado_id: UUID del empleado a consultar.
            empresa_id: filtro de empresa opcional (None = sin restricción).

        Returns:
            InstanciaDetalleResponse con todas las tareas y su progreso.

        Raises:
            AppError: ONBOARDING_NOT_FOUND (404) si no hay onboarding activo para el empleado.
        """
        instancia = self._repo.find_instancia_by_empleado(str(empleado_id), empresa_id)
        if not instancia:
            raise AppError(
                "No hay onboarding activo para este empleado",
                "ONBOARDING_NOT_FOUND",
                404,
            )
        detalle = self._repo.get_progreso(str(instancia.id))
        if not detalle:
            raise AppError("Error al cargar el progreso del onboarding", "ONBOARDING_ERROR", 500)
        return detalle

    def iniciar_onboarding(self, empleado_id: UUID, template_id: Optional[UUID] = None,
                           empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                           rol: Optional[str] = None) -> InstanciaResponse:
        """Inicia el onboarding para un empleado. Delegado a _onboarding_iniciar.iniciar.
        `empresa_id` acota a qué empleado se puede apuntar (None = consolidado); `user_id`/`rol` son
        el sujeto de la visibilidad de la plantilla elegida.
        Raises: EMPLEADO_NOT_FOUND (404), ONBOARDING_ALREADY_ACTIVE (409),
        TEMPLATE_NOT_FOUND (404)."""
        return iniciar(self._repo, self._templates_repo, self._empleado_repo,
                       empleado_id, template_id, empresa_id, user_id, rol)

    def completar_tarea(self, instancia_id: UUID, tarea_id: UUID) -> bool:
        """
        Marca una tarea de onboarding como completada.

        Args:
            instancia_id: UUID de la instancia de onboarding.
            tarea_id: UUID de la tarea a completar.

        Returns:
            True si la tarea fue marcada como completada.

        Raises:
            AppError: TAREA_NOT_FOUND (404) si la combinación instancia/tarea no existe.
        """
        ok = self._repo.completar_tarea(str(instancia_id), str(tarea_id))
        if not ok:
            raise AppError("Tarea no encontrada en esta instancia", "TAREA_NOT_FOUND", 404)
        logger.info(
            "Tarea de onboarding completada",
            extra={"instancia_id": str(instancia_id), "tarea_id": str(tarea_id)},
        )
        return True
