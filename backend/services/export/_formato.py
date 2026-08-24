"""Las tres decisiones de PRESENTACIÓN que comparten los cuatro renderers del motor.

Viven acá y no en cada renderer porque los cuatro las tomaban por separado y **divergían**:
el PDF escribía `str(None)` → la celda decía literalmente "None", mientras Excel y CSV dejaban
el hueco vacío. Un mismo listado exportado en dos formatos no puede decir cosas distintas sobre
el mismo dato faltante.

🔴 LAS TRES SALIERON DE ABRIR LOS ARCHIVOS, no de leer el código: son exactamente lo que un
export de objetivos, vacaciones o recategorizaciones mostraba mal (23/8/2026).
"""
from typing import Any, Optional


def etiqueta(clave: str) -> str:
    """`fecha_efectiva` → `Fecha efectiva`. El encabezado que ve quien abre el archivo."""
    return clave.replace("_", " ").capitalize()


def celda(valor: Any) -> str:
    """El valor de una celda, como TEXTO para el archivo.

    🔴 `None` es HUECO, no la palabra "None". Un `str(None)` en una columna opcional
    —`rol_nuevo` cuando la recategorización sólo cambió la categoría— le dice al lector que ahí
    hay un dato que dice "None", y no que no hay dato. Medido: 7 celdas en el export de
    objetivos y 4 en el de recategorizaciones.

    `False` y `0` SÍ se imprimen: son valores, no ausencias. Por eso la comparación es
    `is None` y no un `if not valor`.
    """
    return "" if valor is None else str(valor)


def titulo_seccion(clave: str, nombre_documento: str) -> Optional[str]:
    """El encabezado de una sección, o `None` si repetiría el título del documento.

    Un export de listado trae UNA tabla cuya clave es el nombre del módulo (`objetivos`), y el
    documento ya se llama así: el archivo abría con "Objetivos" y debajo, otra vez, "Objetivos".
    Cuando el documento trae varias secciones (los reportes del catálogo) las claves son
    distintas del título y este helper no descarta ninguna.
    """
    titulo = etiqueta(clave)
    return None if titulo.casefold() == (nombre_documento or "").strip().casefold() else titulo
