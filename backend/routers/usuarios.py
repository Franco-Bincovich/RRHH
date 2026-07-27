"""
Router de usuarios del sistema. Listado (para selectores) + alta con rol asignable.
La autenticación vive en routers/auth.py; acá el alta va gateada con USUARIOS + WRITE.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from integrations.supabase_client import supabase_admin
from schemas.usuario import (
    CambiarPasswordRequest,
    CambiarPasswordResponse,
    CrearUsuarioRequest,
    CrearUsuarioResponse,
)
from services.usuario_service import UsuarioService
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.USUARIOS


def _svc() -> UsuarioService:
    return UsuarioService()


@router.get("", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_usuarios(request: Request) -> dict:
    """Retorna usuarios activos del sistema (para el selector de responsable de objetivos)."""
    data = (
        supabase_admin.table("users")
        .select("id, nombre, apellido, email, username, rol")
        .eq("activo", True)
        .order("apellido")
        .execute().data or []
    )
    return {"items": data, "total": len(data)}


@router.post("", response_model=CrearUsuarioResponse, status_code=201,
             dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def crear_usuario(
    request: Request,
    body: CrearUsuarioRequest,
    service: UsuarioService = Depends(_svc),
) -> CrearUsuarioResponse:
    """Crea un usuario con el rol indicado (validado en el schema) y contraseña temporal. Solo admin_rrhh."""
    creado_por = request.state.user.get("id", "system")
    return service.crear_usuario(body, creado_por)


# Autenticado, pero es superficie de credenciales: verifica `password_actual`, así que sin
# límite es un oráculo para adivinar la clave vigente desde una sesión secuestrada.
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


@router.delete("/{user_id}", status_code=204,
               dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def eliminar_usuario(
    user_id: UUID,
    request: Request,
    service: UsuarioService = Depends(_svc),
) -> None:
    """Elimina un usuario del sistema. Solo admin_rrhh. No permite auto-eliminación.
    El id sale del path; el ejecutor, del token."""
    service.eliminar_usuario(str(user_id), request.state.user.get("id"))
