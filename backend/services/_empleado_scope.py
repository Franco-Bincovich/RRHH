"""
Barrera de empresa sobre el empleado TARGET de una operación (helper transversal).

Lo usan los módulos que cuelgan de un empleado y reciben su id de afuera —offboarding,
sucesión, y más adelante onboarding y vacaciones—. No es lo mismo que el filtro de empresa
del repo: `_with_empresa` restringe QUÉ FILA se toca cuando ya elegiste el registro, pero no
dice nada sobre A QUÉ EMPLEADO podés apuntar. Sin esta barrera, un empleado_id de otra
empresa entra igual y la operación se ejecuta sobre él.

Ojo con el orden respecto de la derivación de empresa: estos módulos derivan la empresa DEL
EMPLEADO a propósito (offboarding_service, sucesion_service — está documentado y no se
revierte: define en qué empresa se escribe). Validar primero no contradice eso; al contrario,
una vez que el empleado pasó la barrera, la empresa derivada y la del usuario coinciden por
construcción, así que la derivación queda blindada sin cambiarla.

Devuelve el empleado (no un bool) para que el caller reuse la fila en vez de consultarla dos
veces — es justamente la fila de la que después sale `empleado.empresa_id`.
"""
from typing import Optional
from uuid import UUID

from schemas.empleado import EmpleadoResponse
from services._empleados_utils import empleado_or_404
from services.ownership import puede_gestionar_empleado
from utils.errors import AppError


def ensure_empleado_de_empresa(repo, empleado_id, empresa_id: Optional[UUID]) -> EmpleadoResponse:
    """Carga el empleado validando que sea de `empresa_id`. Lo devuelve para reusar la fila.

    `empresa_id` None = vista consolidada ("Todas las empresas", semántica de get_empresa_id):
    no restringe, cualquier empleado existente pasa.

    El 404 es el MISMO que el de "el empleado no existe" —mismo code y mismo mensaje, nunca un
    403— para no confirmar la existencia de empleados de otra empresa. Se delega en
    `empleado_or_404` en vez de re-lanzar el AppError acá: así el mensaje queda con una sola
    fuente y no puede divergir del resto del sistema.

    Args:
        repo: EmpleadoRepo (o doble de test) — su find_by_id ya filtra por empresa.
        empleado_id: empleado objetivo de la operación (UUID o str).
        empresa_id: empresa activa del request. None = sin restricción.

    Returns:
        EmpleadoResponse del empleado validado.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si no existe o es de otra empresa.
    """
    return empleado_or_404(repo.find_by_id(str(empleado_id), empresa_id))


def ensure_empleado_visible(repo, ownership_repo, empleado_id, empresa_id: Optional[UUID],
                            user_id: Optional[str], rol: Optional[str]) -> EmpleadoResponse:
    """Barrera completa para leer datos de UN empleado: empresa ∩ ownership, en ese orden.

    Son dos ejes independientes y se COMPONEN, no se elige uno:
      - empresa  → de qué organización es el empleado (frontera multiempresa).
      - ownership→ dentro de mi empresa, a qué empleados llego por mi rol. admin_rrhh y
                   gerencia_lectura no tienen restricción; mandos_medios ve su propio registro
                   y sus subordinados directos (criterio único en services.ownership).

    Los dos fallos devuelven el MISMO 404 EMPLEADO_NOT_FOUND que "no existe" —nunca un 403—:
    un mando no debe poder distinguir "no existe" de "existe pero no es tuyo", igual que ya
    hace `cancel` en vacaciones. Reusa `puede_gestionar_empleado`, que resuelve el mismo
    conjunto que los listados (ids_empleados_visibles); NO se define un criterio nuevo.

    Args:
        repo: EmpleadoRepo (o doble) — su find_by_id filtra por empresa.
        ownership_repo: EmpleadoOwnershipRepo (o doble) con find_by_user_id e ids_subordinados.
        empleado_id: empleado objetivo de la lectura.
        empresa_id: empresa activa del request. None = consolidado, no restringe.
        user_id / rol: sujeto del ownership (request.state.user). rol desconocido → fail-closed.

    Returns:
        EmpleadoResponse del empleado validado por ambos ejes.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si no existe, es de otra empresa, o el rol no lo alcanza.
    """
    empleado = ensure_empleado_de_empresa(repo, empleado_id, empresa_id)
    if not puede_gestionar_empleado(user_id, rol, empleado_id, ownership_repo):
        raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)
    return empleado
