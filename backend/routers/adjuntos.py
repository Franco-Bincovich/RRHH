"""Router de adjuntos genéricos (polimórficos). Rutas protegidas por AuthMiddleware (JWT).

Los permisos NO se gatean con require_permission acá: dependen de la ENTIDAD del adjunto
(dato del request), no de una sección estática. El gating dinámico vive en AdjuntoService,
que recibe el rol y resuelve el permiso por sección. empresa_id sale de la empresa activa.
"""
from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, Query, Request, UploadFile

from schemas.adjunto import AdjuntoListResponse, AdjuntoResponse
from services.adjunto_service import AdjuntoService
from utils.empresa import get_empresa_id

router = APIRouter()


def _svc() -> AdjuntoService:
    return AdjuntoService()


def _actor(request: Request) -> Tuple[Optional[str], str]:
    """Extrae (rol, usuario_id) del usuario autenticado (seteado por AuthMiddleware)."""
    user = getattr(request.state, "user", None) or {}
    return user.get("rol"), user.get("id", "system")


@router.post("", response_model=AdjuntoResponse, status_code=201)
async def subir_adjunto(
    request: Request,
    entidad: str = Form(...),
    entidad_id: UUID = Form(...),
    categoria: Optional[str] = Form(None),
    descripcion: Optional[str] = Form(None),
    file: UploadFile = File(...),
    service: AdjuntoService = Depends(_svc),
) -> AdjuntoResponse:
    rol, usuario_id = _actor(request)
    content = await file.read()
    return service.subir(
        entidad, entidad_id, get_empresa_id(request), content,
        file.filename or "archivo", file.content_type or "application/octet-stream",
        categoria, descripcion, rol, usuario_id,
    )


@router.get("", response_model=AdjuntoListResponse)
async def listar_adjuntos(
    request: Request,
    entidad: str = Query(...),
    entidad_id: UUID = Query(...),
    service: AdjuntoService = Depends(_svc),
) -> AdjuntoListResponse:
    rol, _ = _actor(request)
    items = service.listar(entidad, entidad_id, get_empresa_id(request), rol)
    return AdjuntoListResponse(items=items, total=len(items))


@router.get("/{id}/url")
async def url_adjunto(id: UUID, request: Request, service: AdjuntoService = Depends(_svc)) -> dict:
    rol, _ = _actor(request)
    return {"url": service.url_descarga(str(id), get_empresa_id(request), rol)}


@router.put("/{id}/principal", response_model=AdjuntoResponse)
async def marcar_principal(
    id: UUID, request: Request,
    principal: bool = Body(True, embed=True),
    service: AdjuntoService = Depends(_svc),
) -> AdjuntoResponse:
    rol, usuario = _actor(request)
    return service.marcar_principal(str(id), principal, get_empresa_id(request), rol, usuario)


@router.delete("/{id}", status_code=200)
async def eliminar_adjunto(id: UUID, request: Request, service: AdjuntoService = Depends(_svc)) -> dict:
    rol, usuario_id = _actor(request)
    service.eliminar(str(id), get_empresa_id(request), rol, usuario_id)
    return {"ok": True}
