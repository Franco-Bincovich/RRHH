"""
Repositorio de refresh tokens (tabla refresh_tokens, migración 076).

DESTINO: backend/repositories/token_repo.py (hoy NO existe — los refresh tokens los
manejaba gotrue, no había nada que persistir).

Escrito en asyncpg sobre el postgres_client del staging, NO en el SDK de Supabase.
Placeholders posicionales ($1, $2...): nunca interpolar valores en el SQL.

⚠️ ASYNC, a diferencia de todos los repos actuales de RRHH (que son síncronos porque el
SDK de Supabase lo es). Sus callers tienen que await. Ver README_AUTH.md.
"""
from typing import Any, Optional
from uuid import UUID

from integrations.postgres_client import execute, fetch, fetchone, fetchval

_TABLE = "refresh_tokens"

# Columnas del perfil que consume el auth. Explícitas, no `*`: password_hash es sensible y
# tiene que verse en el SELECT para que nadie lo filtre sin querer al agregar un caller.
_USER_COLS = (
    "id, email, username, nombre, apellido, rol, activo, password_hash, must_change_password"
)


class TokenRepo:
    async def save(self, user_id: str, token_hash: str, expire: Any) -> str:
        """Persiste el hash de un refresh token emitido.

        Args:
            user_id: UUID del dueño del token.
            token_hash: Hash bcrypt del token crudo (NUNCA el token en claro).
            expire: datetime con tz de expiración.

        Returns:
            El id (UUID como str) de la fila creada — lo necesita la rotación para borrarla.
        """
        row_id = await fetchval(
            f"INSERT INTO {_TABLE} (user_id, token_hash, expires_at) "
            "VALUES ($1, $2, $3) RETURNING id",
            UUID(str(user_id)), token_hash, expire,
        )
        return str(row_id)

    async def find_by_user(self, user_id: str) -> list[dict]:
        """Trae los refresh tokens VIGENTES de un usuario.

        Filtra los expirados en el WHERE en vez de traerlos y descartarlos en Python: cada
        candidato cuesta un bcrypt.checkpw (~100ms a propósito), así que traer basura se
        paga caro.

        Args:
            user_id: UUID del dueño.

        Returns:
            Lista de dicts {id, token_hash, expires_at}, la más nueva primero. Vacía si no
            hay ninguno vigente.
        """
        return await fetch(
            f"SELECT id, token_hash, expires_at FROM {_TABLE} "
            "WHERE user_id = $1 AND expires_at > now() ORDER BY created_at DESC",
            UUID(str(user_id)),
        )

    async def delete(self, token_id: str) -> None:
        """Borra un refresh token por id. Es el paso de consumo de la rotación.

        Args:
            token_id: UUID de la fila.
        """
        await execute(f"DELETE FROM {_TABLE} WHERE id = $1", UUID(str(token_id)))

    async def delete_all_by_user(self, user_id: str) -> None:
        """Borra TODOS los refresh tokens de un usuario (logout global).

        Equivale al `auth.admin.sign_out` de gotrue (auth_service.py:112), que invalidaba
        todas las sesiones del usuario.

        Args:
            user_id: UUID del dueño.
        """
        await execute(f"DELETE FROM {_TABLE} WHERE user_id = $1", UUID(str(user_id)))


class UserAuthRepo:
    """Lecturas de public.users que necesita el auth. Separado de TokenRepo: otra tabla.

    En la migración esto puede fusionarse con el usuario_repo real; vive acá para que el
    módulo de auth del staging sea autocontenido.
    """

    async def find_by_username(self, username: str) -> Optional[dict]:
        """Resuelve username → perfil completo, case-insensitive.

        Espeja el `ilike("username", username)` que hoy hace auth_service.py:38 contra el
        SDK. LOWER($1) sobre la columna: sin un índice funcional
        (`CREATE INDEX ... ON users (LOWER(username))`) es un seq scan — irrelevante con 3
        usuarios, a revisar si crece.

        Args:
            username: Nombre de usuario tal como lo tipeó el cliente.

        Returns:
            Dict con id, email, username, nombre, apellido, rol, activo, password_hash y
            must_change_password; None si no existe.
        """
        return await fetchone(
            f"SELECT {_USER_COLS} FROM users WHERE LOWER(username) = LOWER($1)",
            username,
        )

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        """Trae el perfil por id. Lo usa la rotación de refresh para re-leer el rol.

        Args:
            user_id: UUID del usuario.

        Returns:
            El perfil como dict; None si el usuario ya no existe (borrado entre la emisión
            del refresh y su uso).
        """
        return await fetchone(
            f"SELECT {_USER_COLS} FROM users WHERE id = $1",
            UUID(str(user_id)),
        )
