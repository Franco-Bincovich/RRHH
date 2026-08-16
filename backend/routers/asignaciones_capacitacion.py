"""Router de asignaciones de capacitaciones — LECTURAS. empresa_id: X-Empresa-Id.

Las escrituras (alta, cambio de estado, baja y carga del certificado) viven en
`asignaciones_capacitacion_escrituras.py`, montado en el MISMO prefijo: las rutas no cambiaron.
El porqué del corte está en el docstring de ese archivo.
"""
from typing import Literal, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from schemas.capacitacion import AsignacionListResponse, AsignacionResponse
from services.asignacion_service import AsignacionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.CAPACITACIONES
def _svc() -> AsignacionService: return AsignacionService()


@router.get("", response_model=AsignacionListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_asignaciones(
    request: Request,
    empleado_id: Optional[UUID] = Query(None),
    capacitacion_id: Optional[UUID] = Query(None),
    estado: Optional[str] = Query(None),
    area_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AsignacionService = Depends(_svc),
) -> AsignacionListResponse:
    return service.get_all(get_empresa_id(request), empleado_id, capacitacion_id, estado, area_id, page, page_size)


# El export declara los MISMOS Query que el listado MENOS `page`/`page_size`: no se pagina, por
# diseño. Lo verifica tests/test_paridad_list_export.py en las dos direcciones.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_asignaciones(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), empleado_id: Optional[UUID] = Query(None), capacitacion_id: Optional[UUID] = Query(None), estado: Optional[str] = Query(None), area_id: Optional[UUID] = Query(None), service: AsignacionService = Depends(_svc)) -> Response:
    d = service.exportar(get_empresa_id(request), formato, empleado_id, capacitacion_id, estado, area_id)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}/certificado", status_code=200, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_certificado_url(
    id: UUID,
    request: Request,
    service: AsignacionService = Depends(_svc),
) -> dict:
    return {"url": service.get_certificado_signed_url(str(id), get_empresa_id(request))}
