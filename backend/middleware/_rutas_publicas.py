"""
QUÉ RUTAS DEL SISTEMA NO PIDEN AUTENTICACIÓN. Fuente de verdad única.

Salió de `middleware/auth.py`, que quedó en 200/200 al sumarle la quinta ruta pública. Es el
MISMO corte que ya se le hizo a ese archivo con `_empresa_header.py`, y por el mismo motivo: el
bloque no comparte ni estado ni flujo con la verificación del JWT — `_is_public` lo consulta con
un string y recibe un bool.

Que viva aparte tiene además un valor propio: **este archivo es el inventario completo de la
superficie sin auth del sistema**. Si alguien quiere saber qué se puede tocar sin token, es un
archivo, no un grep.

🔴 NUEVE RUTAS, Y NINGUNA MÁS. Cuatro incondicionales y CINCO gateadas por el mismo flag. Antes de agregar
una sexta, leer las ocho condiciones que las actuales cumplen (`docs/SEGURIDAD-PENTEST.md` y el
encabezado de `services/identificacion_service.py`): un autenticador propio y nombrado, la
identidad saliendo de la fila persistida y no del request, rechazo único, franja de rate limit
con decorador, y el path exacto sin barra final.
"""
from config.settings import settings

# ── Incondicionales ───────────────────────────────────────────────────────────
#   /health                              → probe de la plataforma; no toca la base.
#   /api/auth/login                      → autentica con contraseña (Supabase Auth).
#   /api/auth/refresh                    → autentica con un refresh token que Supabase ROTA.
#   /api/integraciones/google/callback   → autentica con un nonce de un solo uso (mig 080).
# Las cuatro tienen un autenticador REAL. La quinta, abajo, no — y por eso está gateada.
PUBLIC_ROUTES = frozenset([
    "/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/integraciones/google/callback",
])

# ── Gateada por flag: la quinta ───────────────────────────────────────────────
# 🔴 Identificación por DNI del link de carga de horas. NO entra en `PUBLIC_ROUTES` porque ese
# frozenset es INCONDICIONAL, y ésta tiene que dejar de ser pública con `HORAS_PUBLICO_ENABLED`
# apagado — que es el 100% del tiempo hasta que producto la habilite.
#
# Es un STRING EXACTO y no un regex: el dni viaja en el BODY, no en el path (un identificador
# personal no va en una URL — queda en access logs, historial y header Referer). Sin parámetro no
# hay nada que acotar, así que no hay un `.+` que pueda ensancharse por descuido. Si algún día
# llevara parámetro, el acotador es `[^/]+`, NUNCA `.+`.
#
# Sin barra final: el matcheo es igualdad de string, así que "/identificar/" NO es pública. El
# redirect de Starlette a la forma sin barra ocurre en el router, DETRÁS del middleware.
RUTA_IDENTIFICACION = "/api/horas-publico/identificar"

# Las dos ESCRITURAS del link. Son públicas igual que la identificación, pero NO son igual de
# débiles: exigen el token de sesión de 256 bits con TTL que emite el paso 1
# (`services/_sesion_horas.py`). O sea CUMPLEN las condiciones #1 y #2 que la identificación no
# puede cumplir, y por eso la debilidad del módulo queda confinada a ese primer paso.
RUTA_CARGA_HORAS = "/api/horas-publico/horas"
RUTA_CARGA_LICENCIA = "/api/horas-publico/licencia"

# La ÚNICA lectura del link. Autenticada por el mismo token de sesión que las escrituras, así que
# cumple las condiciones #1 y #2 igual que ellas. Acotada a la semana EN CURSO por diseño: sin
# rango libre, lo peor que puede leer un token robado son siete días. Ver `_semana_publica`.
RUTA_SEMANA = "/api/horas-publico/semana"

# El catálogo que necesita el select del formulario. `cliente_id` es obligatorio en la carga y
# `GET /api/clientes` exige JWT: sin esta ruta el formulario no se puede completar. Autenticada
# por el mismo token de sesión y acotada a la empresa del empleado.
RUTA_CLIENTES = "/api/horas-publico/clientes"

_GATEADAS_POR_HORAS = frozenset({RUTA_IDENTIFICACION, RUTA_CARGA_HORAS,
                                 RUTA_CARGA_LICENCIA, RUTA_SEMANA, RUTA_CLIENTES})


def rutas_publicas_activas() -> frozenset:
    """Las rutas públicas VIGENTES ahora mismo: las incondicionales más las que su flag habilita.

    Existe para que `_is_public` y el smoke test lean de UN solo lugar. `scripts/_smoke_rutas.py`
    importaba `PUBLIC_ROUTES` directo, y con una ruta gateada por flag eso se rompe en las DOS
    direcciones: encendida, `barrer_auth` la reportaría como DESPROTEGIDA (falso positivo), y
    `barrer_publicas` ni la probaría (falso negativo, el peligroso). Son exactamente los dos
    modos de falla que el comentario de ese script ya declaraba para una lista escrita a mano.

    NO incluye las de assessment: son un regex, no strings, y el smoke test compara por igualdad.
    """
    if settings.horas_publico_enabled:
        return PUBLIC_ROUTES | _GATEADAS_POR_HORAS
    return PUBLIC_ROUTES
