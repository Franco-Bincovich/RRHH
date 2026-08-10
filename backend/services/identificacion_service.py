"""
Identificación por DNI del link PÚBLICO de carga de horas.
Flujo: router (sin auth) → service → repository → DB

🔴 RECHAZO ÚNICO: HAY UN SOLO `raise` EN TODO EL ARCHIVO.
Los CINCO motivos por los que una identificación puede no prosperar —el dni no existe, existe
pero el empleado está de baja, existe pero su empresa no tiene clientes que cargar, matchea en
más de una empresa, o superó el límite de intentos— salen por el MISMO `AppError`: mismo status,
mismo code, mismo mensaje. Desde afuera son un solo estado. Que haya un único punto de salida no
es estilo: es lo que hace imposible que alguien agregue un sexto motivo con un mensaje propio y
abra un oráculo sin darse cuenta. Mismo criterio que `_oauth_state.consumir` y que la barrera de
empresa de la Fase 2.

Adentro los cinco SÍ se distinguen, y se guardan en `intentos_identificacion.resultado`: el log
es lo único que le permite a RRHH ver que alguien está probando dnis.

🔴 EL TIMING TAMBIÉN ES UN CANAL, Y SE NIVELA.
Un dni inexistente se resuelve con UNA query; uno que existe dispara una segunda (los clientes
de su empresa). Esa diferencia es medible desde afuera y convierte el mensaje uniforme en
decorativo: el atacante no lee el body, cronometra. Por eso toda respuesta —éxito o rechazo—
espera hasta un PISO FIJO de tiempo antes de salir.

⚠️ Lo que el piso NO hace, dicho sin maquillar: si algún camino TARDA MÁS que el piso, la
diferencia vuelve a filtrarse. El piso tiene que quedar por encima del peor camino real, y por
eso `_PISO_SEGUNDOS` está calibrado sobre dos queries más el INSERT del log contra Supabase, con
margen. 🚩 Si la latencia de la base cambia (otro proveedor, otra región, el cutover a RDS), hay
que RE-MEDIR: un piso que quedó corto no avisa, simplemente deja de nivelar.
Tampoco iguala el tamaño del body ni la varianza de red — son canales más ruidosos y más caros
de cerrar, y no se venden como cerrados.

🔴 LA IDENTIDAD SALE DE LA FILA PERSISTIDA. El único dato que entra del request es el dni; el
`empleado_id` y el `empresa_id` se resuelven contra la base y NO vuelven en la respuesta (ver
`schemas/horas_publico.py`). Es la condición que queda como techo del daño de esta ruta.
"""
import asyncio
from time import perf_counter
from typing import Optional, Tuple

from repositories import identificacion_repo
from repositories.sesion_horas_repo import SesionHorasRepo
from schemas.horas_publico import IdentificacionResponse
from utils.errors import AppError
from utils.logger import logger
from services._sesion_horas import emitir
from utils.rate_limit_dni import consumir_intento

# El mensaje NO nombra el motivo y NO promete que el dni exista. "Verificá el número" es una
# acción que sirve tanto si se equivocó de tecla como si no está habilitado, y no confirma nada.
_RECHAZO = ("No pudimos identificarte. Verificá el número e intentá de nuevo.",
            "IDENTIFICACION_INVALIDA", 401)

_OK = "ok"
# Piso de tiempo de respuesta. Ver la nota del encabezado: tiene que superar al peor camino real
# (dos queries + el INSERT del log). 300 ms da margen sobre los ~100-200 ms medidos contra
# Supabase desde Vercel, y el costo es tolerable porque el endpoint se llama UNA vez por sesión
# y está limitado a 10/min por IP.
_PISO_SEGUNDOS = 0.30


def _nombre_de_pila(nombre: str) -> str:
    """Primer token de `empleados.nombre`. "Juan Carlos" → "Juan".

    Es lo mínimo que permite confirmar que la persona tecleó bien SU dni. El apellido, el cargo
    y la empresa se omiten a propósito — el porqué de cada uno está en el schema."""
    return (nombre or "").strip().split(" ")[0]


