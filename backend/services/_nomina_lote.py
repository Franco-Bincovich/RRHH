"""
Acumulador del resultado de un import de nómina, fila por fila.

Extraído de `nomina_empleados_service.py`, que llegó a 141 contra un límite de 150. El service
tenía siete variables sueltas de acumulación (`creados`, `actualizados`, `cargados_ok`, `total`,
`con_faltantes`, `no_cargados`, `ids_creados`) manipuladas dentro del loop; acá pasan a ser
estado de un objeto y el loop queda en tres líneas.

La lógica se movió VERBATIM: la clasificación en los tres grupos (OK / con faltantes / no
cargados), el número de fila (`start=2`, porque la 1 es el encabezado) y los conteos son
idénticos a antes.

Lleva además el PRESUPUESTO DE TIEMPO: el objeto que sabe cuánto se hizo es el que decide si hay
margen para otra fila. Ver `hay_margen`.
"""
import time
from typing import Callable, List, Optional

from config.settings import settings
from schemas.importacion_nomina_empleados import (
    FilaConFaltantes, FilaNoCargada, ImportacionNominaEmpleadosResult,
)


def resultado_headers_invalidos(motivo: str) -> ImportacionNominaEmpleadosResult:
    """Resultado de un archivo cuyo encabezado no sirve: nada se procesó, nada se tocó.

    La fila reportada es la 1 (el encabezado), no la 2: el error no es de una fila de datos.
    """
    return ImportacionNominaEmpleadosResult(
        total=0, creados=0, actualizados=0, cargados_ok=0, con_faltantes=[],
        no_cargados=[FilaNoCargada(fila=1, empleado="(encabezados)", motivo=motivo)])


class LoteNomina:
    """Estado de un import en curso: cuántas filas entraron en cada grupo, con qué detalle, y
    cuánto tiempo queda.

    Args:
        presupuesto: segundos disponibles. None → toma `settings.import_presupuesto_segundos`.
            Un presupuesto <= 0 significa SIN LÍMITE (procesa todo), no "cortar en la fila 1":
            así una configuración en 0 degrada al comportamiento previo en vez de romper el import.
        reloj: fuente de tiempo monotónica, inyectable para los tests. Se usa `monotonic` y no
            `time.time` porque un ajuste de hora del sistema no debe alterar el presupuesto.
    """

    def __init__(self, presupuesto: Optional[float] = None,
                 reloj: Callable[[], float] = time.monotonic) -> None:
        self.total = 0
        self.creados = 0
        self.actualizados = 0
        self.cargados_ok = 0
        self.con_faltantes: List[FilaConFaltantes] = []
        self.no_cargados: List[FilaNoCargada] = []
        # Ids de las altas: nominan el evento de auditoría de lote (las altas no emiten el suyo).
        self.ids_creados: List[str] = []

        self._reloj = reloj
        self._inicio = reloj()
        self._presupuesto = settings.import_presupuesto_segundos if presupuesto is None else presupuesto
        self.parcial = False
        self.ultima_fila_procesada: Optional[int] = None
        self.filas_sin_procesar = 0

    # ── Presupuesto ──

    def segundos(self) -> float:
        """Segundos consumidos desde que arrancó el lote."""
        return round(self._reloj() - self._inicio, 3)

    def hay_margen(self) -> bool:
        """¿Queda presupuesto para procesar OTRA fila entera?

        Se consulta ANTES de empezar una fila, nunca en medio: una fila se procesa completa o no
        se procesa. Si se chequeara adentro, un corte dejaría el empleado creado pero sin su
        proyecto o su cesión, que es peor que no haberlo tocado — y el reintento no lo arreglaría,
        porque el dedup por DNI lo mandaría por la rama de update sin volver a intentar lo que
        faltó.
        """
        if self._presupuesto <= 0:
            return True    # sin límite configurado
        return self.segundos() < self._presupuesto

    def cortar(self, filas_restantes: int) -> None:
        """Marca el lote como parcial. `filas_restantes` son las que quedaron SIN TOCAR."""
        self.parcial = True
        self.filas_sin_procesar = filas_restantes

    def filas_con_margen(self, filas: List[dict]):
        """Rinde `(nº de fila, fila)` mientras haya presupuesto; al agotarse marca el corte y para.

        La guarda vive ACÁ y no en el caller porque el objeto que lleva el reloj es el que tiene
        que decidir si sigue. El chequeo ocurre ANTES de rendir cada fila, así que el consumidor
        no puede quedarse a mitad de una: o la recibe entera o no la recibe.

        Recibe una LISTA, no el reader: para decir cuántas filas quedaron sin procesar hay que
        saber cuántas había. Un CSV de nómina son cientos de filas de ~200 bytes, así que
        materializarlo no es un costo relevante.
        """
        for i, raw in enumerate(filas):
            if not self.hay_margen():
                self.cortar(len(filas) - i)
                return
            self.contar_fila()
            yield i + 2, raw       # la fila 1 del archivo es el encabezado

    def contar_fila(self) -> None:
        """Una fila más leída del CSV, con independencia de cómo termine."""
        self.total += 1

    def registrar_cargada(self, fila: int, empleado: str, nuevo: bool, faltan: list,
                          empleado_id: Optional[str]) -> None:
        """Fila que SE ESCRIBIÓ. `faltan` no vacío la manda a "con faltantes", igual cargada."""
        if nuevo:
            self.creados += 1
            if empleado_id:
                self.ids_creados.append(empleado_id)
        else:
            self.actualizados += 1
        if faltan:
            self.con_faltantes.append(FilaConFaltantes(fila=fila, empleado=empleado, faltan=faltan))
        else:
            self.cargados_ok += 1
        self.ultima_fila_procesada = fila

    def registrar_fallo(self, fila: int, empleado: str, motivo: str) -> None:
        """Fila que NO se cargó. El lote NO aborta: se anota el motivo y se sigue con la siguiente.

        Cuenta como PROCESADA: se la miró y se decidió. El reintento la va a volver a rechazar
        por el mismo motivo, así que "hasta dónde llegué" tiene que incluirla."""
        self.no_cargados.append(FilaNoCargada(fila=fila, empleado=empleado, motivo=motivo))
        self.ultima_fila_procesada = fila

    def resultado(self) -> ImportacionNominaEmpleadosResult:
        """Proyecta el estado acumulado al schema de respuesta."""
        return ImportacionNominaEmpleadosResult(
            total=self.total, creados=self.creados, actualizados=self.actualizados,
            cargados_ok=self.cargados_ok, con_faltantes=self.con_faltantes,
            no_cargados=self.no_cargados, parcial=self.parcial,
            ultima_fila_procesada=self.ultima_fila_procesada,
            filas_sin_procesar=self.filas_sin_procesar, segundos=self.segundos())
