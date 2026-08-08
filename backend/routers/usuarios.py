"""
Router de usuarios del sistema — LECTURAS (listado + export) y cambio de contraseña.

El alta y la baja viven en routers/usuarios_escrituras.py, montado en el MISMO prefijo: las
rutas no cambiaron. El porqué del corte está en el docstring de ese archivo.
La autenticación vive en routers/auth.py; acá el ABM va gateado con USUARIOS + WRITE.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.usuario import CambiarPasswordRequest, CambiarPasswordResponse
from services.usuario_service import UsuarioService
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.USUARIOS


def _svc() -> UsuarioService:
    return UsuarioService()


@router.get("", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_usuarios(request: Request, service: UsuarioService = Depends(_svc)) -> dict:
    """Usuarios activos del sistema (pantalla de ABM y selector de responsable de objetivos).

    La query vive en el repo, no acá: el export sale del MISMO método, y con la consulta
    escrita en el router las dos puntas podrían divergir sin que nada avise."""
    return service.listar()


# ⚠️ ANTES de cualquier ruta /{...}: si un GET /{user_id} se agregara arriba, "exportar"
# matchearía como un uuid y este endpoint devolvería 422 en vez de un archivo.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_usuarios(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: UsuarioService = Depends(_svc)) -> Response:
    d = service.exportar(formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


# Autenticado, pero es superficie de credenciales: verifica `password_actual`, así que sin
# límite es un oráculo para adivinar la clave vigente desde una sesión secuestrada.
# 🔴 SE QUEDA EN ESTE ARCHIVO, no se fue con las escrituras: la clave del limiter es
# `routers.<módulo>.<función>`, así que mudarlo cambiaría la clave y dejaría su franja sin
# verificar. Mismo motivo por el que el export tampoco se mueve.
@router.post("/cambiar-password", response_model=CambiarPasswordResponse)
@limiter.limit("10/hour")
async def cambiar_password(
    request: Request,
    body: CambiarPasswordRequest,
    service: UsuarioService = Depends(_svc),
) -> CambiarPasswordResponse:
    """Cambia la contraseña del usuario autenticado (self-service, SIN gate de rol:
    cualquier usuario cambia SU propia clave). El id sale del token, nunca del body."""
    service.cambiar_password(request.state.user["id"], body.password_actual, body.password_nueva)
    return CambiarPasswordResponse()
