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
from services._alcance_mandos import alcance_listado, empresa_efectiva
from services._empleado_scope import ensure_empleado_visible
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._vacaciones_pendientes_export import construir_filas_export
from services._vacaciones_pendientes_write import actualizar as _actualizar
from services._vacaciones_pendientes_write import crear as _crear
from services._vacaciones_pendientes_write import eliminar as _eliminar
from services.audit_service import AuditService
from services.export import Descarga, build_export


class VacacionesPendientesService:
    def __init__(self, repo: Optional[VacacionesPendientesRepo] = None,
                 audit: Optional[AuditService] = None,
                 ownership_repo: Optional[EmpleadoOwnershipRepo] = None,
                 empleado_repo: Optional[EmpleadoRepo] = None) -> None:
        self._repo = repo or VacacionesPendientesRepo()
        self._audit = audit or AuditService()
        self._ownership = ownership_repo or EmpleadoOwnershipRepo()
        self._empleados = empleado_repo or EmpleadoRepo()

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

    def exportar(self, user_id: str, rol: str, empresa_id: Optional[UUID] = None,
                 formato: str = "excel", area_id: Optional[UUID] = None,
                 empleado_id: Optional[UUID] = None, proyecto_id: Optional[UUID] = None) -> Descarga:
        """Exporta los días pendientes con los MISMOS filtros que el listado.

        🔴 VA POR `get_all`, NO POR EL REPO. VACACIONES está en MANDOS_MEDIOS_SECCIONES, así que
        el universo de este módulo NO lo acota solo la empresa: lo acota el OWNERSHIP (a qué
        empleados llego por mi `manager_id`), que se resuelve en `alcance_listado`. Un export que
        le pegara al repo por su cuenta —aunque le pasara el `empresa_id`— le entregaría a un
        `mandos_medios` los días de gente que no puede ver en ninguna pantalla, en un archivo
        descargable y sin ningún error. Reusar el listado es lo que hace que eso no pueda pasar.

        El total sale con `count="exact"` de la misma consulta, así que el chequeo de límite
        respeta los filtros y actúa antes de traer nada grande.
        """
        pagina = self.get_all(user_id, rol, empresa_id, area_id, empleado_id,
                              1, LIMITE_FILAS_EXPORT, proyecto_id)
        verificar_limite_export(pagina.total)
        datos = {"Días pendientes": construir_filas_export(pagina.items)}
        return build_export(nombre="Días de vacaciones pendientes", datos=datos,
                            filename_base="vacaciones_pendientes", formato=formato)

    def get_by_empleado(self, empleado_id: UUID, user_id: Optional[str] = None,
                        rol: Optional[str] = None, empresa_id: Optional[UUID] = None,
                        ) -> VacacionPendienteListResponse:
        """Días pendientes de un empleado. Gate empresa ∩ ownership sobre el empleado target."""
        empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
        ensure_empleado_visible(self._empleados, self._ownership, empleado_id, empresa_id, user_id, rol)
        items = self._repo.find_by_empleado(str(empleado_id), empresa_id)
        return VacacionPendienteListResponse(items=items, total=len(items))

    # Las tres ESCRITURAS viven en services/_vacaciones_pendientes_write.py (extraídas por
    # límite de líneas), junto con el literal único del 404 del módulo.

    def crear(self, data: VacacionPendienteCreate, created_by: str, rol: Optional[str] = None,
              empresa_id: Optional[UUID] = None) -> VacacionPendienteResponse:
        """Registra días no tomados de un período. Ver _vacaciones_pendientes_write.crear."""
        return _crear(self._repo, self._audit, self._empleados, self._ownership,
                      data, created_by, rol, empresa_id)

    def actualizar(self, id: UUID, data: VacacionPendienteUpdate, empresa_id: Optional[UUID] = None,
                   usuario_id: Optional[str] = None, rol: Optional[str] = None) -> VacacionPendienteResponse:
        """Edita el registro. Ver _vacaciones_pendientes_write.actualizar."""
        return _actualizar(self._repo, self._audit, self._ownership, id, data,
                           empresa_id, usuario_id, rol)

    def eliminar(self, id: UUID, empresa_id: Optional[UUID] = None,
                 usuario_id: Optional[str] = None, rol: Optional[str] = None) -> None:
        """Borra el registro. Ver _vacaciones_pendientes_write.eliminar."""
        _eliminar(self._repo, self._audit, self._ownership, id, empresa_id, usuario_id, rol)
