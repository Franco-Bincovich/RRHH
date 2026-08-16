"""
`sujeto(request)` — quién mira, para los módulos que tienen filas públicas y privadas.

VIVE EN `utils/` Y NO EN UN ROUTER, y el motivo es el mismo por el que `puede_ver_costos` salió
a `routers/_recategorizaciones_costos.py`: en cuanto un segundo módulo lo necesita, la copia y el
original divergen. Nació dentro de `routers/onboarding_templates.py` (un router exportando un
helper que otro router importa) y el segundo caso —la agenda de eventos— lo subió acá antes de
duplicarlo, que es el orden correcto: se mueve cuando aparece el segundo, no después.

🔑 DEVUELVE LOS DOS JUNTOS, Y ES LA DECISIÓN DEL MÓDULO. `user_id` dice de quién es una fila
privada y `rol` si hay que filtrar (`gerencia_lectura` ve las privadas ajenas). Exponerlos como
dos funciones sueltas invitaba a pasar uno y olvidarse del otro, y olvidarse del `rol` no rompe
nada visible: simplemente le esconde a la dirección filas que sí puede ver.

⚠️ NO reemplaza a `utils/empresa.get_empresa_id`. Son dos ejes distintos que se componen por
INTERSECCIÓN: la empresa dice de qué sociedad es la fila, el sujeto dice quién la escribió.
"""
from typing import Optional, Tuple

from starlette.requests import Request


def sujeto(request: Request) -> Tuple[Optional[str], Optional[str]]:
    """(user_id, rol) del request — el sujeto de la visibilidad pública/privada.

    Se lee de `request.state.user`, que puebla `AuthMiddleware`, igual que `require_permission`.
    Los dos salen `None` solo en un estado imposible por una ruta autenticada: el middleware es
    fail-closed y corta antes. Aun así se lee defensivamente (sin `AttributeError` ni `KeyError`)
    porque el caller de abajo trata `user_id=None` como "no restringe", y una excepción acá
    convertiría un estado raro en un 500 en vez de dejar que el gate de permisos responda 403.

    Args:
        request: Request de Starlette ya pasado por AuthMiddleware.

    Returns:
        Tupla `(user_id, rol)`, los dos como texto o None.
    """
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        return None, None
    return user.get("id"), user.get("rol")
