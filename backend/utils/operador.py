"""
Quién está haciendo el request. El dato que todo evento de auditoría necesita para servir.

Nació el 24/8/2026 al cablearle auditoría a `/objetivos`, cuando el router de escrituras quedó
en 84/80 y el helper que lo pasaba de largo resultó no ser de objetivos: **50 routers escriben
`request.state.user.get("id", "system")` a mano y no existía un solo lugar donde viviera.**

🔴 NO SE MIGRARON LOS OTROS 49 EN ESA TANDA, y es deliberado: tocar 49 routers para reemplazar
una expresión que hoy funciona es exactamente el refactor preventivo que este repo no hace
(regla #1: no modificar archivos fuera del scope de la tarea). Este módulo existe para que el
próximo router que lo necesite no escriba la copia 51, y para que la migración —si alguna vez se
decide— sea un reemplazo mecánico contra un símbolo, no contra un literal repetido.

⚠️ POR QUÉ NO VA EN `utils/empresa.py`, que es el vecino obvio. Ese archivo resuelve LA EMPRESA
del request y su nombre lo dice; meterle el usuario lo volvería "utils/cosas_del_request.py" sin
renombrarlo, que es como los módulos dejan de decir qué tienen adentro. Son dos ejes distintos
—de qué empresa se está mirando vs. quién está mirando— y el repo ya los trata así en todas las
firmas de service (`empresa_id` y `usuario_id` viajan siempre separados, nunca juntos).
"""
from starlette.requests import Request

# El mismo default que ya usaban los 50 call sites a mano. `AuthMiddleware` es fail-closed y
# garantiza que haya un user en `request.state`, así que este valor no debería aparecer nunca en
# la tabla. Está para que un evento se grabe con un dueño raro antes que PERDERSE: un
# AttributeError acá lo tragaría `AuditService.registrar`, que por diseño no propaga, y el evento
# desaparecería sin dejar ni un log de negocio. Un "system" en `/auditoria` es una anomalía
# visible; un evento que no está no se puede ni buscar.
SIN_USUARIO = "system"


def usuario_id(request: Request) -> str:
    """El id del operador del request, tal como lo dejó `AuthMiddleware` en `request.state`.

    Args:
        request: el request de FastAPI/Starlette.

    Returns:
        El user id, o `SIN_USUARIO` si el middleware no dejó ninguno (ver la nota de arriba).
    """
    return getattr(request.state, "user", {}).get("id", SIN_USUARIO)
