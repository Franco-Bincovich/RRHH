"""
Repositorio de states de OAuth (los nonces del flujo de autorización, tabla oauth_states).
Interfaz pública: crear · consumir · purgar_vencidos
"""
from integrations.supabase_client import supabase_admin
from utils.errors import AppError
from utils.logger import logger

_TABLE = "oauth_states"


class OAuthStateRepo:
    def crear(self, state_hash: str, user_id: str, proveedor: str, expires_at: str) -> dict:
        """Guarda un state pendiente. `state_hash` es el SHA-256 del nonce, nunca el crudo."""
        payload = {
            "state_hash": state_hash,
            "user_id": user_id,
            "proveedor": proveedor,
            "expires_at": expires_at,
        }
        result = supabase_admin.table(_TABLE).insert(payload).execute()
        if not result.data:
            logger.error("Supabase insert vacío en oauth_states")
            raise AppError("Error al iniciar la conexión", "DB_ERROR", 500)
        return result.data[0]

    def consumir(self, state_hash: str, proveedor: str) -> dict | None:
        """Borra el state y devuelve la fila borrada, o None si no había ninguna.

        El DELETE **es** la operación de consumo, y por eso el uso único es atómico: si dos
        callbacks llegan a la vez con el mismo valor, la base le entrega la fila a uno solo y
        el otro recibe None. Un `select` seguido de un `delete` dejaría esa ventana abierta.
        """
        result = (
            supabase_admin.table(_TABLE)
            .delete()
            .eq("state_hash", state_hash)
            .eq("proveedor", proveedor)
            .execute()
        )
        return result.data[0] if result.data else None

    def purgar_vencidos(self, ahora: str) -> int:
        """Borra los states vencidos y devuelve cuántos eran.

        Higiene, no corrección: la verificación ya descarta los vencidos por `expires_at`, así
        que una fila sin borrar no cambia ninguna decisión. Se llama desde el camino que crea
        states (ver services/_oauth_state.generar), que es el que genera las filas — así se
        autobalancea y no hace falta un job periódico.
        """
        result = supabase_admin.table(_TABLE).delete().lt("expires_at", ahora).execute()
        return len(result.data or [])
