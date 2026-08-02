"""
Escrituras dirigidas al token de Google de `usuario_integraciones`.

Satélite de `integracion_repo.py`, que quedó en 102 contra un límite de 100 al sumarle la
persistencia del token renovado. Molde: `_empleado_write_repo.py` — el repo principal conserva
la interfaz pública y delega en una línea, así ningún call site cambia.

El corte es por forma de la escritura: acá vive el UPDATE de DOS COLUMNAS, y en el principal
quedan los upserts de credencial completa (`save_google_tokens`, `save_api_key`). Que son
justamente lo que NO hay que usar para esto — ver el porqué abajo.
"""
from typing import Optional

from integrations.supabase_client import supabase_admin

TABLE = "usuario_integraciones"


def actualizar_token(user_id: str, access_token: str, token_expiry: Optional[str]) -> None:
    """Persiste el access_token RENOVADO (y su vencimiento) sin tocar nada más.

    🔴 UPDATE DIRIGIDO A DOS COLUMNAS, NO UN UPSERT. La respuesta del refresh de Google NO trae
    `refresh_token` —solo lo manda en el consentimiento inicial—, así que un upsert con el
    payload completo escribiría NULL encima del refresh token guardado y dejaría la integración
    muerta: el próximo vencimiento ya no tendría con qué renovar y el usuario tendría que
    reconectar sin entender por qué. Es un bug que se arregla reconectando, o sea el más difícil
    de diagnosticar: se ve como "a veces se desconecta solo".

    No levanta si no encuentra la fila: quien llama ya tiene el token en la mano, y esto es una
    optimización para el PRÓXIMO request, no parte de la operación en curso.

    Args:
        user_id: dueño de la integración.
        access_token: el token recién obtenido del refresh.
        token_expiry: vencimiento en ISO 8601, o None si Google no informó `expires_in`.
    """
    (supabase_admin.table(TABLE)
     .update({"access_token": access_token, "token_expiry": token_expiry})
     .eq("user_id", user_id).eq("tipo", "google")
     .execute())
