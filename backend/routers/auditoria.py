"""
Router del audit log (T18.4a) — lectura paginada de eventos de auditoría.
Sección: "auditoria". Solo lectura: el sistema escribe el audit, no el usuario.
empresa_id para el filtro: header X-Empresa-Id (get_empresa_id), None = consolidado.
"""
from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.auditoria import AuditLogListResponse
from services.audit_service import AuditService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()

SECCION = Seccion.AUDITORIA


def _svc() -> AuditService:
    return AuditService()


@router.get("", response_model=AuditLogListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_auditoria(
    request: Request,
    usuario_id: Optional[UUID] = Query(None),
    entidad: Optional[str] = Query(None),
    evento: Optional[str] = Query(None),
    registro_id: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: AuditService = Depends(_svc),
) -> AuditLogListResponse:
    return service.listar(
        empresa_id=get_empresa_id(request),
        usuario_id=usuario_id,
        entidad=entidad,
        evento=evento,
        registro_id=registro_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        page_size=page_size,
    )


@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_auditoria(
    request: Request,
    usuario_id: Optional[UUID] = Query(None),
    entidad: Optional[str] = Query(None),
    evento: Optional[str] = Query(None),
    registro_id: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    service: AuditService = Depends(_svc),
) -> Response:
    """Export del listado — mismos Query que el listado. `request` lo exige slowapi."""
    d = service.exportar(
        empresa_id=get_empresa_id(request), usuario_id=usuario_id, entidad=entidad,
        evento=evento, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        registro_id=registro_id, formato=formato,
    )
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
