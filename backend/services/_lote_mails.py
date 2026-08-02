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
        self.parcial = False
        self.sin_procesar = 0
        self._reloj = reloj
        self._inicio = reloj()
        self._presupuesto = settings.mail_presupuesto_segundos if presupuesto is None else presupuesto

    def segundos(self) -> float:
        return round(self._reloj() - self._inicio, 3)

    def hay_margen(self) -> bool:
        """¿Queda presupuesto para OTRO mail entero?

        Se consulta ANTES de empezar cada uno, nunca en el medio: un mail se manda completo o no
        se manda. Chequear adentro dejaría un envío a medias —mandado pero sin registrar— y el
        reintento lo volvería a mandar por no encontrarlo en el log.
        """
        if self._presupuesto <= 0:
            return True
        return self.segundos() < self._presupuesto

    def destinatarios_con_margen(self, destinatarios: list):
        """Rinde destinatarios mientras haya presupuesto; al agotarse marca el corte y para.

        La guarda vive ACÁ y no en el caller porque el objeto que lleva el reloj es el que tiene
        que decidir si sigue. Recibe una LISTA y no un iterador: para decir cuántos quedaron sin
        procesar hay que saber cuántos había.
        """
        for i, d in enumerate(destinatarios):
            if not self.hay_margen():
                self.parcial = True
                self.sin_procesar = len(destinatarios) - i
                return
            yield d

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
