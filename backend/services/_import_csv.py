"""
ARMADO del CSV subido: delimitador, cabeceras y numeración de filas.

El ENCODING vive en `_import_encoding` y este módulo lo usa: son dos responsabilidades y la
política de encoding difiere por flujo (ver allá), mientras que el delimitador y la forma de
comparar cabeceras son las mismas para todos.

## 🚩 DÓNDE VA EL MAPEO DE COLUMNAS CUANDO LLEGUE EL ARCHIVO DE NOVEDADES

RRHH va a subir un archivo mensual de novedades (ausencias y vacaciones pendientes). **Su
vocabulario de columnas NO está escrito y no hay que inventarlo**: un mapeo con nombres
provisorios es documentación disfrazada de código, y el archivo definitivo puede traer columnas
que los históricos no tienen.

Cuando llegue, el mapeo va en un módulo propio —`services/_novedades_columnas.py`— con la misma
forma que `_nomina_empleados_transforms.py`: qué columnas espera, cuáles son obligatorias y cómo
se arma el dict de una fila. Los VALORES ya tienen parsers y no hay que escribir ninguno:
`_nomina_parsers.parse_fecha` (acepta `d/m/yyyy` sin padding), `limpiar`, `parse_bool`.

Los dos históricos que se vieron: **inasistencias** (trae DNI y CUIT) y **vacaciones** (trae solo
legajo). Los dos en el mismo formato que nómina: `;`, latin-1, CRLF, fechas `d/m/yyyy`.

🔴 **BLOQUEO CONOCIDO, y no es un problema de código:** el archivo de vacaciones solo trae
LEGAJO, y `legajo` está **0 de 19** en producción — RRHH nunca lo mandó, aunque el import de
nómina ya sabe leerlo (`HEADERS_OPCIONALES`). **Ese import hoy no tendría con qué matchear a
nadie.** Se resuelve de una de dos formas, las dos con RRHH: que la nómina traiga la columna
Legajo, o que el archivo de vacaciones traiga DNI. **No inventar un fallback por nombre**: el
archivo de vacaciones tampoco trae nombre.
"""
import csv
import io
from typing import Iterator, List, Optional, Tuple

from services._import_encoding import decodificar


def abrir(data: bytes, delimiter: str = ";", permitir_latin1: bool = True) -> csv.DictReader:
    """Decodifica y devuelve el `DictReader` listo. Es el único lugar donde se elige delimitador.

    Devuelve el reader y no la lista de filas a propósito: los dos flujos que lo usan lo
    consumen distinto (nómina lo materializa para su presupuesto de tiempo, evaluaciones lo
    itera rindiendo problemas), y materializar acá le impondría a uno la forma del otro.
    """
    return csv.DictReader(io.StringIO(decodificar(data, permitir_latin1)), delimiter=delimiter)


def normalizar_header(s: Optional[str]) -> str:
    """Clave de comparación de una cabecera: trim + colapsa espacios internos + casefold.

    Es la normalización de nómina, que es la MÁS TOLERANTE de las dos que había (evaluaciones
    hacía `strip().upper()`, sin colapsar espacios internos). Unificar hacia la más tolerante
    solo puede aceptar cabeceras que antes se rechazaban —`"NOTA  FINAL"` con doble espacio—,
    nunca rechazar una que antes pasaba: no puede romper un archivo que hoy funciona.
    """
    return " ".join((s or "").split()).casefold()


def faltantes(fieldnames: Optional[List[str]], requeridas: List[str]) -> List[str]:
    """Las columnas requeridas que NO están, con su nombre ORIGINAL para el mensaje de error.

    Se devuelven los nombres tal como los declaró el caller —no normalizados— porque el mensaje
    lo lee alguien de RRHH que tiene el archivo abierto: "Faltan columnas: nota final" no se
    encuentra en la planilla, "NOTA FINAL" sí.
    """
    presentes = {normalizar_header(f) for f in (fieldnames or []) if f}
    return [c for c in requeridas if normalizar_header(c) not in presentes]


def filas(reader: csv.DictReader, upper: bool = False) -> Iterator[Tuple[int, dict]]:
    """Rinde `(nº de fila del archivo, fila)` con los valores trimeados.

    El número arranca en 2 porque la fila 1 es el encabezado: es el número que ve quien abre el
    CSV en Excel, y por eso el reporte de errores es accionable.

    `upper=True` además pasa las CLAVES a mayúsculas — lo necesita evaluaciones, cuyo vocabulario
    está declarado en mayúsculas. Nómina resuelve cada celda por nombre normalizado (`_get`), así
    que no lo usa.
    """
    for n, raw in enumerate(reader, start=2):
        if upper:
            yield n, {(k or "").strip().upper(): (v or "").strip() for k, v in raw.items() if k}
        else:
            yield n, raw
