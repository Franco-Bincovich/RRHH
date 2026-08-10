"""
La identidad ENTRE el paso 1 del link público (identificarse) y el paso 2 (cargar).

🔴 ES LA DECISIÓN DE DISEÑO DEL MÓDULO, y el porqué completo —las tres alternativas que se
evaluaron y por qué se descartaron dos— está en el encabezado de `migrations/105_sesiones_horas.sql`.
El resumen: el paso 1 emite un token OPACO de 256 bits y el paso 2 lo presenta; el `empleado_id`
y el `empresa_id` salen de la fila persistida y NUNCA del body.

🔴 LO QUE ESTO CAMBIA EN EL NIVEL DE SEGURIDAD DEL MÓDULO, que es el punto:
El paso 1 no puede cumplir las condiciones #1 y #2 de las rutas públicas (autenticador propio;
nonce de 256 bits con TTL) porque el acceso es solo con DNI, y un DNI es enumerable. **El paso 2
SÍ las cumple**: un token de `secrets.token_urlsafe(32)`, guardado hasheado, con vencimiento.
O sea la debilidad queda CONFINADA a la identificación, y todo lo que ESCRIBE está detrás de un
autenticador de verdad. Adivinar un DNI ya no alcanza para escribir.

Funciones libres que reciben el repo — mismo molde que `_oauth_state.py`, del que esto es
hermano directo. Las diferencias con aquel (no es de un solo uso, TTL más largo) están explicadas
en la migración y en `SesionHorasRepo.buscar_vigente`.

RECHAZO ÚNICO: los tres motivos por los que un token puede no servir —ausente, desconocido,
vencido— salen por el MISMO AppError, con el mismo code, mensaje y status. Distinguirlos le
contaría al que pregunta en cuál de los tres está.
"""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional, Tuple

from utils.errors import AppError
from utils.logger import logger

# 30 minutos. Contra los 10 de `oauth_states`: allá el único paso humano es aceptar un
# consentimiento; acá la persona completa un formulario varias veces —el día, o la semana— y
# vencerle la sesión a la mitad la manda a re-tipear el DNI.
_TTL_MINUTOS = 30
# 32 bytes → 256 bits. Es lo que hace que guardar un SHA-256 sin salt alcance.
_BYTES_ENTROPIA = 32

_CODE_RECHAZO = "SESION_INVALIDA"
_MENSAJE_RECHAZO = "Tu sesión expiró. Volvé a identificarte con tu DNI."


def _hash(token: str) -> str:
    """SHA-256 hex del token. Determinístico a propósito: el lookup es por índice único."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def emitir(repo, empleado_id: str, empresa_id: str) -> Tuple[str, datetime]:
    """Crea una sesión y devuelve (token EN CRUDO, cuándo vence).

    El crudo se devuelve UNA vez, acá, y de la base solo sale su hash. Purga las vencidas antes
    de insertar, así la recién creada nunca es candidata de su propia limpieza.

    Args:
        repo: SesionHorasRepo.
        empleado_id / empresa_id: resueltos server-side desde la fila que el DNI matcheó.

    Returns:
        (token, expires_at). El token es lo único que el cliente necesita para el paso 2.
    """
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(minutes=_TTL_MINUTOS)
    token = secrets.token_urlsafe(_BYTES_ENTROPIA)
    repo.purgar_vencidas(ahora.isoformat())
    repo.crear(_hash(token), empleado_id, empresa_id, expira.isoformat())
    return token, expira


def resolver(repo, token: Optional[str]) -> Tuple[str, str]:
    """Verifica un token y devuelve de quién es. LA ÚNICA fuente de identidad del paso 2.

    Args:
        repo: SesionHorasRepo.
        token: El valor que mandó el cliente. Puede ser None.

    Returns:
        (empleado_id, empresa_id), los dos de la fila PERSISTIDA.

    Raises:
        AppError: SESION_INVALIDA (401), idéntico para los tres motivos de rechazo.
    """
    fila = repo.buscar_vigente(_hash(token), datetime.now(UTC).isoformat()) if token else None
    if not fila:
        # El WARNING no incluye el token: un log estructurado se agrega y se exporta.
        logger.warning("Sesión de carga de horas rechazada")
        raise AppError(_MENSAJE_RECHAZO, _CODE_RECHAZO, 401)
    return str(fila["empleado_id"]), str(fila["empresa_id"])
