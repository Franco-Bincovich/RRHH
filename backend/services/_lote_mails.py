"""
Presupuesto de tiempo de un envío MASIVO de mails, con reporte parcial.

Molde: `services/_nomina_lote.LoteNomina`, que resuelve exactamente el mismo problema para el
import de nómina — y se copia el patrón, no el archivo: aquel acumula filas de un CSV y este
destinatarios, así que compartir la clase obligaría a generalizarla hasta que no explique nada.

## 🔴 EL PEOR CASO NO ES "TARDA": ES MANDAR 30 Y REINTENTAR LOS 30

`backend/vercel.json` declara `maxDuration: 300` y no hay procesos de fondo (cero
`BackgroundTasks`, cero `asyncio.create_task` en todo el backend — y en serverless un thread
post-respuesta se muere con la función). Un envío de 50 mails a ~2 s cada uno son ~100 s de
alguien mirando un spinner; con más volumen, el corte a los 300 s deja la mitad mandada, sin
reporte y sin saber cuál mitad.

Con presupuesto: se manda de a uno chequeando el margen ANTES de cada mail, y al agotarse se
devuelve el reporte de lo que salió y lo que quedó. **La idempotencia hace el resto**: el
reintento consulta `mail_enviado.ya_enviado` y saltea los que ya salieron. Sin eso, reintentar
un lote cortado mandaría de nuevo los 30 primeros — que es el daño real, porque es visible para
50 personas de afuera.

⚠️ El presupuesto es MÁS CHICO que el del import (280 s) a propósito: acá cada unidad es una
llamada de red externa con su propio timeout, no una escritura a nuestra base. ~120 s es el punto
de partida; el log de envíos da los datos para calibrarlo con la realidad en vez de a ojo.
"""
import time
from typing import Callable, List, Optional

from config.settings import settings
from services._presupuesto import Presupuesto


class LoteMails:
    """Estado de un envío masivo: cuántos salieron, cuáles fallaron, cuánto tiempo queda.

    Args:
        presupuesto: segundos disponibles. None → `settings.mail_presupuesto_segundos`.
            <= 0 significa SIN LÍMITE (manda todo), no "cortar en el primero": una configuración
            en 0 degrada al comportamiento previo en vez de romper el envío.
        reloj: fuente monotónica, inyectable para test. Monotónica y no `time.time` porque un
            ajuste de hora del sistema no debe alterar el presupuesto.
    """

    def __init__(self, presupuesto: Optional[float] = None,
                 reloj: Callable[[], float] = time.monotonic) -> None:
        self.enviados = 0
        self.omitidos = 0                 # ya se les había mandado (idempotencia)
        self.fallidos: List[dict] = []
        # El reloj y la decisión de seguir viven en `Presupuesto`, COMPUESTO y no heredado: acá
        # queda el vocabulario del envío (enviados/omitidos/fallidos), que es lo que no se puede
        # generalizar sin dejar de explicar nada. `parcial` y `sin_procesar` se delegan para que
        # el contrato que ven los callers no cambie.
        self._p = Presupuesto(
            settings.mail_presupuesto_segundos if presupuesto is None else presupuesto, reloj)

    @property
    def parcial(self) -> bool:
        return self._p.parcial

    @property
    def sin_procesar(self) -> int:
        return self._p.sin_procesar

    def segundos(self) -> float:
        return self._p.transcurridos()

    def hay_margen(self) -> bool:
        """¿Queda presupuesto para OTRO mail entero? Ver `Presupuesto.hay_margen`."""
        return self._p.hay_margen()

    def destinatarios_con_margen(self, destinatarios: list):
        """Rinde destinatarios mientras haya presupuesto. Ver `Presupuesto.con_margen`."""
        return self._p.con_margen(destinatarios)

    def registrar_envio(self) -> None:
        self.enviados += 1

    def registrar_omitido(self) -> None:
        """Ya se le había mandado hoy: no es un error ni un envío. Se cuenta aparte para que el
        reporte de un reintento no diga "0 enviados" y parezca que no hizo nada."""
        self.omitidos += 1

    def registrar_fallo(self, destinatario: str, motivo: str) -> None:
        self.fallidos.append({"destinatario": destinatario, "motivo": motivo})

    def resumen(self) -> dict:
        return {"enviados": self.enviados, "omitidos": self.omitidos, "fallidos": self.fallidos,
                "parcial": self.parcial, "sin_procesar": self.sin_procesar,
                "segundos": self.segundos()}
