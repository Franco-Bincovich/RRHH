"""
Escrituras de la agenda de eventos: alta, edición, toggle de resuelta y baja.

Separado de `eventos_agenda.py` y montado en el MISMO prefijo, así que las rutas no cambian.

🔴 SÍ HAY DELETE, al revés que recategorizaciones — y la asimetría entre los dos módulos es la
decisión, no un descuido. Una recategorización es un HECHO histórico del que cuelga la cadena de
`*_anterior`; un evento es un RECORDATORIO del que no cuelga nada, se carga a mano y alguien se
va a equivocar de fecha. La auditoría guarda el snapshot previo, así que borrar no pierde el
rastro. Molde del borrado con confirmación: `vacantes_escrituras.py`.

🔴 EL TOGGLE DE RESUELTA ES **UN** ENDPOINT (`PUT /{id}/resuelta`) Y NO DOS. Resolver es
reversible (decisión de producto), así que "resolver" y "desresolver" son el mismo cambio de
estado con distinto valor: dos rutas obligarían al front a elegir cuál llamar mirando un estado
que puede estar viejo, y dejarían dos caminos escribiendo las mismas tres columnas.

⚠️ EL ALTA USA `require_empresa_id` Y EL RESTO `get_empresa_id`, y no es una inconsistencia: al
CREAR hay que decidir de qué empresa es el evento y la vista consolidada no lo dice, así que el
error le pide al usuario que elija en el selector. Al EDITAR o BORRAR, la empresa ya está en la
fila y el header solo acota qué filas se alcanzan — `None` ahí es la vista consolidada legítima.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from schemas.evento_agenda import EventoCreate, EventoResponse, EventoResuelta, EventoUpdate
from services.evento_agenda_service import EventoAgendaService
from utils.empresa import get_empresa_id, require_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.sujeto import sujeto

router = APIRouter()
SECCION = Seccion.EVENTOS
_WRITE = Depends(require_permission(SECCION, Accion.WRITE))


def _service() -> EventoAgendaService:
    return EventoAgendaService()


@router.post("", response_model=EventoResponse, status_code=201, dependencies=[_WRITE])
async def create_evento(
    request: Request,
    body: EventoCreate,
    service: EventoAgendaService = Depends(_service),
) -> EventoResponse:
    # `sujeto(request)[0]` = el autor. NO viaja en el body: aceptarlo permitiría cargar un evento
    # privado a nombre de otro, o sea una fila que ese otro no puede ver ni borrar.
    return service.crear(body, require_empresa_id(request), sujeto(request)[0])


@router.put("/{id}", response_model=EventoResponse, dependencies=[_WRITE])
async def update_evento(
    id: UUID,
    body: EventoUpdate,
    request: Request,
    service: EventoAgendaService = Depends(_service),
) -> EventoResponse:
    return service.editar(id, body, get_empresa_id(request), *sujeto(request))


@router.put("/{id}/resuelta", response_model=EventoResponse, dependencies=[_WRITE])
async def set_resuelta(
    id: UUID,
    body: EventoResuelta,
    request: Request,
    service: EventoAgendaService = Depends(_service),
) -> EventoResponse:
    return service.resolver(id, body.resuelta, get_empresa_id(request), *sujeto(request))


@router.delete("/{id}", status_code=204, dependencies=[_WRITE])
async def delete_evento(
    id: UUID,
    request: Request,
    service: EventoAgendaService = Depends(_service),
) -> Response:
    service.borrar(id, get_empresa_id(request), *sujeto(request))
    return Response(status_code=204)
