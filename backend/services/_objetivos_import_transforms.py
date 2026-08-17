"""
Vocabulario de columnas del Excel de objetivos y armado de una fila.

Molde: `_nomina_empleados_transforms.py` — qué columnas espera, cuáles son obligatorias, y cómo
se arma el dict de una fila. Los VALORES ya llegan como string desde `_import_excel` (que
resolvió `None`, floats y fechas), así que acá no hay nada de formato: solo vocabulario.

Los dos vecinos, salidos de acá por límite de líneas:
  · `_objetivos_import_jerarquia.py` — qué columna hace que el archivo entero se rechace, y el
    porqué de que este import NO arme jerarquía.
  · `_objetivos_import_valores.py` — cómo se lee el CONTENIDO de una celda (la fecha, las áreas).
"""
import unicodedata
from typing import List

from schemas.objetivo import TIPO_POR_DEFECTO, TIPOS
from services._import_csv import normalizar_header
from services._objetivos_import_jerarquia import (  # noqa: F401  (re-export: ver abajo)
    COLUMNAS_JERARQUIA, MENSAJE_JERARQUIA, trae_columna_de_jerarquia,
)
from services._objetivos_import_valores import separar_areas

# 🔑 Los tres de arriba se RE-EXPORTAN a propósito. El preview los usa como `tx.MENSAJE_JERARQUIA`
# y los tests como `tx.COLUMNAS_JERARQUIA`: este módulo sigue siendo la puerta única al vocabulario
# de columnas, y quien lea el preview no tiene que saber que la jerarquía vive en otro archivo.


