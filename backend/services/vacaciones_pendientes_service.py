"""
Servicio de días de vacaciones PENDIENTES (los que no se tomaron).
Flujo: router → service → repository → DB

Reglas de negocio:
  - empresa_id se hereda del empleado (no lo provee el usuario), igual que en vacaciones.
  - Un registro por (empleado, período): lo garantiza la UNIQUE de la migración 083, que es
    lo que le da idempotencia al import futuro.
  - dias_liquidados ≤ dias (CHECK en la DB). Entero, no bool: admite liquidación parcial.

🔴 DOS EJES QUE SE COMPONEN POR INTERSECCIÓN, nunca uno en lugar del otro:
  - empresa   → frontera multiempresa. Va en el WHERE del repo (Forma A).
  - ownership → dentro de mi empresa, a qué empleados llego por mi rol. VACACIONES está en
    MANDOS_MEDIOS_SECCIONES, así que un mandos_medios SÍ llega a estos endpoints: sin el eje
    de ownership podría cargar días a nombre de un empleado que no es su subordinado. Por eso
    el target se valida con `ensure_empleado_visible` (empresa ∩ ownership) y NO con
    `ensure_empleado_de_empresa`, que alcanza solo para módulos fuera de esa lista.
  Los listados componen los ejes vía `_alcance_mandos.alcance_listado`, que envuelve al
  `_ownership_filter.resolver_empleado_ids` de las 13 superficies de vacaciones/ausencias. Un
  `.eq()` propio que lo esquive no da error: devuelve filas de empleados que ese rol no debería ver.
  🔴 Y para `mandos_medios` el eje de EMPRESA no restringe —el manager_id lo reemplaza (decisión de
  producto 2/8/2026)—, por eso toda empresa que llega al repo pasa antes por `empresa_efectiva`.
  El porqué y la invariante de la que depende, en `services/_alcance_mandos.py`.

🔴 EL BLOQUEO POR PERÍODO CERRADO NO SE APLICA ACÁ, y es deliberado. Cuatro razones:
  1. `verificar_periodo_abierto` compara el RANGO DE FECHAS del registro contra los períodos
     cerrados. Un pendiente no tiene fechas: no es un hecho en el calendario, es un saldo.
  2. Mapear `periodo` al rango [1/1/año, 31/12/año] sería una regla mucho más agresiva de la
     que nadie pidió: `_periodo_utils._solapa` es solapamiento, así que UN SOLO día cerrado
     de 2024 bloquearía TODOS los pendientes de 2024.
  3. `periodos_cerrados` tiene 0 filas en producción: hoy ninguna de las dos variantes se
     puede probar contra datos reales.
  4. La regla solo aplica a mandos_medios (_periodo_utils.py:57).
  Revisar cuando pasen las dos cosas: que RRHH cierre un período de verdad, y que se defina
  si los días no usados se acumulan al año siguiente (de eso depende que cerrar un período
  signifique algo para un pendiente).
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_ownership_repo import EmpleadoOwnershipRepo
from repositories.empleado_repo import EmpleadoRepo
from repositories.vacaciones_pendientes_repo import VacacionesPendientesRepo
from repositories._scope_filtros import empleados_de_proyecto
from schemas.vacaciones_pendientes import (
    VacacionPendienteCreate, VacacionPendienteListResponse,
    VacacionPendienteResponse, VacacionPendienteUpdate,
)
from services._audit_payloads_vacaciones import (
    payload_alta_pendiente, payload_baja_pendiente, payload_update_pendiente,
)
from services._alcance_mandos import alcance_listado, empresa_efectiva
from services._empleado_scope import ensure_empleado_visible
from services.audit_service import AuditService
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError
from utils.logger import logger


class VacacionesPendientesService:
    def __init__(self, repo: Optional[VacacionesPendientesRepo] = None,
                 audit: Optional[AuditService] = None,
                 ownership_repo: Optional[EmpleadoOwnershipRepo] = None,
                 empleado_repo: Optional[EmpleadoRepo] = None) -> None:
        self._repo = repo or VacacionesPendientesRepo()
        self._audit = audit or AuditService()
        self._ownership = ownership_repo or EmpleadoOwnershipRepo()
        self._empleados = empleado_repo or EmpleadoRepo()

    def _or_404(self, row: Optional[VacacionPendienteResponse]) -> VacacionPendienteResponse:
        """Literal ÚNICO del 404. Mismo code y mensaje para 'no existe', 'es de otra empresa' y
        'está fuera del alcance de tu rol' —nunca un 403—: un status o un texto distinto
        confirmaría que el registro existe y es de otro (oráculo de enumeración)."""
        if not row:
            raise AppError("Registro de días pendientes no encontrado", "VACACION_PENDIENTE_NOT_FOUND", 404)
        return row

    def _gestionable(self, row: Optional[VacacionPendienteResponse], usuario_id, rol) -> VacacionPendienteResponse:
        """Empresa (ya aplicada en el WHERE del repo) ∩ ownership. Los dos fallos → el mismo 404."""
        row = self._or_404(row)
        if not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, self._ownership):
            return self._or_404(None)
        return row

    def get_all(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None,
                area_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None,
                page: int = 1, page_size: int = 20,
                proyecto_id: Optional[UUID] = None) -> VacacionPendienteListResponse:
        """Página de días pendientes filtrada por empresa/área/empleado/proyecto ∩ ownership.
        `vacio` → devuelve vacío SIN consultar la tabla (fail-closed del contrato de la tupla)."""
        proyecto_ids = empleados_de_proyecto(proyecto_id) if proyecto_id else None
        empresa, empleado_ids, vacio = alcance_listado(
            user_id, rol, empresa_id, area_id, empleado_id, self._ownership, proyecto_ids)
        items, total = ([], 0) if vacio else self._repo.find_all(empresa, empleado_ids, page, page_size)
        return VacacionPendienteListResponse(items=items, total=total)

    def get_by_empleado(self, empleado_id: UUID, user_id: Optional[str] = None,
                        rol: Optional[str] = None, empresa_id: Optional[UUID] = None,
                        ) -> VacacionPendienteListResponse:
        """Días pendientes de un empleado. Gate empresa ∩ ownership sobre el empleado target."""
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        ensure_empleado_visible(self._empleados, self._ownership, empleado_id, empresa_id, user_id, rol)
        items = self._repo.find_by_empleado(str(empleado_id), empresa_id)
        return VacacionPendienteListResponse(items=items, total=len(items))

    def crear(self, data: VacacionPendienteCreate, created_by: str, rol: Optional[str] = None,
              empresa_id: Optional[UUID] = None) -> VacacionPendienteResponse:
        """Registra días no tomados de un período. La empresa sale del EMPLEADO, no del header."""
        empleado = ensure_empleado_visible(
            self._empleados, self._ownership, data.empleado_id,
            empresa_efectiva(empresa_id, rol), created_by, rol)
        if data.dias_liquidados > data.dias:
            raise AppError("Los días liquidados no pueden superar los días pendientes",
                           "DIAS_LIQUIDADOS_INVALIDOS", 422)
        row = self._repo.crear({
            "empleado_id": str(data.empleado_id), "empresa_id": empleado.empresa_id,
            "periodo": data.periodo, "dias": data.dias,
            "dias_liquidados": data.dias_liquidados, "comentario": data.comentario,
        })
        self._audit.registrar(**payload_alta_pendiente(row, created_by))
        logger.info("Días de vacaciones pendientes registrados",
                    extra={"registro_id": row.id, "empleado_id": str(data.empleado_id), "periodo": data.periodo})
        return row

    def actualizar(self, id: UUID, data: VacacionPendienteUpdate, empresa_id: Optional[UUID] = None,
                   usuario_id: Optional[str] = None, rol: Optional[str] = None) -> VacacionPendienteResponse:
        """Edita el registro (típicamente `dias_liquidados`). Gate empresa ∩ ownership antes de escribir."""
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        prior = self._gestionable(self._repo.find_by_id(str(id), empresa_id), usuario_id, rol)
        patch = data.model_dump(exclude_unset=True, exclude_none=True)
        if patch.get("dias_liquidados", 0) > patch.get("dias", prior.dias):
            raise AppError("Los días liquidados no pueden superar los días pendientes",
                           "DIAS_LIQUIDADOS_INVALIDOS", 422)
        nuevo = self._or_404(self._repo.update(str(id), patch, empresa_id))
        self._audit.registrar(**payload_update_pendiente(prior, nuevo, usuario_id))
        return nuevo

    def eliminar(self, id: UUID, empresa_id: Optional[UUID] = None,
                 usuario_id: Optional[str] = None, rol: Optional[str] = None) -> None:
        """Borra el registro. Audita con el snapshot tomado ANTES del delete."""
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        prior = self._gestionable(self._repo.find_by_id(str(id), empresa_id), usuario_id, rol)
        if not self._repo.delete(str(id), empresa_id):
            self._or_404(None)
        self._audit.registrar(**payload_baja_pendiente(prior, usuario_id))
        logger.info("Días de vacaciones pendientes eliminados", extra={"registro_id": str(id)})
