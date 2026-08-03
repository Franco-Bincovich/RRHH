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

🔴 Para `mandos_medios` la empresa NO restringe: el manager_id la reemplaza (decisión de producto
2/8/2026). Por eso cada método pasa la empresa por `empresa_efectiva` antes de tocar el repo, y los
listados van por `alcance_listado`. El porqué —y la invariante de la que depende— en
`services/_alcance_mandos.py`. No lo repliques en otro módulo sin leerlo.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from repositories.empleado_ownership_repo import EmpleadoOwnershipRepo
from repositories.empleado_repo import EmpleadoRepo
from repositories.periodo_repo import PeriodoRepo
from repositories.vacaciones_pendientes_repo import VacacionesPendientesRepo
from repositories.vacaciones_repo import VacacionesRepo
from schemas.vacaciones import (
    SaldoVacacionesResponse, SolicitudVacacionesCreate,
    SolicitudVacacionesListResponse, SolicitudVacacionesResponse, SolicitudVacacionesUpdate,
)
from services._alcance_mandos import alcance_listado, empresa_efectiva
from services._empleado_scope import ensure_empleado_visible
from repositories._scope_filtros import empleados_de_proyecto
from services._vacaciones_export import construir_filas_export
from services._vacaciones_saldo import calcular_saldo
from services._vacaciones_utils import derive_estado
from services._vacaciones_write import actualizar, cancel, crear
from services.audit_service import AuditService
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services.export import Descarga, build_export
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError


class VacacionesService:
    def __init__(self, repo: Optional[VacacionesRepo] = None, audit: Optional[AuditService] = None, periodo_repo: Optional[PeriodoRepo] = None, ownership_repo: Optional[EmpleadoOwnershipRepo] = None, empleado_repo: Optional[EmpleadoRepo] = None, pendientes_repo: Optional[VacacionesPendientesRepo] = None) -> None:
        self._repo = repo or VacacionesRepo()
        self._audit = audit or AuditService()
        self._periodos = periodo_repo or PeriodoRepo()
        self._ownership = ownership_repo or EmpleadoOwnershipRepo()
        self._empleados = empleado_repo or EmpleadoRepo()
        self._pendientes = pendientes_repo or VacacionesPendientesRepo()

    def get_all(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None, area_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None, estado: Optional[str] = None, page: int = 1, page_size: int = 20, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None, proyecto_id: Optional[UUID] = None) -> SolicitudVacacionesListResponse:
        """Página de solicitudes (estado derivado) filtrada por empresa/área/empleado/estado y ownership. vacio → devuelve vacío sin consultar.
        `today` se calcula una vez: mismo valor para el filtro server-side y para derive_estado (sin desalineación en los bordes).
        fecha_desde/fecha_hasta acotan por SOLAPAMIENTO con el rango (ver repositories/_rango_fechas): una solicitud que
        empieza antes del rango pero lo cruza ENTRA. Se compone por INTERSECCIÓN con el ownership, que ya viajó en empleado_ids."""
        today = date.today()
        proyecto_ids = empleados_de_proyecto(proyecto_id) if proyecto_id else None
        empresa, empleado_ids, vacio = alcance_listado(user_id, rol, empresa_id, area_id, empleado_id, self._ownership, proyecto_ids)
        rows, total = ([], 0) if vacio else self._repo.find_all(empresa, empleado_ids, page, page_size, estado, today, desde=fecha_desde, hasta=fecha_hasta)
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
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        ensure_empleado_visible(self._empleados, self._ownership, empleado_id, empresa_id, user_id, rol)
        today = date.today()
        items = [derive_estado(r, today) for r in self._repo.find_vacaciones_empleado(str(empleado_id), empresa_id)]
        return SolicitudVacacionesListResponse(items=items, total=len(items))

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """Detalle de una solicitud. Gate empresa ∩ ownership (empresa en el WHERE del repo, luego
        el rol): una ajena a un mando da el MISMO 404 que una inexistente, igual que cancel."""
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row or not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, self._ownership):
            raise AppError("Solicitud de vacaciones no encontrada", "VACACION_NOT_FOUND", 404)
        return derive_estado(row, date.today())

    def create(self, data: SolicitudVacacionesCreate, created_by: str, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """Registra un período de vacaciones. Delegado a _vacaciones_write.crear
        (ownership + empresa del empleado + período + solapamiento)."""
        return crear(self._repo, self._periodos, self._ownership, data, created_by, rol)

    def cancel(self, id: UUID, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """Cancela una solicitud (cancelada=True, no borra). Delegado a _vacaciones_write.cancel."""
        return cancel(self._repo, self._periodos, self._ownership, self._audit, id,
                      empresa_efectiva(empresa_id, rol), usuario_id, rol)

    def actualizar(self, id: UUID, data: SolicitudVacacionesUpdate, empresa_id: Optional[UUID] = None,
                   usuario_id: Optional[str] = None, rol: Optional[str] = None) -> SolicitudVacacionesResponse:
        """Edición parcial de una solicitud. Delegado a _vacaciones_write.actualizar."""
        return actualizar(self._repo, self._ownership, self._audit, id, data,
                          empresa_efectiva(empresa_id, rol), usuario_id, rol)

    def get_saldo(self, empleado_id: UUID, user_id: Optional[str] = None, rol: Optional[str] = None, empresa_id: Optional[UUID] = None) -> SaldoVacacionesResponse:
        """Saldo de vacaciones por período, con vencimiento. Gate empresa ∩ ownership antes de
        calcular; delegado a calcular_saldo (helper). Raises EMPLEADO_NOT_FOUND (404) —mismo 404
        para ajeno e inexistente—.

        Los pendientes entran al cálculo porque sus días LIQUIDADOS consumen cupo (mig 083). El
        repo viaja como parámetro, no se instancia adentro del helper: el helper es la costura
        que testea test_saldo_service_vs_r11 y necesita poder recibir un doble."""
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        ensure_empleado_visible(self._empleados, self._ownership, empleado_id, empresa_id, user_id, rol)
        return calcular_saldo(self._repo, empleado_id, empresa_id, self._pendientes)