def _sin_acentos(s: str) -> str:
    """"áreas" → "areas". Descompone y descarta lo que no es ASCII. Ver `_get`."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

# Nombres tal como se le muestran a quien tiene la planilla abierta.
COL_TITULO = "Titulo"
COL_RESPONSABLE = "Responsable"
COL_PRIORIDAD = "Prioridad"
COL_FECHA = "Fecha entrega"
COL_DESCRIPCION = "Descripcion"
COL_RESPONSABLES = "Responsables"
# Las tres de la migración 119.
# 🔴 "Areas" SIN ACENTO acá, y el export la escribe CON acento ("Áreas involucradas").
# `normalizar_header` **no saca acentos** —solo recorta, colapsa espacios y hace casefold— así que
# los dos nombres NO son la misma clave. Lo resuelve `_get`, que compara sin acentos: ver su
# docstring. Se declara sin acento porque es lo que una persona tipea más rápido, y el acento
# entra igual.
COL_TIPO = "Tipo"
COL_PERIODICIDAD = "Periodicidad"
COL_AREAS = "Areas involucradas"

REQUERIDAS: List[str] = [COL_TITULO, COL_RESPONSABLE]
OPCIONALES: List[str] = [COL_PRIORIDAD, COL_FECHA, COL_DESCRIPCION, COL_RESPONSABLES,
                         COL_TIPO, COL_PERIODICIDAD, COL_AREAS]

_SEPARADORES = (";", ",")


def _get(fila: dict, columna: str) -> str:
    """Valor de una columna por su nombre normalizado. '' si no está.

    🔴 SI NO MATCHEA EXACTO, REINTENTA SIN ACENTOS. `normalizar_header` recorta, colapsa espacios
    y hace casefold, pero **no toca los acentos**: "Áreas involucradas" y "Areas involucradas" son
    dos claves distintas para él. Y eso importa acá más que en otros imports por una razón
    concreta: **el export de este módulo escribe los encabezados CON acento** ("Áreas
    involucradas", "Descripción"), así que sin este reintento una planilla exportada, editada y
    resubida perdería esas columnas EN SILENCIO — entraría sin áreas y sin descripción, sin un
    solo error.

    El reintento es local a objetivos a propósito: `normalizar_header` lo comparten los tres
    imports del repo y volverlo insensible a acentos es una decisión que los afecta a los tres.
    Acá se resuelve el caso propio sin tocar la primitiva compartida.

    🚩 LO QUE ESTO **NO** ARREGLA, y hay que saberlo: `Titulo` es columna REQUERIDA y su chequeo
    lo hace `_import_excel.faltantes`, que compara con `normalizar_header` a secas. El export
    escribe "Título", así que **resubir un archivo exportado rebota entero** con
    COLUMNAS_FALTANTES antes de llegar a esta función. Es anterior a esta sesión y arreglarlo
    toca el chequeo compartido de columnas requeridas; queda declarado, no escondido.
    """
    normal = normalizar_header(columna)
    if normal in fila:
        return (fila.get(normal) or "").strip()
    buscada = _sin_acentos(normal)
    clave = next((k for k in fila if _sin_acentos(k) == buscada), None)
    return (fila.get(clave) or "").strip() if clave else ""


def parsear_fila(fila: dict) -> dict:
    """Fila cruda → campos del objetivo. No valida: eso lo hace el service contra `users`.

    `prioridad` cae a "media" cuando viene vacía o con un valor que no es del enum: es el mismo
    default que la columna en la base, y rechazar una fila entera por una prioridad mal escrita
    sería desproporcionado — el dato importante es el título y el responsable.

    🔴 `tipo` CAE AL DEFAULT IGUAL QUE `prioridad`, no rechaza la fila. Es la simetría explícita
    con el campo de arriba, y el default es el de PRODUCTO (`operativo`), no el de la columna
    (`anual`): lo que se carga de ahora en adelante nace en la vista permisiva. Los dos defaults
    conviven a propósito — el porqué está en `schemas/objetivo.TIPO_POR_DEFECTO`.
    ⚠️ Un "Anual" con mayúscula entra bien (`.lower()`); un "semestral" cae a operativo **sin
    avisar**, igual que una prioridad mal escrita. Es la política declarada del flujo: el dato
    importante es el título y el responsable.

    🔴 UN ARCHIVO SIN LAS TRES COLUMNAS NUEVAS ENTRA COMPLETO. `_get` devuelve `""` para una
    columna ausente, así que `tipo` cae al default, `periodicidad` queda en `""` (el default de
    la columna, que es NOT NULL) y `areas` en `[]` (que PostgREST escribe como `'{}'`). No hay
    una sola rama especial para eso: sale del mismo camino que una celda vacía.
    """
    prioridad = _get(fila, COL_PRIORIDAD).lower()
    tipo = _get(fila, COL_TIPO).lower()
    return {
        "titulo": _get(fila, COL_TITULO),
        "responsable": _get(fila, COL_RESPONSABLE),
        "prioridad": prioridad if prioridad in ("baja", "media", "alta") else "media",
        "fecha_entrega": _get(fila, COL_FECHA),
        "descripcion": _get(fila, COL_DESCRIPCION) or None,
        "responsables": _separar(_get(fila, COL_RESPONSABLES)),
        "tipo": tipo if tipo in TIPOS else TIPO_POR_DEFECTO,
        "periodicidad": _get(fila, COL_PERIODICIDAD),
        "areas": separar_areas(_get(fila, COL_AREAS)),
    }


def _separar(valor: str) -> List[str]:
    """"ana@x.com; beto@x.com" → ["ana@x.com", "beto@x.com"]. Acepta `;` y `,`.

    Los dos separadores porque el archivo lo escribe una persona: en un Excel en español el `;`
    es el natural, pero el `,` es el que sale de copiar y pegar de cualquier otro lado.

    🔴 LAS ÁREAS **NO** USAN ESTA FUNCIÓN, y la diferencia no es un descuido: acá se puede partir
    por los dos a la vez porque un email o un username **no puede tener una coma adentro**, así
    que ningún valor legítimo se destruye. Un nombre de área sí puede ("Legales, Compliance"), y
    por eso `_objetivos_import_valores.separar_areas` le da prioridad al `;`. Mismo problema, dato
    distinto, dos reglas — escritas en los dos lados para que no se "unifiquen".
    """
    if not valor:
        return []
    for sep in _SEPARADORES:
        valor = valor.replace(sep, "\n")
    return [p.strip() for p in valor.split("\n") if p.strip()]


def identificador(fila: dict) -> str:
    """Cómo se nombra una fila en el reporte de errores: por su título, que es lo que el
    usuario reconoce al mirar la planilla. Vacío → un marcador, nunca una cadena vacía."""
    return _get(fila, COL_TITULO) or "(sin título)"
