"""Router de lecturas de vacaciones POR EMPLEADO (saldo e histórico). Se registra en
/api/vacaciones ANTES del router de vacaciones (rutas estáticas /saldo y /empleado vs /{id}):
si fuera al revés, /{id} matchearía primero y "saldo" entraría como un UUID inválido.

Separado del router principal —que queda con listado, export y escrituras— para darle margen
de líneas al filtro por período. La empresa sale de X-Empresa-Id; el gate empresa ∩ ownership
vive en el service (ensure_empleado_visible), no acá."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.vacaciones import SaldoVacacionesResponse, SolicitudVacacionesListResponse
from services.vacaciones_service import VacacionesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.VACACIONES


def _svc() -> VacacionesService:
    return VacacionesService()


@router.get("/saldo/{empleado_id}", response_model=SaldoVacacionesResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_saldo(empleado_id: UUID, request: Request, service: VacacionesService = Depends(_svc)) -> SaldoVacacionesResponse:
    u = request.state.user
    return service.get_saldo(empleado_id, u.get("id"), u.get("rol"), get_empresa_id(request))


@router.get("/empleado/{empleado_id}", response_model=SolicitudVacacionesListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_vacaciones_empleado(empleado_id: UUID, request: Request, service: VacacionesService = Depends(_svc)) -> SolicitudVacacionesListResponse:
    u = request.state.user
    return service.get_by_empleado(empleado_id, u.get("id"), u.get("rol"), get_empresa_id(request))
