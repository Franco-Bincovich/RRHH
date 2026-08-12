"""
Lookups de UNA fila de `public.users`. Satélite de `usuario_repo.py`.

Se extrajo porque `usuario_repo` estaba en **99/100** y no admitía el método que faltaba
(`por_username`, ver abajo). Molde: `_empleado_lookup_repo.py` — funciones libres, y el repo
sostiene la interfaz pública delegando en una línea, así ningún caller cambia.

El corte es por FORMA de la consulta, no por tamaño: acá viven las cuatro que devuelven **una
fila o None**. Las escrituras, los chequeos de unicidad (que devuelven bool) y el listado se
quedan en el repo.

🔴 LAS CUATRO USAN `limit(1)` Y DEVUELVEN `None`, NUNCA `.single()`. `.single()` LANZA con 0
filas, y en las cuatro "el usuario no existe" es una respuesta legítima que el caller convierte
en negación (un 401, un 422, un caché que no guarda), no un error de base. Es la regla que ya
está escrita en CLAUDE.md y que en `area_repo` y `empresa_repo` costó dos 500.
"""
from typing import Optional

from integrations.supabase_client import supabase_admin

_USERS = "users"

# Perfil completo del login: lo que la sesión necesita mostrar, sin credenciales.
_SELECT_LOGIN = "id, email, username, nombre, apellido, rol, must_change_password"


def por_username(username: str) -> Optional[dict]:
    """Perfil de login por username, case-insensitive. None si no existe.

    🔴 `ilike` SIN COMODINES es una igualdad case-insensitive, no una búsqueda parcial: el
    username se compara entero. Meterle `%` acá dejaría entrar a cualquiera cuyo nombre de
    usuario sea prefijo de otro.

    Esta query vivía en `auth_service` y era la única de `users` que no tenía método propio.
    Devuelve None en vez de lanzar: el service traduce el vacío al 401 genérico, que es el que
    no revela si el username existe.
    """
    res = supabase_admin.table(_USERS).select(_SELECT_LOGIN).ilike("username", username).limit(1).execute()
    return res.data[0] if res.data else None


def email(user_id: str) -> Optional[str]:
    """Email del usuario por id (para reautenticar en el cambio de contraseña). None si no existe."""
    res = supabase_admin.table(_USERS).select("email").eq("id", user_id).limit(1).execute()
    return res.data[0]["email"] if res.data else None


def estado(user_id: str) -> Optional[dict]:
    """Estado de autorización (rol + activo + ultimo_acceso), para el caché del middleware.

    Los tres campos salen de la MISMA fila y la misma query: sumarlos no cuesta un request más.
    None si el usuario no existe.
    """
    res = supabase_admin.table(_USERS).select("rol, activo, ultimo_acceso").eq("id", user_id).limit(1).execute()
    return res.data[0] if res.data else None


def perfil(user_id: str) -> Optional[dict]:
    """Perfil mínimo (id, username, rol) para la baja y su auditoría. None si no existe."""
    res = supabase_admin.table(_USERS).select("id, username, rol").eq("id", user_id).limit(1).execute()
    return res.data[0] if res.data else None
