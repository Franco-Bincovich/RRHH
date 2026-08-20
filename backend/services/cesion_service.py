"""
Servicio de cesiones (entidad hija de empleado). Flujo: router → service → repository → DB.

Ownership: la cesión hereda la empresa del empleado (empleados.empresa_id) y se valida la
pertenencia contra la empresa activa del request (fail-closed → 404 si no pertenece). El gating
de ROL va en el router (require_permission(Seccion.EMPLEADOS)). Audita alta/update/baja.
"""
from typing import Optional
from uuid import UUID

from repositories.cesion_repo import CesionRepo
from repositories.empleado_repo import EmpleadoRepo
from schemas.cesion import CesionCreate, CesionListResponse, CesionResponse, CesionUpdate
from schemas.empleado import EmpleadoResponse
from services._audit_payloads_cesion import (
    payload_alta_cesion, payload_baja_cesion, payload_update_cesion,
)
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger


class CesionService:
    def __init__(
        self, repo: Optional[CesionRepo] = None,
        empleado_repo: Optional[EmpleadoRepo] = None, audit: Optional[AuditService] = None,
    ) -> None:
        self._repo = repo or CesionRepo()
        self._empleados = empleado_repo or EmpleadoRepo()
        self._audit = audit or AuditService()

    def _empleado_or_404(self, empleado_id: UUID, empresa_id: Optional[UUID]) -> EmpleadoResponse:
        """Carga el empleado validando pertenencia a la empresa activa. 404 si no existe/no pertenece."""
        emp = self._empleados.find_by_id(str(empleado_id), empresa_id)
        if not emp:
            raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)
        return emp

    def _cesion_owned(self, id: UUID, empresa_id: Optional[UUID]) -> CesionResponse:
        """Carga la cesión validando pertenencia a la empresa activa. 404 si ajena/inexistente."""
        cesion = self._repo.find_by_id(str(id))
        if not cesion or (empresa_id and str(cesion.empresa_id) != str(empresa_id)):
            raise AppError("Cesión no encontrada", "CESION_NOT_FOUND", 404)
        return cesion

    def listar(self, empleado_id: UUID, empresa_id: Optional[UUID] = None) -> CesionListResponse:
        """Lista las cesiones del empleado (fecha desc). Valida ownership del empleado."""
        self._empleado_or_404(empleado_id, empresa_id)
        items = self._repo.find_by_empleado(str(empleado_id))
        return CesionListResponse(items=items, total=len(items))

    def crear(
        self, empleado_id: UUID, data: CesionCreate,
        empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None,
    ) -> CesionResponse:
        """Crea una cesión heredando empresa_id del empleado. Audita alta_cesion."""
        emp = self._empleado_or_404(empleado_id, empresa_id)
        cesion = self._repo.crear({
            "empleado_id": str(empleado_id), "empresa_id": str(emp.empresa_id),
            "fecha": str(data.fecha), "empresa_cesion": data.empresa_cesion,
        })
        self._audit.registrar(**payload_alta_cesion(cesion, usuario_id))
        logger.info("Cesión creada", extra={"cesion_id": cesion.id, "empleado_id": str(empleado_id)})
        return cesion

    def actualizar(
        self, id: UUID, data: CesionUpdate,
        empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None,
    ) -> CesionResponse:
        """Actualización parcial (fecha / empresa_cesion). Audita update_cesion con diff."""
        prior = self._cesion_owned(id, empresa_id)
        patch: dict = {}
        if data.fecha is not None:
            patch["fecha"] = str(data.fecha)
        if data.empresa_cesion is not None:
            patch["empresa_cesion"] = data.empresa_cesion
        updated = self._repo.update(str(id), patch) or prior
        self._audit.registrar(**payload_update_cesion(prior, updated, usuario_id))
        logger.info("Cesión actualizada", extra={"cesion_id": str(id)})
        return updated

    def eliminar(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> None:
        """Borra la cesión (hard delete). Audita baja_cesion."""
        prior = self._cesion_owned(id, empresa_id)
        self._repo.delete(str(id))
        self._audit.registrar(**payload_baja_cesion(prior, usuario_id))
        logger.info("Cesión eliminada", extra={"cesion_id": str(id)})
