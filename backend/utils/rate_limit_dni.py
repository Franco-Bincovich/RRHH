"""
Segundo eje del rate limit de la ruta pública de identificación: el contador POR DNI INTENTADO.

🔴 POR QUÉ NO ALCANZA EL LÍMITE POR IP QUE YA TIENE EL ENDPOINT. Son dos ataques distintos y
ninguno de los dos contadores cubre lo del otro:

  · POR IP (10/min, el decorador de slowapi) frena a UNA máquina probando muchos dnis. No frena
    a alguien con un pool de IPs residenciales: cada IP arranca su propio contador en cero.
  · POR DNI (este módulo) no frena la enumeración —un enumerador prueba un dni DISTINTO cada
    vez, así que nunca toca dos veces el mismo contador— pero sí frena el uso repetido de un dni
    ajeno YA CONOCIDO, que es el otro escenario: alguien que averiguó el dni de un compañero y
    lo usa todos los días. Contra eso el límite por IP no hace nada, porque el volumen por IP es
    de una persona normal.

Los dos juntos cubren los dos; cualquiera solo deja la mitad abierta.

🔴 SE APOYA EN EL STORAGE DE `utils/rate_limit.py`, no en un dict propio. `limiter.limiter` es
la estrategia de `limits` que ya usa la app, así que este contador hereda `RATE_LIMIT_STORAGE_URI`
tal cual: hoy `memory://` (por proceso) y el día que infraestructura conecte Redis pasa a ser
compartido sin tocar una línea de acá. Un dict propio habría quedado fuera de esa mejora para
siempre. `limiter.limiter.get_window_stats` ya se usa en `_retry_after`, así que no es una API
privada nueva.

⚠️ LA MISMA LIMITACIÓN QUE EL RESTO DEL RATE LIMIT, dicha sin maquillar: con `memory://` el
contador es POR PROCESO. En serverless cada cold start arranca en cero y con N instancias el
límite efectivo es N×. Para las otras cuatro rutas públicas eso es una degradación aceptable
porque las cuatro tienen un autenticador real detrás. Acá el rate limit ES la única defensa, así
que `RATE_LIMIT_STORAGE_URI=redis://...` deja de ser una mejora y pasa a ser precondición.

🔴 LA CLAVE ES UN HASH DEL DNI, Y ACÁ SÍ TIENE SENTIDO —al revés que en el log de la migración
104, donde se guarda en claro—. No es por confidencialidad (8 dígitos son reversibles en
segundos): es que el valor NO TIENE NINGUNA UTILIDAD como clave, es un identificador opaco de
bucket. Hashearlo no cuesta nada y evita rociar dnis por el keyspace de un Redis que mañana
puede ser compartido o inspeccionado. En el log el valor SÍ tiene utilidad forense y hashearlo
la destruiría a cambio de nada. Misma pregunta, respuestas distintas, por motivos distintos.
"""
import hashlib

from limits import parse

from utils.rate_limit import limiter

# 20 por hora y por dni. Generoso para un humano —el empleado se identifica una vez por sesión,
# y 20 tolera de sobra reintentos y varias cargas en el día— y un techo real para un script que
# machaca un dni ajeno: 480/día en vez de infinito.
# La ventana es HORARIA y no por minuto a propósito: el abuso que este eje ataca es sostenido en
# el tiempo, no una ráfaga. Las ráfagas ya las corta el límite por IP.
LIMITE_POR_DNI = parse("20/hour")

_ESPACIO = "identificacion-dni"


def _clave(dni: str) -> str:
    """SHA-256 del dni normalizado. Ver la nota del encabezado sobre por qué acá SÍ se hashea."""
    return hashlib.sha256(dni.strip().encode("utf-8")).hexdigest()


def consumir_intento(dni: str) -> bool:
    """Registra un intento contra el contador del dni y dice si estaba permitido.

    Returns:
        True si el intento entra dentro del límite; False si lo superó.

    🔴 SE CONSUMEN LOS INTENTOS FALLIDOS TAMBIÉN, y es lo que hace útil al contador: si solo se
    contaran los aciertos, machacar un dni ajeno sería gratis hasta acertar.

    Fail-OPEN ante un fallo del storage: si el backend de contadores no responde, se DEJA PASAR.
    Es el mismo criterio que `utils/empresas_cache` documenta — un blip de infraestructura no
    puede dejar afuera a todo el padrón de una feature cuyo público son empleados sin cuenta.
    El eje por IP sigue en pie mientras tanto, así que no queda sin ninguna defensa.
    """
    try:
        return bool(limiter.limiter.hit(LIMITE_POR_DNI, _ESPACIO, _clave(dni)))
    except Exception:  # noqa: BLE001 — ver el docstring
        return True
