"""
`puede_ver_costos(request)` — la dependency que decide si `impacto_salarial` viaja.

Vive en un archivo propio y NO en uno de los tres routers del módulo porque **los tres la
usan** (planilla, ficha y export), y una copia por router es exactamente cómo una de las
superficies se queda con la versión vieja y devuelve el monto a quien no debe verlo. Mismo
criterio con el que `_usuario_id` se importa entre `clientes.py` y `clientes_escrituras.py`.

🔴 POR QUÉ NO ES UN `require_permission(COSTOS, READ)` COMO DEPENDENCY DE LA RUTA. Aquel
DENIEGA el request entero con 403; acá el request es legítimo y lo único que cambia es un
campo. Gatear la ruta con COSTOS dejaría a `gerencia_lectura`, y a cualquier rol futuro sin
costos, sin poder ver el historial de rol y seniority — que no son datos sensibles y son el 90%
del valor del módulo. Es la diferencia con `HistorialSalarialSection`, donde el bloque ENTERO
es un dato de costos y ocultarlo entero sí corresponde.

⚠️ Es fail-closed por construcción: `puede()` devuelve False ante un rol None o desconocido.
"""
from typing import Optional

from starlette.requests import Request

from utils.permisos import Accion, Seccion, puede


def puede_ver_costos(request: Request) -> bool:
    """¿El rol del request tiene lectura sobre COSTOS? Fail-closed ante un state raro.

    Se lee de `request.state.user` (lo pone AuthMiddleware), igual que `require_permission`.
    """
    user = getattr(request.state, "user", None)
    rol: Optional[str] = user.get("rol") if isinstance(user, dict) else None
    return puede(rol, Seccion.COSTOS, Accion.READ)


def usuario_id(request: Request) -> Optional[str]:
    """Id del usuario del request, para `registrado_por` y la trazabilidad de la auditoría."""
    user = getattr(request.state, "user", None)
    return user.get("id") if isinstance(user, dict) else None
