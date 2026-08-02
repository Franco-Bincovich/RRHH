"""
Alta de un usuario del sistema (extraído para mantener el service ≤150 líneas).

Función libre que recibe los colaboradores (repo, audit) — mismo molde que
`services/_onboarding_iniciar.py`. El service la delega en una línea.
La lógica se movió VERBATIM desde UsuarioService.crear_usuario.

🔴 EL CORTE SE HIZO ACÁ Y NO EN OTRO MÉTODO por un motivo concreto: `usuario_service` estaba en
149/150 y eso BLOQUEABA la guarda pendiente en `eliminar_usuario` (bloquear con 409 la baja del
usuario que es la casilla de correo del sistema — ver `repositories/integracion_remitente_repo.py`).
El alta es el método más largo y el más autocontenido de los tres, así que sacarlo es lo que deja
sitio para esa guarda sin volver a tocar límites.
"""
import secrets
from typing import Optional

from integrations.supabase_client import supabase_admin
from schemas.usuario import CrearUsuarioRequest, CrearUsuarioResponse
from services._audit_payloads_usuarios import payload_alta_usuario
from utils.errors import AppError
from utils.logger import logger

# Alfabeto sin caracteres ambiguos (sin O/0/I/l/1/o) + símbolos, para la password temporal.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789@#$%&*"


def _generar_password(n: int = 16) -> str:
    """Genera una contraseña temporal aleatoria (secrets) de n chars sin ambigüedades."""
    return "".join(secrets.choice(_ALFABETO) for _ in range(n))


def _rollback_auth(uid: str) -> None:
    """Borra el auth.users recién creado para no dejar identidad huérfana (best-effort)."""
    try:
        supabase_admin.auth.admin.delete_user(uid)
    except Exception as exc:
        logger.error("rollback_auth_fallo", extra={"user_id": uid, "error": str(exc)})


def crear(repo, audit, data: CrearUsuarioRequest, creado_por: Optional[str]) -> CrearUsuarioResponse:
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
    if repo.email_existe(email):
        raise AppError("Ya existe un usuario con ese email", "EMAIL_DUPLICADO", 409)
    if repo.username_existe(username):
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
        repo.insert_perfil({
            "id": uid, "email": email, "nombre": data.nombre.strip(),
            "apellido": data.apellido.strip(), "username": username,
            "rol": data.rol, "must_change_password": True,
        })
        if data.empleado_id is not None and not repo.vincular_empleado(str(data.empleado_id), uid):
            raise AppError("El empleado indicado no existe", "EMPLEADO_NOT_FOUND", 404)
    except Exception as exc:
        _rollback_auth(uid)  # borra auth.users; el CASCADE limpia el perfil si se insertó
        if isinstance(exc, AppError):
            raise
        raise AppError("No se pudo crear el usuario", "USUARIO_CREATE_ERROR", 500) from exc

    audit.registrar(**payload_alta_usuario(uid, username, data.rol, creado_por))
    logger.info("Usuario creado", extra={"user_id": uid, "username": username, "creado_por": creado_por})
    return CrearUsuarioResponse(id=uid, username=username, password_temporal=password)
