"""
Router de la agenda de eventos — LECTURAS. Montado en /api/eventos.

Las escrituras viven en `eventos_agenda_escrituras.py`, sobre el MISMO prefijo — el corte es por
límite de líneas (80/80) y las rutas no cambian. Molde: `clientes.py` / `clientes_escrituras.py`.

🔴 EL LISTADO NACE PAGINADO, con `page_size` topeado en 100. Un `page_size` sin techo convierte
el listado en un export encubierto que esquiva `verificar_limite_export` — que acá además no
existe, porque **este módulo no tiene export** (decisión de producto: una agenda de recordatorios
no es un dato que se lleve a Excel; lo que se hace con un evento es resolverlo).

🔑 `sujeto(request)` viaja en LOS TRES endpoints, y es lo que hace que un evento privado de otro
usuario no aparezca. Sin él el service recibe `user_id=None`, que NO restringe: la agenda entera
quedaría pública. Vive en `utils/sujeto.py` desde que este módulo fue el segundo en necesitarlo.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.evento_agenda import EventoListResponse, EventoResponse
from services.evento_agenda_service import EventoAgendaService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.sujeto import sujeto

router = APIRouter()
SECCION = Seccion.EVENTOS


def _service() -> EventoAgendaService:
    return EventoAgendaService()


@router.get("", response_model=EventoListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_eventos(
    request: Request,
    incluir_resueltas: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: EventoAgendaService = Depends(_service),
) -> EventoListResponse:
    return service.listar(page, page_size, get_empresa_id(request), *sujeto(request),
                          incluir_resueltas=incluir_resueltas)


# 🔴 `/pendientes` va ANTES de `/{id}`: si fuera después, FastAPI resuelve por ORDEN DE
# DECLARACIÓN y "pendientes" matchearía como el path param `id: UUID` → 422 en vez de la lista.
@router.get("/pendientes", response_model=list[EventoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def eventos_pendientes(
    request: Request,
    service: EventoAgendaService = Depends(_service),
) -> list[EventoResponse]:
    """Los que ya entraron en su ventana de aviso. Sin paginar y sin resueltos.

    Es lo que va a consumir la tarjeta del dashboard (sesión 2). Sale de acá y no de
    `dashboard_service` porque el dato es de este módulo: el panel lo va a leer, no lo calcula.
    """
    return service.pendientes(get_empresa_id(request), *sujeto(request))


@router.get("/{id}", response_model=EventoResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_evento(
    id: UUID,
    request: Request,
    service: EventoAgendaService = Depends(_service),
) -> EventoResponse:
    return service.obtener(id, get_empresa_id(request), *sujeto(request))
