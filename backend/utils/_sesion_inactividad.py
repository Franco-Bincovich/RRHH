"""
La POLÍTICA de sesión: cuánto vale una sesión sin actividad, y cada cuánto se registra esa
actividad.

Salió de `utils/usuario_estado.py`, que quedó en 212 líneas contra un límite de 200 al sumarle
la inactividad. El corte no es por tamaño nada más: aquel módulo es INFRAESTRUCTURA (un caché
con TTL, fail-closed, singleton por proceso) y esto son DOS DECISIONES DE PRODUCTO —8 horas, 5
minutos— que se van a discutir con RRHH y no con nadie que sepa lo que es un TTL. Separadas, esa
discusión pasa por un archivo que no tiene lógica de caché adentro.

`_parsear_fecha` viene con ellas porque solo existe para esto: convertir el `ultimo_acceso` que
devuelve PostgREST en algo comparable contra el reloj.
"""
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # solo para el tipo: importarlo en runtime cerraría un ciclo con el caché,
    from utils.usuario_estado import EstadoUsuario  # que es quien importa este módulo.

# 8 horas sin UN SOLO request y la sesión deja de valer. No mide "estar frente a la pantalla":
# mide requests, que es lo único que el backend ve. Leer un informe sin tocar nada no cuenta
# como actividad, y está bien que no cuente — la sesión sigue abierta, no el ojo del usuario.
INACTIVIDAD_MAXIMA = timedelta(hours=8)

# Cada cuánto, COMO MÁXIMO, se escribe `ultimo_acceso`. Sin esto, cada request de cada usuario
# sería un UPDATE: convertiría una tabla que hoy se lee en una que se escribe todo el tiempo,
# para ganar una precisión (el segundo exacto del último acceso) que a una ventana de 8 horas
# no le cambia nada.
THROTTLE_ESCRITURA = timedelta(minutes=5)


def parsear_fecha(valor) -> Optional[datetime]:
    """Timestamp de PostgREST → datetime aware. None si viene vacío o ilegible.

    Un valor sin zona se asume UTC: comparar un naive con un aware LANZA, y una excepción acá
    tumbaría el request de cualquiera cuya fila tenga un formato inesperado."""
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def sesion_expirada(estado: "EstadoUsuario") -> bool:
    """¿Pasaron más de `INACTIVIDAD_MAXIMA` sin un solo request de este usuario?

    🔴 `ultimo_acceso=None` devuelve False, y NO es un descuido: hasta esta tanda la columna
    estuvo muerta, así que TODAS las filas de producción la tienen en NULL. Tratar el NULL como
    "hace infinito que no aparece" dejaría a los 3 usuarios de RRHH afuera en el primer request
    después del deploy, sin ninguna forma de volver a entrar salvo tocar la base a mano. NULL
    significa "no hay evidencia de inactividad"; el propio request que lo encuentra lo sella.
    """
    if not estado.resuelto or estado.ultimo_acceso is None:
        return False
    return datetime.now(timezone.utc) - estado.ultimo_acceso > INACTIVIDAD_MAXIMA
