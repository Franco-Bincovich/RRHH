"""
Repositorio de las sesiones del link público de horas (tabla `sesiones_horas`, migración 105).
Interfaz: crear · buscar_vigente · purgar_vencidas

Molde: `oauth_state_repo.py`. La diferencia de fondo está en `buscar_vigente`, que NO borra —
ver su docstring.
"""
from typing import Optional

from integrations.supabase_client import supabase_admin
from utils.errors import AppError
from utils.logger import logger

_T = "sesiones_horas"


class SesionHorasRepo:
    def crear(self, token_hash: str, empleado_id: str, empresa_id: str,
              expires_at: str) -> dict:
        """Persiste una sesión. `token_hash` es el SHA-256 del token, nunca el crudo."""
        res = supabase_admin.table(_T).insert({
            "token_hash": token_hash, "empleado_id": empleado_id,
            "empresa_id": empresa_id, "expires_at": expires_at,
        }).execute()
        if not res.data:
            logger.error("Supabase insert vacío en sesiones_horas")
            raise AppError("Error al iniciar la sesión", "DB_ERROR", 500)
        return res.data[0]

    def buscar_vigente(self, token_hash: str, ahora: str) -> Optional[dict]:
        """La sesión de ese token si no venció, o None.

        🔴 NO BORRA, al revés que `OAuthStateRepo.consumir`, y la diferencia es deliberada: allá
        el borrado ES la verificación porque un nonce completa UN flujo y se quema. Acá una
        sesión cubre una sesión de trabajo real, donde la persona carga varios renglones del día
        o de la semana. Quemarla en la primera carga obligaría a re-tipear el DNI en cada uno.

        Lo que reemplaza al uso único es el TTL: el filtro `expires_at > ahora` va EN LA QUERY,
        no comparado en Python después de traer la fila. Una sesión vencida no se distingue de
        una inexistente, que es lo que el rechazo único necesita.
        """
        res = (supabase_admin.table(_T)
               .select("id, empleado_id, empresa_id, expires_at")
               .eq("token_hash", token_hash).gt("expires_at", ahora)
               .maybe_single().execute())
        return res.data if (res and res.data) else None

    def purgar_vencidas(self, ahora: str) -> int:
        """Borra las sesiones vencidas y devuelve cuántas eran.

        Higiene, no corrección: `buscar_vigente` ya las descarta por `expires_at`. Corre en el
        camino que CREA sesiones —el que genera las filas— así que se autobalancea sin job
        periódico. Mismo patrón que `oauth_state_repo.purgar_vencidos`.
        """
        res = supabase_admin.table(_T).delete().lt("expires_at", ahora).execute()
        return len(res.data or [])
