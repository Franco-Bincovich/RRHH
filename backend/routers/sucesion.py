"""Router de sucesión — mapa de talento y planes de carrera. empresa_id: lecturas por X-Empresa-Id (None = todas); CREATE heredada del empleado en el service."""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.sucesion import (
    EmpleadoAnalisisResponse, EmpleadoMapaResponse,
    HitoBodyCreate, HitoResponse,
    PlanCarreraCreate, PlanCarreraResponse, ReadinessUpdate,
)
from services.sucesion_service import SucesionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.SUCESION


def _svc() -> SucesionService:
    return SucesionService()


@router.get("/mapa", response_model=list[EmpleadoMapaResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_mapa_talento(request: Request, svc: SucesionService = Depends(_svc)) -> list[EmpleadoMapaResponse]:
    return svc.get_mapa_talento(get_empresa_id(request))


@router.get("/analisis", response_model=list[EmpleadoAnalisisResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_analisis_posicion(
    request: Request, area_id: UUID, svc: SucesionService = Depends(_svc),
) -> list[EmpleadoAnalisisResponse]:
    return svc.get_analisis_posicion(area_id, get_empresa_id(request))


@router.get("/planes", response_model=list[PlanCarreraResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_planes_carrera(request: Request, svc: SucesionService = Depends(_svc)) -> list[PlanCarreraResponse]:
    return svc.get_planes_carrera(get_empresa_id(request))


@router.post("/planes", response_model=PlanCarreraResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_plan_carrera(
    data: PlanCarreraCreate, request: Request, svc: SucesionService = Depends(_svc),
) -> PlanCarreraResponse:
    return svc.create_plan_carrera(data, get_empresa_id(request))


@router.get("/planes/{plan_id}/hitos", response_model=list[HitoResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_hitos(
    plan_id: UUID, request: Request, svc: SucesionService = Depends(_svc),
) -> list[HitoResponse]:
    return svc.get_hitos(plan_id, get_empresa_id(request))


@router.post("/planes/{plan_id}/hitos", response_model=HitoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_hito(
    plan_id: UUID, data: HitoBodyCreate, request: Request, svc: SucesionService = Depends(_svc),
) -> HitoResponse:
    return svc.create_hito(plan_id, data, get_empresa_id(request))


@router.put("/planes/{plan_id}/readiness", response_model=PlanCarreraResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_readiness(
    plan_id: UUID, data: ReadinessUpdate, request: Request, svc: SucesionService = Depends(_svc),
) -> PlanCarreraResponse:
    return svc.update_readiness(plan_id, data.readiness, get_empresa_id(request))


@router.put("/hitos/{hito_id}/completar", response_model=dict, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def completar_hito(
    hito_id: UUID, request: Request, svc: SucesionService = Depends(_svc),
) -> dict:
    svc.completar_hito(hito_id, get_empresa_id(request))
    return {"ok": True}
