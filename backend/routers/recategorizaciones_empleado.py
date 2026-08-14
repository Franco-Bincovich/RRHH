"""
Historial de recategorizaciones DENTRO DE LA FICHA del colaborador.

Montado en `/api` con la ruta anidada `/empleados/{empleado_id}/recategorizaciones`, igual que
`cesiones.py`. Es la SEGUNDA VISTA de la misma tabla, y tiene forma distinta a propósito:

  · la planilla (`/api/recategorizaciones`) es un listado de empresa → PAGINADO, con filtros;
  · esto es el historial de UNA persona → LISTA PLANA, sin paginar, más reciente primero.

Son una o dos por persona por año: paginar acá sería un paginador de una sola página, y
obligaría al front a manejar estado de página en un bloque de la ficha que no lo necesita. Molde
exacto: `GET /api/costos/nomina/empleado/{empleado_id}`, que alimenta el historial salarial de
esa misma ficha.

🔴 GATEA CON `Seccion.RECATEGORIZACIONES` Y NO CON `EMPLEADOS`, aunque se consuma desde la ficha
de empleados. Es el mismo criterio, escrito en `routers/costos.py:63-76`, por el que el
historial salarial gatea con COSTOS: el permiso lo decide de QUÉ es el dato, no en qué pantalla
se muestra. Hoy no existe un rol con acceso a una sección y no a la otra, pero los roles cambian
y este endpoint no se va a volver a mirar.

⚠️ La barrera de EMPRESA se aplica en el service sobre el EMPLEADO objetivo, no acá: el
`empresa_id` del header no valida a qué empleado apuntás.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers._recategorizaciones_costos import puede_ver_costos
from schemas.recategorizacion import RecategorizacionResponse
from services.recategorizacion_service import RecategorizacionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.RECATEGORIZACIONES


def _service() -> RecategorizacionService:
    return RecategorizacionService()


@router.get(
    "/empleados/{empleado_id}/recategorizaciones",
    response_model=List[RecategorizacionResponse],
    dependencies=[Depends(require_permission(SECCION, Accion.READ))],
)
async def historial_recategorizaciones(
    empleado_id: UUID,
    request: Request,
    service: RecategorizacionService = Depends(_service),
) -> List[RecategorizacionResponse]:
    """Historial completo del colaborador, del más reciente al más viejo. Sin paginar.

    Lista vacía si nunca lo recategorizaron, que NO es un error: hoy es el caso de los 31.
    """
    return service.historial_empleado(empleado_id, get_empresa_id(request),
                                      puede_ver_costos=puede_ver_costos(request))
