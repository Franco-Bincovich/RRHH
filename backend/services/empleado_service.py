"""
Servicio de empleados. Lógica de negocio del módulo de Empleados.
Flujo: router → service → repository → DB
"""
import math
from typing import Optional
from uuid import UUID

from repositories._scope_filtros import empleados_de_proyecto
from repositories.area_repo import AreaRepo
from repositories.empleado_repo import EmpleadoRepo
from schemas.empleado import EmpleadoCreate, EmpleadoListResponse, EmpleadoResponse, EmpleadoUpdate
from services._empleados_export import construir_filas_export
from services._empleados_utils import empleado_or_404
from services._empleados_write import actualizar, crear, desactivar
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services.audit_service import AuditService
from services.export import Descarga, build_export


class EmpleadoService:
    def __init__(self, repo: Optional[EmpleadoRepo] = None, audit: Optional[AuditService] = None,
                 area_repo: Optional[AreaRepo] = None) -> None:
        self._repo = repo or EmpleadoRepo()
        self._audit = audit or AuditService()
        self._areas = area_repo or AreaRepo()

    def create_empleado(self, data: EmpleadoCreate, created_by: str, empresa_id: UUID, *,
                        areas_validadas: frozenset = frozenset(), auditar: bool = True) -> EmpleadoResponse:
        """Alta de empleado + audit. Delegado a _empleados_write.crear.
        Los dos keyword-only son para el import de nómina; su default deja el alta manual igual.
        Raises: LEGAJO_DUPLICADO (409), AREA_NOT_FOUND (404), MANAGER_NOT_FOUND (404)."""
        return crear(self._repo, self._audit, self._areas, data, created_by, empresa_id,
                     areas_validadas=areas_validadas, auditar=auditar)

    def update_empleado(self, id: UUID, data: EmpleadoUpdate, empresa_id: Optional[UUID] = None,
                        usuario_id: Optional[str] = None, *, areas_validadas: frozenset = frozenset(),
                        prior: Optional[EmpleadoResponse] = None) -> EmpleadoResponse:
        """Actualización parcial + audit del diff. Delegado a _empleados_write.actualizar.
        Los dos keyword-only son para el import de nómina; su default deja la edición manual igual.
        Raises: EMPLEADO_NOT_FOUND (404), AREA_NOT_FOUND (404), MANAGER_NOT_FOUND (404), MANAGER_CICLO (400)."""
        return actualizar(self._repo, self._audit, self._areas, id, data, empresa_id, usuario_id,
                          areas_validadas=areas_validadas, prior=prior)

    def deactivate_empleado(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> bool:
        """Baja lógica (soft delete) + audit. Delegado a _empleados_write.desactivar.
        Raises: EMPLEADO_NOT_FOUND (404)."""
        return desactivar(self._repo, self._audit, id, empresa_id, usuario_id)

    def get_empleados(
        self,
        page: int,
        page_size: int,
        empresa_id: Optional[UUID] = None,
        area_id: Optional[str] = None,
        estado: Optional[str] = None,
        search: Optional[str] = None,
        es_lider: Optional[bool] = None,
        proyecto_id: Optional[UUID] = None,
    ) -> EmpleadoListResponse:
        """
        Retorna la lista paginada de empleados con filtros opcionales.

        Args:
            page: Número de página (1-indexed).
            page_size: Cantidad de registros por página.
            empresa_id: Filtro por empresa. None = todas las empresas (vista consolidada).
            area_id: Filtro por ID de área (UUID como string).
            estado: Filtro por estado (activo | baja | licencia).
            search: Búsqueda por nombre o apellido (case-insensitive).
            es_lider: Si se provee, filtra por el flag de liderazgo (selector de usuarios).

        Returns:
            EmpleadoListResponse con items, total y metadatos de paginación.
        """
        proyecto_ids = empleados_de_proyecto(proyecto_id) if proyecto_id else None
        items, total = self._repo.find_all(page, page_size, empresa_id, area_id, estado, search, es_lider, proyecto_ids)
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return EmpleadoListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", area_id: Optional[str] = None, estado: Optional[str] = None, search: Optional[str] = None, es_lider: Optional[bool] = None, proyecto_id: Optional[UUID] = None) -> Descarga:
        """Exporta empleados (columnas legibles del legajo, sin UUIDs) con los MISMOS filtros que el listado; sin paginar."""
        pagina = self.get_empleados(1, LIMITE_FILAS_EXPORT, empresa_id, area_id, estado, search, es_lider, proyecto_id)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        items = pagina.items
        return build_export(nombre="Empleados", datos={"Empleados": construir_filas_export(items)}, filename_base="empleados", formato=formato)

    def get_empleado(self, id: UUID, empresa_id: Optional[UUID] = None) -> EmpleadoResponse:
        """
        Retorna el detalle completo de un empleado por ID.

        Args:
            id: UUID del empleado a consultar.
            empresa_id: Si se provee, valida que el empleado pertenezca a esa empresa.

        Returns:
            EmpleadoResponse con todos los campos del empleado.

        Raises:
            AppError: EMPLEADO_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
        """
        return empleado_or_404(self._repo.find_by_id(str(id), empresa_id))
