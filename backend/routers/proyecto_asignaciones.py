"""
Router de asignaciones de proyecto. Comparte prefix /api/proyectos con proyectos.py.
empresa_id para validaciones: header X-Empresa-Id.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.proyectos import (
    AsignacionAreaCreate, AsignacionBulkCreate, AsignacionBulkResult,
    AsignacionCreate, AsignacionListResponse, AsignacionResponse, AsignacionUpdate,
)
from services.asignaciones_service import AsignacionesService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.PROYECTOS


def _svc() -> AsignacionesService:
    return AsignacionesService()


@router.get("/{proyecto_id}/asignaciones", response_model=AsignacionListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_asignaciones(
    proyecto_id: UUID, request: Request,
    service: AsignacionesService = Depends(_svc),
) -> AsignacionListResponse:
    return service.get_by_proyecto(proyecto_id, get_empresa_id(request))


@router.post("/{proyecto_id}/asignaciones", response_model=AsignacionResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def asignar_empleado(
    proyecto_id: UUID, request: Request, body: AsignacionCreate,
    service: AsignacionesService = Depends(_svc),
) -> AsignacionResponse:
    return service.asignar(proyecto_id, body, get_empresa_id(request))


@router.post("/{proyecto_id}/asignaciones/bulk", response_model=AsignacionBulkResult, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def asignar_bulk(
    proyecto_id: UUID, request: Request, body: AsignacionBulkCreate,
    service: AsignacionesService = Depends(_svc),
) -> AsignacionBulkResult:
    return service.asignar_bulk(proyecto_id, body, get_empresa_id(request))


@router.post("/{proyecto_id}/asignaciones/area", response_model=AsignacionBulkResult, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def asignar_area(
    proyecto_id: UUID, body: AsignacionAreaCreate, request: Request,
    service: AsignacionesService = Depends(_svc),
) -> AsignacionBulkResult:
    """Asigna al proyecto TODOS los empleados del área, resueltos AHORA (foto, no vínculo vivo).

    Endpoint propio y no un modo del bulk: un schema donde hay que mandar `empleado_ids` O
    `area_id` obliga a cada caller a conocer esa regla, y el error que sale es peor que un 404.
    Lo que sí se comparte es la CLASIFICACIÓN del resultado (ver `_asignaciones_bulk`).

    Devuelve los mismos tres grupos que el bulk manual: creadas, ya asignados y errores."""
    return service.asignar_area(proyecto_id, body, get_empresa_id(request))


@router.put("/{proyecto_id}/asignaciones/{asig_id}", response_model=AsignacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_asignacion(
    proyecto_id: UUID, asig_id: UUID, body: AsignacionUpdate, request: Request,
    service: AsignacionesService = Depends(_svc),
) -> AsignacionResponse:
    return service.update(asig_id, body, get_empresa_id(request))


@router.delete("/{proyecto_id}/asignaciones/{asig_id}", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_asignacion(
    proyecto_id: UUID, asig_id: UUID, request: Request,
    service: AsignacionesService = Depends(_svc),
) -> dict:
    service.delete(asig_id, get_empresa_id(request))
    return {"ok": True}
