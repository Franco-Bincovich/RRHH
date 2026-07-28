"""
Servicio de alta de usuarios del sistema (rol asignable: los 3 roles válidos).
Flujo: router → service → repository. La identidad va a Supabase Auth (auth.users);
el perfil, a public.users. Ambos pasos van juntos o se revierten (rollback del auth user).
"""
import secrets
from typing import Optional

from integrations.supabase_client import supabase_admin, supabase_client
from repositories.usuario_repo import UsuarioRepo
from schemas.usuario import CrearUsuarioRequest, CrearUsuarioResponse
from services._audit_payloads_usuarios import (
    payload_alta_usuario, payload_baja_usuario, payload_cambio_password,
)
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger

# Alfabeto sin caracteres ambiguos (sin O/0/I/l/1/o) + símbolos, para la password temporal.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789@#$%&*"


def _generar_password(n: int = 16) -> str:
    """Genera una contraseña temporal aleatoria (secrets) de n chars sin ambigüedades."""
    return "".join(secrets.choice(_ALFABETO) for _ in range(n))


class UsuarioService:
    def __init__(self, repo: Optional[UsuarioRepo] = None, audit: Optional[AuditService] = None) -> None:
        self._repo = repo or UsuarioRepo()
        self._audit = audit or AuditService()

    def _rollback_auth(self, uid: str) -> None:
        """Borra el auth.users recién creado para no dejar identidad huérfana (best-effort)."""
        try:
            supabase_admin.auth.admin.delete_user(uid)
        except Exception as exc:
            logger.error("rollback_auth_fallo", extra={"user_id": uid, "error": str(exc)})

    def crear_usuario(self, data: CrearUsuarioRequest, creado_por: Optional[str]) -> CrearUsuarioResponse:
        """
        Crea un usuario con el rol recibido (ya validado contra ROLES_VALIDOS en el schema):
        identidad en Supabase Auth + perfil en public.users (+ vínculo al empleado si se pasa
        empleado_id). Genera y devuelve una contraseña temporal (una sola vez), con
        must_change_password=true para forzar el cambio.

        Atómico por rollback: si falla el perfil o el vínculo, borra el auth user creado
        antes de propagar. Verifica unicidad de email/username antes de tocar Auth.

        Args:
            data: nombre, apellido, email, username, rol y empleado_id (opcional).
            creado_por: id del admin que ejecuta (para auditoría).

        Returns:
            CrearUsuarioResponse con id, username y la contraseña temporal (no recuperable).

        Raises:
            AppError: EMAIL_DUPLICADO/USERNAME_DUPLICADO (409), EMPLEADO_NOT_FOUND (404),
                      AUTH_CREATE_ERROR (502), USUARIO_CREATE_ERROR (500).
        """
        email = data.email.lower().strip()
        username = data.username.strip()
        if self._repo.email_existe(email):
            raise AppError("Ya existe un usuario con ese email", "EMAIL_DUPLICADO", 409)
        if self._repo.username_existe(username):
            raise AppError("Ya existe un usuario con ese nombre de usuario", "USERNAME_DUPLICADO", 409)

        password = _generar_password()
        try:
            resp = supabase_admin.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
        except Exception as exc:
            raise AppError("No se pudo crear la identidad del usuario", "AUTH_CREATE_ERROR", 502) from exc

        user_obj = getattr(resp, "user", None)
        if not user_obj or not getattr(user_obj, "id", None):
            raise AppError("Respuesta inválida al crear la identidad", "AUTH_CREATE_ERROR", 502)
        uid = str(user_obj.id)

        try:
            self._repo.insert_perfil({
                "id": uid, "email": email, "nombre": data.nombre.strip(),
                "apellido": data.apellido.strip(), "username": username,
                "rol": data.rol, "must_change_password": True,
            })
            if data.empleado_id is not None and not self._repo.vincular_empleado(str(data.empleado_id), uid):
                raise AppError("El empleado indicado no existe", "EMPLEADO_NOT_FOUND", 404)
        except Exception as exc:
            self._rollback_auth(uid)  # borra auth.users; el CASCADE limpia el perfil si se insertó
            if isinstance(exc, AppError):
                raise
            raise AppError("No se pudo crear el usuario", "USUARIO_CREATE_ERROR", 500) from exc

        self._audit.registrar(**payload_alta_usuario(uid, username, data.rol, creado_por))
        logger.info("Usuario creado", extra={"user_id": uid, "username": username, "creado_por": creado_por})
        return CrearUsuarioResponse(id=uid, username=username, password_temporal=password)

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
