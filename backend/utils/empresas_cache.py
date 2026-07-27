"""
Caché por proceso del set de ids de empresa, para validar el header `X-Empresa-Id` sin pegarle
a la base en cada request.

Molde: el `PyJWKClient` de `middleware/auth.py`. Es el mismo problema —un conjunto chico que
cambia poquísimo y hay que consultar en cada request— y las mismas cuatro decisiones:
singleton por proceso · **el constructor no toca la base** (la primera carga es perezosa, en
el primer uso, para no penalizar el cold start en serverless) · TTL, nunca una query por
request · fallar sin colgar el request.

Guarda TODAS las empresas, activas e inactivas. La pregunta que responde este caché es
"¿este UUID es una empresa real?", no "¿está habilitada?". Filtrar por `activa` sería cambiar
quién ve qué, que es otra discusión.

🚨 ESTO ES HARDENING, NO LA BARRERA DE SEGURIDAD.
La barrera es la de Fase 2: filtra filas en el WHERE de cada query y **no depende de esto en
absoluto**. Lo que cierra este caché es que un UUID inventado entre al sistema como si fuera
una empresa y termine, por ejemplo, en `auditoria.empresa_id` —que tiene FK a `empresas`—
haciendo fallar el INSERT del evento, que `AuditService` se traga por diseño: la operación de
negocio se completa y el registro de auditoría desaparece sin dejar rastro.

🚨 FAIL-OPEN, Y NO ES UN DESCUIDO — no lo "corrijas".
Si el caché no se puede cargar, se ACEPTA el header, igual que antes de que este módulo
existiera. Suena al revés, y lo es solo en apariencia: **descartar el header ENSANCHA**, porque
`empresa_id=None` significa "todas las empresas" (vista consolidada). O sea que la opción
conservadora ante un blip de base es aceptar; descartar cambiaría en silencio la vista de todo
el mundo al consolidado. Y no hay riesgo de acceso: el consolidado ya está autorizado para
todos los roles (decisión de producto cerrada), así que un header aceptado de más nunca da
acceso a algo que el usuario no pudiera pedir escribiendo "todas".

Sin lock: dos requests concurrentes pueden refrescar a la vez. Es una lectura idempotente, así
que el peor caso es una query de más — barato comparado con meter un `threading.Lock` en el
camino async del middleware.
"""
import time

from repositories.empresa_repo import EmpresaRepo
from utils.logger import logger

_TTL_SEGUNDOS = 300  # igual que el lifespan del JWKS
# Ventana mínima entre refrescos disparados por un miss. Acota tanto el costo de una empresa
# recién creada (se ve enseguida) como el de alguien martillando UUIDs falsos (1 query cada
# 10s, sin importar el volumen). También limita los reintentos cuando la base no responde.
_GRACIA_MISS_SEGUNDOS = 10


class _EmpresasCache:
    def __init__(self, repo: EmpresaRepo | None = None) -> None:
        # Nada de trabajo acá: instanciar NO toca la base (calca el __init__ de PyJWKClient).
        self._repo = repo
        self._ids: set[str] | None = None
        self._cargado_en: float = 0.0      # último refresco EXITOSO
        self._ultimo_intento: float = 0.0  # último intento, haya salido bien o mal

    def _refrescar(self) -> None:
        """Recarga el set desde la base. Si falla, loguea y deja el set como estaba."""
        self._ultimo_intento = time.monotonic()
        try:
            self._repo = self._repo or EmpresaRepo()
            self._ids = set(self._repo.find_all_ids())
            self._cargado_en = self._ultimo_intento
        except Exception as exc:
            logger.error(
                "No se pudo cargar el caché de empresas; el header X-Empresa-Id se acepta sin validar",
                extra={"motivo": type(exc).__name__},
            )

    def existe(self, empresa_id: str) -> bool:
        """¿`empresa_id` corresponde a una empresa real?

        En el camino normal (hit) no hace ninguna query. Refresca cuando el set venció por TTL,
        y también ante un miss con más de `_GRACIA_MISS_SEGUNDOS` de antigüedad: un miss es
        justamente el caso "quizás es una empresa recién creada", y sin ese refresco quedaría
        invisible hasta 5 minutos mientras el usuario ve el consolidado sin ningún aviso.

        Args:
            empresa_id: UUID en texto, ya validado sintácticamente por el caller.

        Returns:
            True si la empresa existe —o si el caché nunca se pudo cargar (fail-open, ver el
            docstring del módulo)—; False si el set está cargado y el id no está en él.
        """
        ahora = time.monotonic()
        vencido = self._ids is None or ahora - self._cargado_en > _TTL_SEGUNDOS
        if vencido and ahora - self._ultimo_intento > _GRACIA_MISS_SEGUNDOS:
            self._refrescar()

        if self._ids is None:
            return True  # nunca se pudo cargar → fail-open
        if empresa_id in self._ids:
            return True

        # Miss: puede ser una empresa nueva. Un solo refresco, acotado por la gracia.
        if time.monotonic() - self._cargado_en > _GRACIA_MISS_SEGUNDOS:
            self._refrescar()
            return empresa_id in (self._ids or set())
        return False


_cache = _EmpresasCache()


def empresa_existe(empresa_id: str) -> bool:
    """Wrapper sobre el singleton del proceso. Ver `_EmpresasCache.existe`."""
    return _cache.existe(empresa_id)