class IdentificacionService:
    def __init__(self, repo=None, limitador=None, sesiones=None) -> None:
        self._repo = repo or identificacion_repo
        self._limitador = limitador or consumir_intento
        self._sesiones = sesiones or SesionHorasRepo()

    async def identificar(self, dni: str, ip: Optional[str] = None,
                          user_agent: Optional[str] = None) -> IdentificacionResponse:
        """Resuelve el dni a un nombre de pila, o rechaza. Un solo desenlace visible.

        Raises:
            AppError: IDENTIFICACION_INVALIDA (401), idéntico para los cinco motivos.
        """
        inicio = perf_counter()
        dni_limpio = (dni or "").strip()

        resultado, empleado = self._resolver(dni_limpio)

        # El log va ANTES del piso, no después: así su latencia —que es una escritura a la base y
        # varía— queda absorbida por el piso en vez de sumarse encima y volver a diferenciar.
        self._repo.registrar_intento(
            dni=dni_limpio, resultado=resultado,
            empleado_id=str(empleado["id"]) if empleado else None,
            empresa_id=str(empleado["empresa_id"]) if empleado else None,
            ip=ip, user_agent=user_agent,
        )
        await self._nivelar(inicio)

        if resultado != _OK:
            # El WARNING no incluye el dni: el log estructurado se agrega y se exporta, y el
            # valor ya está en la tabla, que es donde tiene control de acceso.
            logger.warning("Identificación pública rechazada", extra={"motivo": resultado})
            raise AppError(*_RECHAZO)
        # 🔴 La sesión se emite DESPUÉS del piso, no antes: es una escritura que solo paga el
        # camino de ÉXITO, así que adelantarla sumaría su latencia ENCIMA del piso y volvería a
        # hacer distinguible el acierto por el reloj — justo lo que la nivelación cierra.
        token, expira = emitir(self._sesiones, str(empleado["id"]), str(empleado["empresa_id"]))
        return IdentificacionResponse(
            nombre=_nombre_de_pila(empleado["nombre"]), token=token, expira_en=expira)

    def _resolver(self, dni: str) -> Tuple[str, Optional[dict]]:
        """Decide el desenlace. Devuelve (resultado, empleado|None) — NUNCA lanza.

        Que no lance es lo que permite que el caller tenga un solo `raise`: si cada rama
        levantara su propia excepción, cinco mensajes distintos serían un typo de distancia.

        🔴 EL ORDEN IMPORTA. El límite por dni va PRIMERO, antes de tocar la base: un contador
        que solo se consulta después de dos queries no protege a la base de nada.
        """
        if not dni:
            return "sin_coincidencia", None
        if not self._limitador(dni):
            return "bloqueado", None

        filas = self._repo.buscar_por_dni(dni)
        if not filas:
            return "sin_coincidencia", None
        if len(filas) > 1:
            # 🔴 `empleados` tiene UNIQUE (empresa_id, dni) y NO unique global: el mismo dni puede
            # estar cargado en dos sociedades del grupo. Las tres salidas posibles eran preguntar
            # de qué empresa —que publica justo el dato que la respuesta se cuida de no dar—,
            # elegir una —que imputaría las horas a la sociedad equivocada, en silencio— o
            # RECHAZAR. Se rechaza: es fail-closed, y queda registrado como `ambiguo` para que
            # RRHH lo vea y lo corrija en los datos, que es donde está el problema.
            # Hoy los 31 dnis de producción son distintos: es una guarda, no un caso vivo.
            return "ambiguo", None

        empleado = filas[0]
        if empleado.get("estado") != "activo":
            return "inactivo", None
        if not self._repo.hay_clientes_activos(str(empleado["empresa_id"])):
            # Sin clientes no hay nada que cargar, así que identificarse no lleva a ningún lado.
            # Se devuelve el empleado igual para que el LOG pueda decir a quién correspondía.
            return "sin_clientes", empleado
        return _OK, empleado

    @staticmethod
    async def _nivelar(inicio: float) -> None:
        """Espera hasta el piso de tiempo. `asyncio.sleep` y no `time.sleep`: bloquear el event
        loop 300 ms por request convertiría la nivelación en un problema de disponibilidad."""
        restante = _PISO_SEGUNDOS - (perf_counter() - inicio)
        if restante > 0:
            await asyncio.sleep(restante)
