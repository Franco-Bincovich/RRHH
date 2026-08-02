"""
Repositorio de integraciones por usuario.
Interfaz pública: get_by_user · save_google_tokens · save_api_key · delete
"""
from typing import Optional

from integrations.supabase_client import supabase_admin
from repositories._integracion_token_repo import actualizar_token
from utils.errors import AppError
from utils.logger import logger

_TABLE = "usuario_integraciones"


class IntegracionRepo:
    def get_by_user(self, user_id: str) -> list[dict]:
        """Devuelve todas las integraciones activas de un usuario."""
        result = (
            supabase_admin.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data or []

    def save_google_tokens(self, user_id: str, tokens: dict) -> dict:
        """Inserta o actualiza los tokens de Google para un usuario."""
        payload = {
            "user_id": user_id,
            "tipo": "google",
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_expiry": tokens.get("token_expiry"),
            "email_cuenta": tokens.get("email_cuenta"),
            "scopes": tokens.get("scopes"),
            "activo": True,
        }
        result = (
            supabase_admin.table(_TABLE)
            .upsert(payload, on_conflict="user_id,tipo")
            .execute()
        )
        if not result.data:
            logger.error("Supabase upsert vacío en usuario_integraciones (google)")
            raise AppError("Error al guardar tokens de Google", "DB_ERROR", 500)
        return result.data[0]

    def save_api_key(self, user_id: str, tipo: str, key: str) -> dict:
        """Inserta o actualiza una API key para un usuario."""
        payload = {
            "user_id": user_id,
            "tipo": tipo,
            "api_key": key,
            "activo": True,
        }
        result = (
            supabase_admin.table(_TABLE)
            .upsert(payload, on_conflict="user_id,tipo")
            .execute()
        )
        if not result.data:
            logger.error("Supabase upsert vacío en usuario_integraciones (api_key)")
            raise AppError("Error al guardar API key", "DB_ERROR", 500)
        return result.data[0]

    def actualizar_token(self, user_id: str, access_token: str, token_expiry: Optional[str]) -> None:
        """Persiste el access_token renovado. Delegado a _integracion_token_repo.actualizar_token,
        donde está escrito por qué es un UPDATE dirigido y no un upsert."""
        actualizar_token(user_id, access_token, token_expiry)

    def get_by_user_and_tipo(self, user_id: str, tipo: str) -> Optional[dict]:
        """Devuelve la integración activa de un tipo específico para un usuario."""
        result = (
            supabase_admin.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("tipo", tipo)
            .maybe_single()
            .execute()
        )
        return result.data

    def delete(self, user_id: str, tipo: str) -> bool:
        """Elimina una integración de un usuario por tipo."""
        result = (
            supabase_admin.table(_TABLE)
            .delete()
            .eq("user_id", user_id)
            .eq("tipo", tipo)
            .execute()
        )
        return bool(result.data)
