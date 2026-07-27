"""
Servicio de refresh tokens con rotación — reemplaza el refresh de gotrue.

DESTINO: backend/services/token_service.py (hoy NO existe: la rotación la hacía Supabase,
auth_service.py:90 `supabase_client.auth.refresh_session`).

CÓMO FUNCIONA LA ROTACIÓN
-------------------------
El refresh token es un JWT (type:"refresh", sub=user_id) del que se guarda solo el HASH
bcrypt en refresh_tokens (migración 076). Cada refresh:
  1. verifica firma/expiración del JWT y saca el user_id de `sub`;
  2. trae los hashes vigentes de ese usuario (find_by_user) y busca el que matchee;
  3. BORRA esa fila — el token queda consumido, one-time use;
  4. emite un access nuevo + un refresh nuevo, y persiste el hash del nuevo.
Si el paso 2 no encuentra match, el token ya fue usado (o es falso) → 401.

POR QUÉ EL JWT LLEVA EL user_id: bcrypt es salteado, así que no se puede buscar por hash
(dos hashes del mismo token difieren). Sin el `sub` no habría forma de saber contra qué
filas comparar, salvo escanear la tabla entera con un checkpw por fila. El `sub` acota la
búsqueda a los tokens de un usuario.

⚠️ ASYNC (asyncpg). Sus callers necesitan await. Ver README_AUTH.md.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from config.settings import settings
from repositories.token_repo_NEW import TokenRepo, UserAuthRepo
from services.auth_service_NEW import ALGORITHM, create_access_token
from utils.errors import AppError
from utils.logger import logger

_BCRYPT_MAX_BYTES = 72  # ver nota en auth_service_NEW


def hash_token(token: str) -> str:
    """Hashea un refresh token con bcrypt antes de persistirlo.

    Un JWT largo pasa los 72 bytes de bcrypt y se truncaría: el hash cubriría solo el
    prefijo. Acá NO importa para la seguridad — los primeros 72 bytes de un JWT ya
    incluyen header y parte del payload con `iat`/`exp`, y de todos modos el token se
    valida antes por firma. Pero conviene saberlo: `checkpw` matchea por ese prefijo.

    Args:
        token: Refresh token crudo.

    Returns:
        El hash bcrypt como str.
    """
    return bcrypt.hashpw(token.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode("utf-8")


def _verify_token_hash(token: str, token_hash: str) -> bool:
    """Compara un refresh token crudo contra un hash guardado. Nunca levanta."""
    try:
        return bcrypt.checkpw(token.encode("utf-8")[:_BCRYPT_MAX_BYTES], token_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


class TokenService:
    def __init__(self, repo: Optional[TokenRepo] = None, user_repo: Optional[UserAuthRepo] = None) -> None:
        """Inyección por constructor, como el resto de los services de RRHH."""
        self._repo = repo or TokenRepo()
        self._user_repo = user_repo or UserAuthRepo()

    async def create_refresh_token(self, user_id: str) -> str:
        """Emite un refresh token y persiste su hash.

        Args:
            user_id: UUID del usuario.

        Returns:
            El refresh token crudo — se devuelve al cliente UNA vez y no se puede recuperar
            (en la base solo queda el hash).
        """
        ahora = datetime.now(timezone.utc)
        expire = ahora + timedelta(days=settings.refresh_token_expiration_days)
        token = jwt.encode(
            {"sub": str(user_id), "iat": ahora, "exp": expire, "type": "refresh"},
            settings.jwt_secret,
            algorithm=ALGORITHM,
        )
        await self._repo.save(str(user_id), hash_token(token), expire)
        return token

    async def refresh_access_token(self, token: str) -> dict:
        """Consume un refresh token y emite un par nuevo (rotación one-time-use).

        Mantiene el código INVALID_REFRESH_TOKEN del auth_service actual (línea 92).

        ⚠️ NO ES ATÓMICO: entre el delete del viejo y el save del nuevo no hay transacción.
        Si el proceso muere en el medio, el usuario queda sin refresh válido y tiene que
        loguear de nuevo. Se prefiere ese fallo (molesto, recuperable) al inverso — no
        borrar y dejar el token viejo vivo, que rompería el one-time-use. Para cerrarlo del
        todo hace falta envolver ambos pasos en una transacción de asyncpg
        (`async with conn.transaction()`), lo que exige que el repo comparta conexión: es
        un refactor del postgres_client, no de este archivo.

        Args:
            token: Refresh token crudo del cliente.

        Returns:
            {"access_token": str, "refresh_token": str} — el refresh es NUEVO; el viejo ya
            no sirve.

        Raises:
            AppError: INVALID_REFRESH_TOKEN (401) si es inválido, expirado, ya usado, o no
                es de tipo refresh. USUARIO_NOT_FOUND (404) si el usuario ya no existe.
        """
        invalido = AppError("Token de refresco inválido o expirado", "INVALID_REFRESH_TOKEN", 401)

        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        except Exception as exc:
            logger.warning("Refresh rechazado", extra={"motivo": type(exc).__name__})
            raise invalido from exc

        # Un access token NO puede pasar por refresh: sin este check, el access (60 min) se
        # convertiría en llave para renovar indefinidamente.
        if payload.get("type") != "refresh":
            raise invalido
        user_id = payload.get("sub")
        if not user_id:
            raise invalido

        fila = next(
            (t for t in await self._repo.find_by_user(user_id)
             if _verify_token_hash(token, t["token_hash"])),
            None,
        )
        if fila is None:  # ya consumido, revocado, o falso
            logger.warning("Refresh rechazado — token no vigente", extra={"user_id": user_id})
            raise invalido

        await self._repo.delete(str(fila["id"]))  # consumo ANTES de emitir

        # El rol se RE-LEE de la base en cada refresh, nunca se copia del token viejo: si un
        # admin cambió el rol (o dio de baja al usuario), el token nuevo lo refleja en vez de
        # arrastrar el privilegio viejo hasta que expire.
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise AppError("Usuario no encontrado", "USUARIO_NOT_FOUND", 404)
        if not user.get("activo", False):
            logger.warning("Refresh rechazado — usuario inactivo", extra={"user_id": user_id})
            raise invalido

        return {
            "access_token": create_access_token(user_id, user["rol"]),
            "refresh_token": await self.create_refresh_token(user_id),
        }

    async def revoke_refresh_token(self, user_id: str) -> None:
        """Revoca TODOS los refresh tokens del usuario (logout).

        Equivale al `auth.admin.sign_out` de gotrue (auth_service.py:112), que invalidaba
        todas las sesiones. Best-effort como el actual: el logout no debe fallarle al
        cliente porque la limpieza no salió.

        Args:
            user_id: UUID del usuario que cierra sesión.
        """
        try:
            await self._repo.delete_all_by_user(str(user_id))
        except Exception as exc:
            logger.warning("Error al revocar refresh tokens", extra={"user_id": user_id, "error": str(exc)})
        logger.info("Logout exitoso", extra={"user_id": user_id})
