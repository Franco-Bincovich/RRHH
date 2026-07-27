"""
Nonces del flujo de autorización OAuth: generación y consumo.

Un flujo de autorización ocurre en dos requests separados —uno arma la URL de consentimiento,
otro recibe el callback cuando el proveedor redirige el navegador de vuelta— y el `state` es
lo que los ata: un valor aleatorio de un solo uso que se emite en el primero y se verifica en
el segundo. **La identidad del usuario sale de la fila persistida, nunca del query param del
callback**, así que el flujo termina conectando la cuenta al usuario que efectivamente lo
inició.

Sin nada de Google: acá no hay proveedor, scopes ni URLs. `proveedor` es un campo más, para
que sumar una segunda integración OAuth no necesite ni otra tabla ni otro módulo. Lo
específico de Google vive en services/_google_oauth.py.

Funciones libres que reciben el repo — mismo molde que _vacaciones_saldo.calcular_saldo(repo,
...) y _onboarding_iniciar.iniciar(repo, ...).

RECHAZO ÚNICO: los cuatro motivos por los que un state puede no servir —ausente, desconocido,
vencido, ya usado— salen por el MISMO AppError, con el mismo código, el mismo mensaje y el
mismo status. Distinguirlos le contaría al que pregunta en cuál de los cuatro casos está, que
es información que no necesita para completar un flujo legítimo. Mismo criterio que la barrera
de empresa de la Fase 2. El WARNING que se loguea tampoco incluye el valor recibido.
"""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from utils.errors import AppError
from utils.logger import logger

# El flujo se completa en segundos: el único paso humano es aceptar el consentimiento. 10
# minutos cubre de sobra un 2FA o un selector de cuenta de por medio, y no tiene sentido ir
# más allá porque los authorization codes de Google expiran en ese mismo orden.
_TTL_MINUTOS = 10
# 32 bytes → 256 bits de entropía. Es lo que hace que guardar un SHA-256 sin salt alcance:
# contra un valor así no hay diccionario ni tabla precomputada.
_BYTES_ENTROPIA = 32

_CODE_RECHAZO = "OAUTH_STATE_INVALIDO"
_MENSAJE_RECHAZO = "No se pudo completar la conexión. Volvé a intentarlo."


def _hash(state: str) -> str:
    """SHA-256 hex del nonce. Determinístico a propósito: el lookup es por índice único."""
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def _vigente(fila: dict) -> bool:
    """True si la fila todavía no venció. Un `expires_at` ausente o ilegible cuenta como vencido."""
    expira = fila.get("expires_at")
    if not expira:
        return False
    try:
        return datetime.fromisoformat(str(expira).replace("Z", "+00:00")) > datetime.now(UTC)
    except ValueError:
        return False


def generar(repo, user_id: str, proveedor: str = "google") -> str:
    """Emite un state nuevo y lo deja persistido a nombre de `user_id`.

    Purga los vencidos en el mismo camino, antes de insertar: es el request que crea las filas,
    así que limpiar acá mantiene la tabla acotada sin depender de un job periódico. Se purga
    primero para que el state recién emitido nunca sea candidato de su propia limpieza.

    Args:
        repo: OAuthStateRepo donde persistir.
        user_id: UUID del usuario que inicia el flujo; es a quien se conectará la cuenta.
        proveedor: Integración para la que se emite. Hoy siempre "google".

    Returns:
        El nonce en crudo, para mandarlo como parámetro `state` al proveedor. De la base solo
        sale su hash.
    """
    ahora = datetime.now(UTC)
    state = secrets.token_urlsafe(_BYTES_ENTROPIA)
    repo.purgar_vencidos(ahora.isoformat())
    repo.crear(_hash(state), user_id, proveedor, (ahora + timedelta(minutes=_TTL_MINUTOS)).isoformat())
    return state


def consumir(repo, state, proveedor: str = "google") -> str:
    """Verifica un state, lo da por usado y devuelve de qué usuario era.

    El borrado ES la verificación (ver OAuthStateRepo.consumir): la fila se entrega una sola
    vez, así que un mismo state no puede completar dos flujos.

    Args:
        repo: OAuthStateRepo contra el que verificar.
        state: El valor recibido en el callback. Puede ser None.
        proveedor: Integración esperada. Hoy siempre "google".

    Returns:
        El `user_id` de la fila persistida — la única fuente de identidad de este flujo.

    Raises:
        AppError: OAUTH_STATE_INVALIDO (400), idéntico para los cuatro motivos de rechazo.
    """
    fila = repo.consumir(_hash(state), proveedor) if state else None
    if fila is None or not _vigente(fila):
        logger.warning("State de OAuth rechazado", extra={"proveedor": proveedor})
        raise AppError(_MENSAJE_RECHAZO, _CODE_RECHAZO, 400)
    return str(fila["user_id"])
