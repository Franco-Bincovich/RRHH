"""
Guarda: no se puede dar de baja al usuario que sostiene la casilla de correo del sistema.

Función libre que recibe su colaborador (el repo del remitente) — mismo molde que
`services/_usuario_alta.py`, que se extrajo de este mismo service por el mismo motivo. El
service la delega en una línea.

Vive acá y no dentro de `usuario_service` porque la explicación de POR QUÉ es más larga que el
código, y con ella adentro el service quedaba en 171/150. Sacarla es lo que deja el
razonamiento escrito sin comprar deuda de líneas.
"""
from typing import Optional

from utils.errors import AppError
from utils.logger import logger


def ensure_no_es_remitente(remitente_repo, user_id: str) -> None:
    """Bloquea la baja del usuario del que cuelga la casilla de correo del sistema.

    El daño que evita: `usuario_integraciones` es POR USUARIO, así que la casilla del sistema
    cuelga de una persona concreta. Bajarla apaga el envío de mails de TODO el sistema —no solo
    los de esa persona— y sin esta guarda nadie se entera hasta que alguien intenta mandar uno y
    le salta `MAIL_SIN_REMITENTE`. Esto mueve el aviso al momento de la baja, que es cuando
    todavía se puede hacer algo al respecto.

    🔴 ES 409 Y NO 400: el pedido está bien formado y el usuario existe. Lo que impide la baja es
    el ESTADO del sistema (esa persona es la casilla), y ese estado es reversible designando
    otra. Un 400 diría "mandaste mal el pedido", que es falso y manda a mirar al lugar
    equivocado.

    El mensaje nombra la consecuencia y la salida concreta. Un 409 "conflicto de estado" no le
    sirve a nadie: quien lo lee está en la pantalla de usuarios, no sabe qué es una integración
    de Google, y necesita que le digan a dónde ir.

    ⚠️ Es una guarda de APLICACIÓN. El `ON DELETE CASCADE` de la FK sigue igual y NO se toca:
    desde el 3/8 la baja es blanda (`activo=false` + ban), así que ese CASCADE ya no se dispara
    por esta vía — pero el `activo=false` apaga el envío igual, porque la integración queda
    colgando de un usuario inactivo. **El agujero existe aunque el CASCADE nunca corra**, y por
    eso la guarda no puede vivir en la base.

    Args:
        remitente_repo: repo con `get_remitente()` (la fila entera de la casilla, o None).
        user_id: usuario que se quiere dar de baja.

    Raises:
        AppError: USUARIO_ES_REMITENTE_SISTEMA (409) si `user_id` sostiene la casilla.
    """
    # 🔴 ES FAIL-OPEN ANTE UN FALLO DE LECTURA, y es deliberado. Si no se puede averiguar quién
    # sostiene la casilla, la baja SIGUE. Dar de baja a alguien es una acción de SEGURIDAD —se
    # usa para sacar a una persona que ya no tiene que estar adentro— y no puede quedar bloqueada
    # porque un subsistema no relacionado esté caído. Lo que esta guarda evita es un ERROR
    # OPERATIVO, no un ataque, y su peor caso es recuperable (designar otra casilla). Al revés,
    # fail-closed convertiría un blip de base en "no se puede echar a nadie". Se loguea a ERROR
    # para que quede rastro de que no se verificó.
    try:
        remitente: Optional[dict] = remitente_repo.get_remitente()
    except Exception:
        logger.error("No se pudo verificar la casilla del sistema; la baja sigue igual",
                     extra={"user_id": user_id})
        return
    # Sin casilla designada no hay nada que proteger: la baja de cualquiera sigue su curso.
    # `get_remitente()` trae la fila ENTERA (`select("*")`), de ahí sale el `user_id`.
    if not remitente or not remitente.get("user_id"):
        return
    if str(remitente["user_id"]) != str(user_id):
        return
    raise AppError(
        "No se puede dar de baja a esta persona: su cuenta es la casilla desde la que el "
        "sistema envía todos los mails. Entrá a Configuración → Integraciones, designá otra "
        "casilla del sistema, y recién después dala de baja.",
        "USUARIO_ES_REMITENTE_SISTEMA", 409,
    )
