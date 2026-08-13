"""Router de empresas — CRUD + upload de logo. Rutas protegidas por AuthMiddleware (JWT)."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response

from schemas.empresa import (
    EmpresaActivaToggle,
    EmpresaCreate,
    EmpresaListResponse,
    EmpresaResponse,
    EmpresaUpdate,
)
from services.empresa_service import EmpresaService
from utils.files import ALLOWED_TYPES_IMAGEN, MAX_SIZE_LOGO, validate_upload
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.EMPRESA


def _service() -> EmpresaService:
    return EmpresaService()


@router.get("", response_model=EmpresaListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_empresas(service: EmpresaService = Depends(_service)) -> EmpresaListResponse:
    return service.list_empresas()


# ⚠️ ANTES de /{id}: si fuera después, "exportar" matchearía como un id y daría 422 de UUID.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_empresas(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: EmpresaService = Depends(_service)) -> Response:
    d = service.exportar(formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=EmpresaResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_empresa(id: UUID, service: EmpresaService = Depends(_service)) -> EmpresaResponse:
    return service.get_empresa(str(id))


@router.post("", response_model=EmpresaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_empresa(
    request: Request,
    body: EmpresaCreate,
    service: EmpresaService = Depends(_service),
) -> EmpresaResponse:
    created_by = request.state.user.get("id", "system")
    return service.create_empresa(body, created_by)


@router.put("/{id}", response_model=EmpresaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_empresa(id: UUID, body: EmpresaUpdate, service: EmpresaService = Depends(_service)) -> EmpresaResponse:
    return service.update_empresa(str(id), body)


@router.patch("/{id}/activa", response_model=EmpresaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def toggle_activa(
    id: UUID,
    body: EmpresaActivaToggle,
    request: Request,
    service: EmpresaService = Depends(_service),
) -> EmpresaResponse:
    return service.toggle_activa(str(id), body.activa, request.state.user.get("id", "system"))


@router.post("/{id}/logo", response_model=EmpresaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def upload_logo(id: UUID, request: Request, file: UploadFile = File(...), service: EmpresaService = Depends(_service)) -> EmpresaResponse:
    content = await file.read()
    validate_upload(content, file.content_type, ALLOWED_TYPES_IMAGEN, MAX_SIZE_LOGO, "logo")
    return service.upload_logo(str(id), content, file.filename or "logo", file.content_type or "image/jpeg",
                               request.state.user.get("id", "system"))
