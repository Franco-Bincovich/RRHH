"""
Presupuesto de TIEMPO de un lote, sin saber de qué es el lote.

Extraído de `_lote_mails.py` cuando la ingesta de CVs pasó a ser el segundo caso de uso. Es la
duplicación que el Bloque G tenía anotada como pendiente: la misma cuenta —cuánto llevo, ¿me
alcanza para uno más?— estaba escrita dos veces con vocabularios distintos.

## 🔴 POR QUÉ EXISTE: EL PEOR CASO NO ES "TARDA", ES CORTARSE SIN DECIR DÓNDE

`backend/vercel.json` declara `maxDuration: 300` y no hay procesos de fondo (cero
`BackgroundTasks`, cero `asyncio.create_task`; en serverless un thread post-respuesta se muere
con la función). Un lote que se pasa del techo se corta a la mitad **sin reporte y sin saber cuál
mitad quedó hecha**. Con presupuesto, se procesa de a uno chequeando el margen ANTES de cada
unidad, y al agotarse se devuelve lo que se hizo y cuánto quedó.

## Lo que este módulo NO hace, a propósito

No cuenta éxitos, omitidos ni fallos: ese vocabulario es de cada dominio (un mail se "envía", un
CV se "crea", una fila de nómina se "carga") y generalizarlo hasta que sirva para los tres lo
dejaría sin explicar nada. Acá solo vive el reloj y la decisión de seguir o parar; el conteo lo
lleva el lote de cada caso de uso, que lo COMPONE en vez de heredarlo.

⚠️ **Queda una tercera copia sin migrar: `services/_nomina_lote.py`.** Tiene la misma cuenta con
otro vocabulario (`filas_sin_procesar`) y su propio valor de settings. No se tocó en esta sesión
por alcance; es el próximo caller natural de este módulo.

⚠️ El reloj es MONOTÓNICO y no `time.time`: un ajuste de hora del sistema no puede alterar un
presupuesto en curso.
"""
import time
from typing import Callable, Iterable, List


class Presupuesto:
    """Cuánto tiempo llevo y si me alcanza para una unidad más.

    Args:
        segundos: presupuesto disponible. **<= 0 significa SIN LÍMITE** (procesa todo), no
            "cortar en el primero": una configuración en 0 degrada al comportamiento previo en
            vez de romper la operación.
        reloj: fuente monotónica, inyectable para test.
    """

    def __init__(self, segundos: float, reloj: Callable[[], float] = time.monotonic) -> None:
        self._segundos = segundos
        self._reloj = reloj
        self._inicio = reloj()
        self.parcial = False        # ¿se cortó por presupuesto?
        self.sin_procesar = 0       # cuántas unidades quedaron sin tocar

    def transcurridos(self) -> float:
        return round(self._reloj() - self._inicio, 3)

    def hay_margen(self) -> bool:
        """¿Queda presupuesto para OTRA unidad entera?

        Se consulta ANTES de empezar cada una, nunca en el medio: una unidad se procesa completa
        o no se procesa. Chequear adentro dejaría trabajo a medias —hecho pero sin registrar— y
        el reintento lo repetiría por no encontrarlo.
        """
        return True if self._segundos <= 0 else self.transcurridos() < self._segundos

    def con_margen(self, items: List) -> Iterable:
        """Rinde items mientras haya presupuesto; al agotarse marca el corte y para.

        La guarda vive ACÁ y no en el caller porque el objeto que lleva el reloj es el que tiene
        que decidir si sigue. Recibe una LISTA y no un iterador: para decir cuántos quedaron sin
        procesar hay que saber cuántos había.
        """
        for i, item in enumerate(items):
            if not self.hay_margen():
                self.parcial = True
                self.sin_procesar = len(items) - i
                return
            yield item
