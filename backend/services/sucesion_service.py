"""
Servicio de sucesión y planes de carrera. Lógica de negocio del módulo.
Flujo: router → service → repository → DB
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.planes_carrera_repo import PlanesCarreraRepo
from repositories.sucesion_repo import SucesionRepo
from schemas.sucesion import (
    EmpleadoAnalisisResponse, EmpleadoMapaResponse,
    HitoBodyCreate, HitoResponse,
    PlanCarreraCreate, PlanCarreraResponse,
)
from services._empleado_scope import ensure_empleado_de_empresa
from utils.errors import AppError
from utils.logger import logger


class SucesionService:
    def __init__(
        self,
        repo: Optional[SucesionRepo] = None,
        planes_repo: Optional[PlanesCarreraRepo] = None,
        empleado_repo: Optional[EmpleadoRepo] = None,
    ) -> None:
        self._repo = repo or SucesionRepo()
        self._planes_repo = planes_repo or PlanesCarreraRepo()
        self._empleado_repo = empleado_repo or EmpleadoRepo()

    def get_mapa_talento(self, empresa_id: Optional[UUID] = None) -> list[EmpleadoMapaResponse]:
        """
        Retorna todos los empleados activos con su potencial y desempeño
        para posicionarlos en el mapa 9-Box, filtrado por empresa.
        """
        return self._repo.get_mapa_talento(empresa_id)

    def get_planes_carrera(self, empresa_id: Optional[UUID] = None) -> list[PlanCarreraResponse]:
        """
        Retorna todos los planes de carrera activos filtrados por empresa (None = todas).
        """
        return self._planes_repo.get_planes_carrera(empresa_id)

    def create_plan_carrera(self, data: PlanCarreraCreate,
                            empresa_id: Optional[UUID] = None) -> PlanCarreraResponse:
        """
        Crea un nuevo plan de carrera para un empleado.
        La empresa en la que se escribe se hereda del empleado — no se pide explícitamente y NO
        cambia. `empresa_id` (header) es solo la barrera de a qué empleado se puede apuntar;
        validado eso, ambas coinciden por construcción. None = todas (consolidado).
        Valida que el empleado no tenga ya un plan activo antes de crear.

        Raises:
            AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa.
            AppError: PLAN_ALREADY_EXISTS (409) si el empleado ya tiene un plan activo.
        """
        empleado = ensure_empleado_de_empresa(self._empleado_repo, data.empleado_id, empresa_id)
        existente = self._planes_repo.get_plan_by_empleado(str(data.empleado_id))
        if existente:
            raise AppError(
                "El colaborador ya tiene un plan de carrera activo",
                "PLAN_ALREADY_EXISTS",
                409,
            )
        empresa_id_str = empleado.empresa_id or ""
        plan = self._planes_repo.create_plan(data, empresa_id_str)
        logger.info("Plan de carrera creado",
                    extra={"empleado_id": str(data.empleado_id), "plan_id": str(plan.id)})
        return plan

    def _plan_or_404(self, plan_id: UUID, empresa_id: Optional[UUID]) -> PlanCarreraResponse:
        """Carga el plan validando empresa. Un plan ajeno da el MISMO 404 que uno inexistente."""
        plan = self._planes_repo.get_plan_by_id(str(plan_id), empresa_id)
        if not plan:
            raise AppError("Plan no encontrado", "PLAN_NOT_FOUND", 404)
        return plan

    def get_hitos(self, plan_id: UUID, empresa_id: Optional[UUID] = None) -> list[HitoResponse]:
        """
        Retorna todos los hitos de un plan de carrera ordenados por creación.
        Valida el plan contra la empresa activa (None = consolidado) antes de leer sus hitos:
        los hitos se alcanzan por plan_id, así que gatear el plan cubre la cadena.
        """
        self._plan_or_404(plan_id, empresa_id)
        return self._planes_repo.get_hitos(str(plan_id))

    def create_hito(self, plan_id: UUID, data: HitoBodyCreate,
                    empresa_id: Optional[UUID] = None) -> HitoResponse:
        """
        Crea un nuevo hito dentro de un plan de carrera.
        La empresa del hito se hereda del plan (que la heredó del empleado) — eso no cambia;
        `empresa_id` solo acota a qué plan se puede apuntar.

        Antes, un plan inexistente o ajeno caía en empresa_id_str="" y creaba el hito igual,
        huérfano de empresa. Ahora corta con 404.

        Raises:
            AppError: PLAN_NOT_FOUND (404) si el plan no existe o es de otra empresa.
        """
        plan = self._plan_or_404(plan_id, empresa_id)
        hito = self._planes_repo.create_hito(
            str(plan_id), data.titulo, data.descripcion,
            str(data.fecha_objetivo) if data.fecha_objetivo else None,
            str(plan.empresa_id or ""), data.tipo,
        )
        logger.info("Hito creado", extra={"plan_id": str(plan_id), "hito_id": str(hito.id)})
        return hito

    def completar_hito(self, hito_id: UUID, empresa_id: Optional[UUID] = None) -> bool:
        """
        Marca un hito del plan de carrera como completado. El hito lleva empresa_id propio,
        así que el filtro va en el WHERE del update (uno ajeno no afecta filas → 404).

        Raises:
            AppError: HITO_NOT_FOUND (404) si el hito no existe o es de otra empresa.
        """
        ok = self._planes_repo.completar_hito(str(hito_id), empresa_id)
        if not ok:
            raise AppError("Hito no encontrado", "HITO_NOT_FOUND", 404)
        logger.info("Hito completado", extra={"hito_id": str(hito_id)})
        return True

    def update_readiness(self, plan_id: UUID, readiness: int,
                         empresa_id: Optional[UUID] = None) -> PlanCarreraResponse:
        """
        Actualiza el readiness de un plan de carrera, previa validación de empresa.

        Raises:
            AppError: PLAN_NOT_FOUND (404) si el plan no existe o es de otra empresa.
        """
        self._plan_or_404(plan_id, empresa_id)
        plan = self._planes_repo.update_readiness(str(plan_id), readiness)
        logger.info("Readiness actualizado",
                    extra={"plan_id": str(plan_id), "readiness": readiness})
        return plan

    def get_analisis_posicion(self, area_id: UUID, empresa_id: Optional[UUID] = None) -> list[EmpleadoAnalisisResponse]:
        """
        Retorna empleados del área ordenados por su score de assessment.
        Los empleados sin assessment aparecen al final con score None.
        """
        return self._repo.get_analisis_posicion(str(area_id), empresa_id)
