"""
Schemas de autenticación. Validación de entrada y salida para los endpoints de /api/auth.
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: UUID
    email: str
    username: str
    rol: str
    nombre: str
    apellido: str
    must_change_password: bool = False  # true = contraseña temporal pendiente de cambio


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserInfo


class UsuarioVigenteResponse(BaseModel):
    """Estado del usuario SEGÚN EL BACKEND, para que el front no gobierne con lo que guardó al
    loguearse. Solo lo que puede cambiar debajo de una sesión abierta: hoy, el rol."""

    id: UUID
    rol: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
