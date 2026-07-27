"""
Servicio de ausencias. Lógica de negocio del módulo de Ausencias.
Flujo: router → service → repository → DB

Reglas de negocio:
  - empresa_id se hereda del empleado al crear (no lo provee el usuario).
  - dias = (fecha_hasta - fecha_desde).days + 1 (extremos incluidos).
  - NO se valida solapamiento de fechas (a diferencia de vacaciones).
  - tipos_ausencia son globales: no pertenecen a ninguna empresa.

El write path (crear/actualizar/eliminar) vive en services/_ausencias_write.py; el
service lo delega. Ownership y bloqueo por período son idénticos allá.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from repositories.ausencias_repo import AusenciasRepo
from repositories.empleado_ownership_repo import EmpleadoOwnershipRepo
from repositories.periodo_repo import PeriodoRepo
from schemas.ausencias import (
    AusenciaCreate, AusenciaListResponse, AusenciaResponse, AusenciaUpdate,
)
from services._ausencias_export import construir_filas_export
from services._ausencias_write import actualizar, crear, eliminar
from services._ownership_filter import resolver_empleado_ids
from services.audit_service import AuditService
from services.export import Descarga, build_export
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError


class AusenciasService:
    def __init__(self, repo: Optional[AusenciasRepo] = None, audit: Optional[AuditService] = None, periodo_repo: Optional[PeriodoRepo] = None, ownership_repo: Optional[EmpleadoOwnershipRepo] = None) -> None:
        self._repo = repo or AusenciasRepo()
        self._audit = audit or AuditService()
        self._periodos = periodo_repo or PeriodoRepo()
        self._ownership = ownership_repo or EmpleadoOwnershipRepo()

    def get_all(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None, area_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None, tipo_id: Optional[UUID] = None, page: int = 1, page_size: int = 20, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> AusenciaListResponse:
        """Página de ausencias filtrada por empresa/área/empleado/tipo y por ownership (intersección). vacio → devuelve vacío sin consultar.
        fecha_desde/fecha_hasta acotan por SOLAPAMIENTO con el rango (ver repositories/_rango_fechas): una ausencia que
        empieza antes del rango pero lo cruza ENTRA. Se compone por INTERSECCIÓN con el ownership, que ya viajó en empleado_ids."""
        empleado_ids, vacio = resolver_empleado_ids(user_id, rol, empresa_id, area_id, empleado_id, self._ownership)
        rows, total = ([], 0) if vacio else self._repo.find_all(empresa_id, empleado_ids, tipo_id, page, page_size, desde=fecha_desde, hasta=fecha_hasta)
        return AusenciaListResponse(items=rows, total=total)

    def exportar(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None, formato: str = "excel", area_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None, tipo_id: Optional[UUID] = None, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> Descarga:
        """Exporta ausencias (columnas legibles, sin UUIDs) respetando ownership; acotable por área/empleado/tipo (mismos filtros que el listado)."""
        filas = construir_filas_export(self.get_all(user_id, rol, empresa_id, area_id, empleado_id, tipo_id, 1, 100000, fecha_desde, fecha_hasta).items)
        return build_export(nombre="Ausencias", datos={"Ausencias": filas}, filename_base="ausencias", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> AusenciaResponse:
        """
        Retorna el detalle de una ausencia. Gate empresa ∩ ownership (empresa en el WHERE del
        repo, luego el rol) — el mismo par que ya aplican actualizar/eliminar en _ausencias_write.

        Raises:
            AppError: AUSENCIA_NOT_FOUND (404) si no existe, no pertenece a la empresa, o el rol
                no gestiona a ese empleado (mismo 404: no delata la existencia de la solicitud).
        """
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row or not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, self._ownership):
            raise AppError("Ausencia no encontrada", "AUSENCIA_NOT_FOUND", 404)
        return row

    def create(self, data: AusenciaCreate, created_by: str, rol: Optional[str] = None) -> AusenciaResponse:
        """Registra una ausencia. Delegado a _ausencias_write.crear (ownership + período + audit)."""
        return crear(self._repo, self._audit, self._periodos, self._ownership, data, created_by, rol)

    def update(self, id: UUID, data: AusenciaUpdate, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> AusenciaResponse:
        """Actualiza una ausencia. Delegado a _ausencias_write.actualizar."""
        return actualizar(self._repo, self._audit, self._periodos, self._ownership, id, data, empresa_id, usuario_id, rol)

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> None:
        """Elimina una ausencia permanentemente. Delegado a _ausencias_write.eliminar."""
        eliminar(self._repo, self._audit, self._periodos, self._ownership, id, empresa_id, usuario_id, rol)
