"""
Repositorio de escritura de usuarios del sistema (perfil espejo en public.users).
La identidad/credencial vive en auth.users (Supabase Auth) — eso lo maneja el service.
Acceso con supabase_admin. Chequeos de unicidad dirigidos (limit 1, sin full-scan).
"""
from datetime import datetime, timezone
from typing import Optional

from integrations.supabase_client import supabase_admin
from utils.errors import AppError

_USERS = "users"
_EMPLEADOS = "empleados"

# Proyección del listado. Sin credenciales ni estado de sesión (ver services/_usuarios_export).
_SELECT_LISTA = "id, nombre, apellido, email, username, rol"


class UsuarioRepo:
    def listar_activos(self) -> list[dict]:
        """Usuarios activos del sistema, ordenados por apellido.

        🔴 Esta query VIVÍA EN EL ROUTER. Bajó acá sin cambiarle nada al traer el export: el
        listado y el archivo salen del MISMO lugar, o divergen sin que nada avise.
        """
        res = supabase_admin.table(_USERS).select(_SELECT_LISTA).eq("activo", True).order("apellido").execute()
        return res.data or []

    def email_existe(self, email: str) -> bool:
        """True si ya hay un usuario con ese email (chequeo dirigido)."""
        res = supabase_admin.table(_USERS).select("id").eq("email", email).limit(1).execute()
        return bool(res.data)

    def username_existe(self, username: str) -> bool:
        """True si ya hay un usuario con ese username (case-insensitive, dirigido)."""
        res = supabase_admin.table(_USERS).select("id").ilike("username", username).limit(1).execute()
        return bool(res.data)

    def insert_perfil(self, payload: dict) -> None:
        """Inserta la fila espejo en public.users. Lanza si el insert vuelve vacío."""
        res = supabase_admin.table(_USERS).insert(payload).execute()
        if not res.data:
            raise AppError("Error al crear el perfil del usuario", "DB_ERROR", 500)

    def vincular_empleado(self, empleado_id: str, user_id: str) -> bool:
        """Setea empleados.user_id. Devuelve False si el empleado no existe (0 filas)."""
        res = supabase_admin.table(_EMPLEADOS).update({"user_id": user_id}).eq("id", empleado_id).execute()
        return bool(res.data)

    def get_email(self, user_id: str) -> Optional[str]:
        """Email del usuario por id (para reautenticar en el cambio de contraseña).
        None si el usuario no existe. Chequeo dirigido (limit 1)."""
        res = supabase_admin.table(_USERS).select("email").eq("id", user_id).limit(1).execute()
        return res.data[0]["email"] if res.data else None

    def bajar_flag_password(self, user_id: str) -> None:
        """Baja must_change_password a false tras un cambio de contraseña exitoso
        (idempotente: dejarlo en false si ya lo estaba no rompe nada)."""
        supabase_admin.table(_USERS).update({"must_change_password": False}).eq("id", user_id).execute()

    def tocar_ultimo_acceso(self, user_id: str) -> str:
        """Sella `users.ultimo_acceso` con la hora actual y devuelve el sello escrito.

        Devolverlo (en vez de un None) es lo que le permite al caché actualizar su copia en
        memoria sin volver a leer: sin eso, el próximo chequeo de inactividad usaría el valor
        viejo hasta que venza el TTL.

        El sello lo pone la app, no `now()` de Postgres: así el valor que se guarda y el que
        queda en memoria son EL MISMO, y un desfasaje de reloj no puede hacer que una sesión
        recién sellada se vea vencida."""
        sello = datetime.now(timezone.utc).isoformat()
        supabase_admin.table(_USERS).update({"ultimo_acceso": sello}).eq("id", user_id).execute()
        return sello

    def get_estado(self, user_id: str) -> Optional[dict]:
        """Estado de autorización del usuario (rol + activo + ultimo_acceso), para el caché del
        middleware.

        Los tres campos salen de la MISMA fila y la misma query: sumarlos no cuesta un request
        más.

        `limit(1)` y no `.single()`: `.single()` LANZA con 0 filas, y acá "el usuario no existe"
        es una respuesta legítima que el caller convierte en negación, no un error de base.
        None si no existe."""
        res = supabase_admin.table(_USERS).select("rol, activo, ultimo_acceso").eq("id", user_id).limit(1).execute()
        return res.data[0] if res.data else None

    def set_activo(self, user_id: str, activo: bool) -> None:
        """Baja/alta BLANDA del perfil: mueve `activo` sin borrar la fila.

        Que la fila sobreviva es el punto: `empleados.user_id` tiene FK con ON DELETE SET NULL,
        así que borrarla desvincula al empleado de su usuario y la auditoría vieja queda
        apuntando a un id que ya no resuelve a ningún nombre."""
        supabase_admin.table(_USERS).update({"activo": activo}).eq("id", user_id).execute()

    def get_perfil(self, user_id: str) -> Optional[dict]:
        """Perfil mínimo (id, username, rol) para la baja y su auditoría. None si no existe."""
        res = supabase_admin.table(_USERS).select("id, username, rol").eq("id", user_id).limit(1).execute()
        return res.data[0] if res.data else None
