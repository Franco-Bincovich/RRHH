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


# ✅ Acá vivió `GET /pendientes` ("lo que va a consumir la tarjeta del dashboard, sesión 2").
# Esa sesión llegó (A6, 19/8/2026) y la tarjeta consume `GET /api/dashboard/atencion`, que
# devuelve los eventos pendientes JUNTO con las alertas calculadas: este endpoint quedaba
# huérfano para siempre y se BORRÓ. La lógica no se movió: `EventoAgendaService.pendientes`
# sigue acá y la consume el panel. (Con la ruta se fue también la nota sobre declarar
# `/pendientes` antes de `/{id}` — sin ruta literal, no hay colisión que ordenar.)
@router.get("/{id}", response_model=EventoResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_evento(
    id: UUID,
    request: Request,
    service: EventoAgendaService = Depends(_service),
) -> EventoResponse:
    return service.obtener(id, get_empresa_id(request), *sujeto(request))
