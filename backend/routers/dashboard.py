"""
Router del Dashboard Ejecutivo.
Ruta protegida por AuthMiddleware (requiere JWT válido).
empresa_id para lectura: header X-Empresa-Id (filtro de vista, None = consolidado).

El panel "Requiere tu atención" (A6) vive acá y no en un router propio:
`registro_routers.py` está en 197/200 y montarlo en el router del dashboard —que es su
pantalla— evita la división. `sujeto(request)` viaja en los dos endpoints nuevos: sin él, un
evento privado ajeno aparecería en el panel (mismo motivo que en `eventos_agenda.py`).
"""
from fastapi import APIRouter, Depends, Request

from schemas.dashboard import DashboardResponse
from schemas.dashboard_atencion import AtencionResponse, ResolverAtencionRequest
from schemas.evento_agenda import EventoResponse
from services.dashboard_atencion_service import DashboardAtencionService
from services.dashboard_service import DashboardService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.sujeto import sujeto

router = APIRouter()
SECCION = Seccion.DASHBOARD


def _service() -> DashboardService:
    return DashboardService()


def _atencion() -> DashboardAtencionService:
    return DashboardAtencionService()


@router.get("", response_model=DashboardResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_dashboard(
    request: Request,
    service: DashboardService = Depends(_service),
) -> DashboardResponse:
    empresa_id = get_empresa_id(request)
    return service.get_dashboard(empresa_id)


@router.get("/atencion", response_model=AtencionResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_atencion(
    request: Request,
    service: DashboardAtencionService = Depends(_atencion),
) -> AtencionResponse:
    """Las alertas calculadas y las manuales, en UNA lista distinguible por `origen`."""
    return service.listar(get_empresa_id(request), *sujeto(request))


# 🔴 Gate `EVENTOS + WRITE`, no DASHBOARD: resolver una alerta manual ESCRIBE un evento de
# agenda (mismas columnas, misma auditoría que `PUT /api/eventos/{id}/resuelta`). El permiso
# sigue a la escritura, no a la pantalla desde la que se dispara.
@router.post("/atencion/resolver", response_model=EventoResponse, dependencies=[Depends(require_permission(Seccion.EVENTOS, Accion.WRITE))])
async def resolver_atencion(
    request: Request,
    body: ResolverAtencionRequest,
    service: DashboardAtencionService = Depends(_atencion),
) -> EventoResponse:
    """Resuelve una alerta MANUAL. Una calculada responde ALERTA_NO_RESOLUBLE (409)."""
    return service.resolver(body, get_empresa_id(request), *sujeto(request))
