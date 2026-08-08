"""
Escrituras de días de vacaciones PENDIENTES: alta, edición y baja.

Extraído de `vacaciones_pendientes_service.py`, que estaba en 146/150 y no admitía el endpoint
de export. Molde: `_vacaciones_write.py` / `_ausencias_write.py` (los hermanos del módulo) y
`_empresa_logo.py` — funciones libres que reciben sus colaboradores.

POR QUÉ SALIÓ ESTE BLOQUE: las tres escrituras comparten el gate `empresa ∩ ownership` sobre el
empleado target y el MISMO literal de 404, que se va con ellas. Las dos lecturas que quedan en
el service resuelven su alcance por otro camino (`alcance_listado`, que trabaja sobre el
conjunto y no sobre una fila). Cortar acá deja cada criterio en un solo archivo.

🔴 EL 404 ES ÚNICO Y NO SE DUPLICA. `or_404` es el literal canónico del módulo: "no existe",
"es de otra empresa" y "está fuera del alcance de tu rol" salen con el mismo status, code y
mensaje. Nunca un 403 — un status o un texto distinto confirmaría que el registro existe y es
de otro (oráculo de enumeración).

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from typing import Optional
from uuid import UUID

from schemas.vacaciones_pendientes import (
    VacacionPendienteCreate, VacacionPendienteResponse, VacacionPendienteUpdate,
)
from services._alcance_mandos import empresa_efectiva
from services._audit_payloads_vacaciones import (
    payload_alta_pendiente, payload_baja_pendiente, payload_update_pendiente,
)
from services._empleado_scope import ensure_empleado_visible
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError
from utils.logger import logger


def or_404(row: Optional[VacacionPendienteResponse]) -> VacacionPendienteResponse:
    """Literal ÚNICO del 404 del módulo. Ver el encabezado del archivo."""
    if not row:
        raise AppError("Registro de días pendientes no encontrado", "VACACION_PENDIENTE_NOT_FOUND", 404)
    return row


def _gestionable(row, ownership, usuario_id, rol) -> VacacionPendienteResponse:
    """Empresa (ya aplicada en el WHERE del repo) ∩ ownership. Los dos fallos → el mismo 404."""
    row = or_404(row)
    if not puede_gestionar_empleado(usuario_id, rol, row.empleado_id, ownership):
        return or_404(None)
    return row


def crear(repo, audit, empleados, ownership, data: VacacionPendienteCreate, created_by: str,
          rol: Optional[str] = None, empresa_id: Optional[UUID] = None) -> VacacionPendienteResponse:
    """Registra días no tomados de un período. La empresa sale del EMPLEADO, no del header."""
    empleado = ensure_empleado_visible(
        empleados, ownership, data.empleado_id, empresa_efectiva(empresa_id, rol), created_by, rol)
    if data.dias_liquidados > data.dias:
        raise AppError("Los días liquidados no pueden superar los días pendientes",
                       "DIAS_LIQUIDADOS_INVALIDOS", 422)
    row = repo.crear({
        "empleado_id": str(data.empleado_id), "empresa_id": empleado.empresa_id,
        "periodo": data.periodo, "dias": data.dias,
        "dias_liquidados": data.dias_liquidados, "comentario": data.comentario,
    })
    audit.registrar(**payload_alta_pendiente(row, created_by))
    logger.info("Días de vacaciones pendientes registrados",
                extra={"registro_id": row.id, "empleado_id": str(data.empleado_id), "periodo": data.periodo})
    return row


def actualizar(repo, audit, ownership, id: UUID, data: VacacionPendienteUpdate,
               empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None,
               rol: Optional[str] = None) -> VacacionPendienteResponse:
    """Edita el registro (típicamente `dias_liquidados`). Gate empresa ∩ ownership antes de escribir."""
    empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
    prior = _gestionable(repo.find_by_id(str(id), empresa_id), ownership, usuario_id, rol)
    patch = data.model_dump(exclude_unset=True, exclude_none=True)
    if patch.get("dias_liquidados", 0) > patch.get("dias", prior.dias):
        raise AppError("Los días liquidados no pueden superar los días pendientes",
                       "DIAS_LIQUIDADOS_INVALIDOS", 422)
    nuevo = or_404(repo.update(str(id), patch, empresa_id))
    audit.registrar(**payload_update_pendiente(prior, nuevo, usuario_id))
    return nuevo


def eliminar(repo, audit, ownership, id: UUID, empresa_id: Optional[UUID] = None,
             usuario_id: Optional[str] = None, rol: Optional[str] = None) -> None:
    """Borra el registro. Audita con el snapshot tomado ANTES del delete."""
    empresa_id = empresa_efectiva(empresa_id, rol)  # mandos_medios: manda el manager, no la empresa
    prior = _gestionable(repo.find_by_id(str(id), empresa_id), ownership, usuario_id, rol)
    if not repo.delete(str(id), empresa_id):
        or_404(None)
    audit.registrar(**payload_baja_pendiente(prior, usuario_id))
    logger.info("Días de vacaciones pendientes eliminados", extra={"registro_id": str(id)})
