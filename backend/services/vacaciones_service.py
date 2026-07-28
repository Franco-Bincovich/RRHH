"""
Servicio de vacaciones. Lógica de negocio del módulo de Vacaciones.
Flujo: router → service → repository → DB

Reglas de negocio:
  - empresa_id se hereda del empleado (no lo provee el usuario).
  - dias = (fecha_hasta - fecha_desde).days + 1  (días corridos, extremos incluidos).
  - Solapamiento: solo entre solicitudes del MISMO empleado y MISMO tipo.
    Tipos distintos pueden coexistir en las mismas fechas.
  - Estado derivado: cancelada > planificada (futuro) > tomada (presente o pasado).
  - Saldo: solo el tipo 'vacaciones' descuenta (gozados + pedidos). Los demás tipos son adicionales.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from repositories.empleado_ownership_repo import EmpleadoOwnershipRepo
from repositories.empleado_repo import EmpleadoRepo
from repositories.periodo_repo import PeriodoRepo
from repositories.vacaciones_repo import VacacionesRepo
from schemas.vacaciones import (
    SaldoVacacionesResponse, SolicitudVacacionesCreate,
    SolicitudVacacionesListResponse, SolicitudVacacionesResponse,
)
from services._audit_payloads import payload_cancelacion_vacacion
from services._empleado_scope import ensure_empleado_visible
from repositories._scope_filtros import empleados_de_proyecto
from services._ownership_filter import resolver_empleado_ids
from services._periodo_utils import verificar_periodo_abierto
from services._vacaciones_export import construir_filas_export
from services._vacaciones_saldo import calcular_saldo
from services._vacaciones_utils import derive_estado
from services._vacaciones_write import crear
from services.audit_service import AuditService
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services.export import Descarga, build_export
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError
from utils.logger import logger


class VacacionesService:
    def __init__(self, repo: Optional[VacacionesRepo] = None, audit: Optional[AuditService] = None, periodo_repo: Optional[PeriodoRepo] = None, ownership_repo: Optional[EmpleadoOwnershipRepo] = None, empleado_repo: Optional[EmpleadoRepo] = None) -> None:
        self._repo = repo or VacacionesRepo()
        self._audit = audit or AuditService()
        self._periodos = periodo_repo or PeriodoRepo()
        self._ownership = ownership_repo or EmpleadoOwnershipRepo()
        self._empleados = empleado_repo or EmpleadoRepo()

    def get_all(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None, area_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None, estado: Optional[str] = None, page: int = 1, page_size: int = 20, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None, proyecto_id: Optional[UUID] = None) -> SolicitudVacacionesListResponse:
        """Página de solicitudes (estado derivado) filtrada por empresa/área/empleado/estado y ownership. vacio → devuelve vacío sin consultar.
        `today` se calcula una vez: mismo valor para el filtro server-side y para derive_estado (sin desalineación en los bordes).
        fecha_desde/fecha_hasta acotan por SOLAPAMIENTO con el rango (ver repositories/_rango_fechas): una solicitud que
        empieza antes del rango pero lo cruza ENTRA. Se compone por INTERSECCIÓN con el ownership, que ya viajó en empleado_ids."""
        today = date.today()
        proyecto_ids = empleados_de_proyecto(proyecto_id) if proyecto_id else None
        empleado_ids, vacio = resolver_empleado_ids(user_id, rol, empresa_id, area_id, empleado_id, self._ownership, proyecto_ids)
        rows, total = ([], 0) if vacio else self._repo.find_all(empresa_id, empleado_ids, page, page_size, estado, today, desde=fecha_desde, hasta=fecha_hasta)
        return SolicitudVacacionesListResponse(items=[derive_estado(r, today) for r in rows], total=total)

    def exportar(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None, formato: str = "excel", area_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None, estado: Optional[str] = None, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None, proyecto_id: Optional[UUID] = None) -> Descarga:
        """Exporta vacaciones (columnas legibles, sin UUIDs) respetando ownership; acotable por área/empleado/estado (mismos filtros que el listado)."""
        pagina = self.get_all(user_id, rol, empresa_id, area_id, empleado_id, estado, 1, LIMITE_FILAS_EXPORT, fecha_desde, fecha_hasta, proyecto_id)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        filas = construir_filas_export(pagina.items)
        return build_export(nombre="Vacaciones", datos={"Vacaciones": filas}, filename_base="vacaciones", formato=formato)

    def get_by_empleado(self, empleado_id: UUID, user_id: Optional[str] = None, rol: Optional[str] = None, empresa_id: Optional[UUID] = None) -> SolicitudVacacionesListResponse:
        """Vacaciones (no canceladas) de un empleado, con estado derivado. Gate empresa ∩ ownership:
        un empleado ajeno (otra empresa, o fuera del alcance de un mando) da el MISMO 404 que uno inexistente."""
        ensure_empleado_visible(self._empleados, self._ownership, empleado_id, empresa_id, user_id, rol)
        today = date.today()
        items = [derive_estado(r, today) for r in self._repo.find_vacaciones_empleado(str(empleado_id), empresa_id)]
        return SolicitudVacacionesListResponse(items=items, total=len(items))

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """Detalle de una solicitud. Gate empresa ∩ ownership (empresa en el WHERE del repo, luego
        el rol): una ajena a un mando da el MISMO 404 que una inexistente, igual que cancel."""
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row or not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, self._ownership):
            raise AppError("Solicitud de vacaciones no encontrada", "VACACION_NOT_FOUND", 404)
        return derive_estado(row, date.today())

    def create(self, data: SolicitudVacacionesCreate, created_by: str, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """Registra un período de vacaciones. Delegado a _vacaciones_write.crear
        (ownership + empresa del empleado + período + solapamiento)."""
        return crear(self._repo, self._periodos, self._ownership, data, created_by, rol)

    def cancel(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """
        Cancela una solicitud seteando cancelada=True (no borra la fila — preserva historial).
        Registra el evento de auditoría tras la cancelación exitosa (usuario_id = operador).

        Ownership: un registro ajeno a un mando responde 404 (igual que inexistente), para no
        confirmar la existencia de solicitudes de empleados que no gestiona.

        Raises:
            AppError: VACACION_NOT_FOUND (404) si el ID no existe o no es gestionable por el rol.
            AppError: YA_CANCELADA (422) si ya estaba cancelada.
        """
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row or not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, self._ownership):
            raise AppError("Solicitud de vacaciones no encontrada", "VACACION_NOT_FOUND", 404)
        verificar_periodo_abierto(row.empresa_id, "vacaciones", rol, desde=row.fecha_desde, hasta=row.fecha_hasta, repo=self._periodos)
        if row.cancelada:
            raise AppError("La solicitud ya está cancelada", "YA_CANCELADA", 422)
        updated = self._repo.cancel(str(id), empresa_id)
        self._audit.registrar(**payload_cancelacion_vacacion(row, updated, usuario_id, row.empresa_id))
        logger.info("Vacaciones canceladas", extra={"solicitud_id": str(id)})
        return derive_estado(updated, date.today())  # type: ignore[arg-type]

    def get_saldo(self, empleado_id: UUID, user_id: Optional[str] = None, rol: Optional[str] = None, empresa_id: Optional[UUID] = None) -> SaldoVacacionesResponse:
        """Saldo anual de vacaciones pagas. Gate empresa ∩ ownership antes de calcular; delegado a
        calcular_saldo (helper). Raises EMPLEADO_NOT_FOUND (404) —mismo 404 para ajeno e inexistente—."""
        ensure_empleado_visible(self._empleados, self._ownership, empleado_id, empresa_id, user_id, rol)
        return calcular_saldo(self._repo, empleado_id, empresa_id)
