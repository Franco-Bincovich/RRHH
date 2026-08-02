"""
Servicio de alta de usuarios del sistema (rol asignable: los 3 roles válidos).
Flujo: router → service → repository. La identidad va a Supabase Auth (auth.users);
el perfil, a public.users. Ambos pasos van juntos o se revierten (rollback del auth user).
"""
from typing import Optional

from integrations.supabase_client import supabase_admin, supabase_client
from repositories.usuario_repo import UsuarioRepo
from schemas.usuario import CrearUsuarioRequest, CrearUsuarioResponse
from services._audit_payloads_usuarios import payload_baja_usuario, payload_cambio_password
from services._usuario_alta import crear as _crear_usuario
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger


class UsuarioService:
    def __init__(self, repo: Optional[UsuarioRepo] = None, audit: Optional[AuditService] = None) -> None:
        self._repo = repo or UsuarioRepo()
        self._audit = audit or AuditService()

    def crear_usuario(self, data: CrearUsuarioRequest, creado_por: Optional[str]) -> CrearUsuarioResponse:
        """Crea identidad + perfil con rollback. Ver services/_usuario_alta.crear."""
        return _crear_usuario(self._repo, self._audit, data, creado_por)

    def cambiar_password(self, user_id: str, password_actual: str, password_nueva: str) -> None:
        """
        Cambia la contraseña del usuario autenticado (self-service). Cubre los dos casos
        con el mismo flujo: cambio obligatorio (must_change_password) y cambio voluntario.

        Reautentica con la contraseña actual (sign_in_with_password) ANTES de cambiar:
        si falla, corta con INVALID_CREDENTIALS 401 genérico (no revela el detalle). Luego
        actualiza la credencial vía Supabase admin y baja must_change_password a false.
        Nunca loguea ninguna de las dos contraseñas.

        Args:
            user_id: id del usuario, SIEMPRE del token (nunca del body → evita IDOR).
            password_actual: contraseña vigente, a verificar por reautenticación.
            password_nueva: nueva contraseña (largo/distinción ya validados por el schema).

        Raises:
            AppError: USUARIO_NOT_FOUND (404), INVALID_CREDENTIALS (401),
                      PASSWORD_UPDATE_ERROR (502).
        """
        email = self._repo.get_email(user_id)
        if not email:
            raise AppError("Usuario no encontrado", "USUARIO_NOT_FOUND", 404)
        try:
            supabase_client.auth.sign_in_with_password({"email": email, "password": password_actual})
        except Exception as exc:
            raise AppError("Contraseña actual incorrecta", "INVALID_CREDENTIALS", 401) from exc
        try:
            supabase_admin.auth.admin.update_user_by_id(user_id, {"password": password_nueva})
        except Exception as exc:
            raise AppError("No se pudo actualizar la contraseña", "PASSWORD_UPDATE_ERROR", 502) from exc

        self._repo.bajar_flag_password(user_id)
        self._audit.registrar(**payload_cambio_password(user_id))
        logger.info("Cambio de contraseña", extra={"user_id": user_id})

    def eliminar_usuario(self, user_id: str, ejecutor_id: Optional[str]) -> None:
        """Elimina un usuario: borra auth.users (admin API); el CASCADE limpia public.users
        y el SET NULL desvincula empleados.user_id. Bloquea la auto-eliminación. Audita
        baja_usuario sin datos sensibles.
        Raises: AppError AUTOELIMINACION (400), USUARIO_NOT_FOUND (404), USUARIO_DELETE_ERROR (502)."""
        if ejecutor_id and str(ejecutor_id) == str(user_id):
            raise AppError("No podés eliminar tu propio usuario", "AUTOELIMINACION", 400)
        perfil = self._repo.get_perfil(user_id)
        if not perfil:
            raise AppError("Usuario no encontrado", "USUARIO_NOT_FOUND", 404)
        try:
            supabase_admin.auth.admin.delete_user(user_id)
        except Exception as exc:
            raise AppError("No se pudo eliminar el usuario", "USUARIO_DELETE_ERROR", 502) from exc
        self._audit.registrar(**payload_baja_usuario(user_id, perfil.get("username"), ejecutor_id))
        logger.info("Usuario eliminado", extra={"user_id": user_id, "eliminado_por": ejecutor_id})
