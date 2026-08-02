"""
Helpers PUROS del parser de evaluaciones (fase 2): decode por BOM, normalización de
identidad (sin acentos), parseo de notas y de TIPO EVALUACION, validación de cabeceras.
Sin I/O, sin estado, sin dependencias del proyecto. Testeable en aislamiento.
"""
import unicodedata
from typing import List, Optional

from services import _import_csv as _csv
from services import _import_encoding as _enc

# ── Vocabulario de columnas (nombres tal como vienen en los archivos, UPPER) ──

IDENTIDAD: List[str] = [
    "ORGANISMO", "GERENCIA", "SECTOR",
    "APELLIDO SUPERIOR", "NOMBRE SUPERIOR",
    "APELLIDO EVALUADO", "NOMBRE EVALUADO",
]
HEADERS_NOTAS: List[str] = IDENTIDAD + ["NOTA FINAL"]
COMPETENCIAS: List[str] = [
    "AUTOGESTION", "CONOCIMIENTO", "VISION ESTRATEGICA", "MANEJO CONFLICTOS",
    "ADAPTACION", "INICIATIVA", "EMPATIA", "ORGANIZACION", "TRABAJO EQUIPO",
    "CONDUCCION EQUIPOS", "PLANIFICACION", "RELACIONES INTERPERSONALES",
    "PROMEDIO PRODUCTIVIDAD", "RESPONSABILIDAD", "COMUNICACION",
]
HEADERS_DESGLOSE: List[str] = IDENTIDAD + ["TIPO EVALUACION"] + COMPETENCIAS

# Competencias EXCLUSIVAS del set de líder: su presencia define perfil='lider' (verificado
# contra los archivos reales: aparecen solo en las filas de los líderes). El perfil existe
# para no promediar sets de competencias distintos, así que la señal es la competencia, no el tipo.
COMPETENCIAS_LIDER = frozenset({
    "VISION ESTRATEGICA", "ORGANIZACION", "CONDUCCION EQUIPOS", "PLANIFICACION", "COMUNICACION",
})

# ── TIPO EVALUACION: valor del archivo -> valor del CHECK de la migración 078 ──

_TIPOS = {
    "AUTOEVALUACION": "AUTOEVALUACION",
    "AUTOEVALUACION LIDER": "AUTOEVALUACION_LIDER",
    "SUPERIOR INMEDIATO": "SUPERIOR_INMEDIATO",
    "PAR": "PAR",
    "COLABORADOR": "COLABORADOR",
    "LIBRES": "LIBRES",
}
# Un evaluado es 'lider' si aparece bajo alguno de estos tipos (regla de negocio, NO es_lider).
TIPOS_LIDER = frozenset({"AUTOEVALUACION_LIDER", "SUPERIOR_INMEDIATO"})


def decodificar(data: bytes) -> str:
    """Bytes → texto para los archivos de evaluaciones. Delegado a `_import_csv.decodificar`.

    🔴 `permitir_latin1=False` A PROPÓSITO: los dos archivos de evaluaciones vienen en UTF-8 y
    UTF-16, y este flujo prefiere fallar con un mensaje claro antes que adivinar. Es el
    comportamiento que ya tenía —hay un test que lo fija— y NO cambia con la unificación.
    El import de nómina sí permite latin-1, porque sus archivos reales lo son.

    La detección (BOM UTF-16, heurística de UTF-16 sin BOM, utf-8-sig) vive en el módulo
    compartido: era la única duplicación real entre los dos imports.
    """
    return _enc.decodificar(data, permitir_latin1=False)


def _sin_acentos(s: str) -> str:
    """Quita diacríticos vía NFKD (á->a, ñ->n) — el _norm de nómina no lo hace."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalizar_campo(s: Optional[str]) -> str:
    """Un campo de identidad: trim + colapsa espacios + sin acentos + casefold."""
    return _sin_acentos(" ".join((s or "").split())).casefold()


def clave_identidad(apellido: str, nombre: str) -> str:
    """Clave de cruce A↔B (y de matcheo): apellido+nombre normalizados como un solo texto."""
    return normalizar_campo(f"{apellido} {nombre}")


def parse_nota(raw: Optional[str]) -> Optional[float]:
    """'  8.89' -> 8.89 · ' 10,00' -> 10.0 · '' / None -> None (no aplica). Inválido -> ValueError."""
    t = (raw or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError as exc:
        raise ValueError(f"nota inválida '{raw}'") from exc


def normalizar_tipo(raw: Optional[str]) -> str:
    """Mapea TIPO EVALUACION al valor del CHECK 078. Desconocido -> ValueError (no se descarta)."""
    clave = " ".join((raw or "").split()).upper()
    tipo = _TIPOS.get(clave)
    if tipo is None:
        raise ValueError(f"tipo de evaluador desconocido '{raw}'")
    return tipo


def headers_faltantes(fieldnames: Optional[List[str]], requeridas: List[str]) -> str:
    """Columnas requeridas ausentes, como texto. '' = están todas. Delegado a `_import_csv`.

    ⚠️ La comparación pasó de `strip().upper()` a la normalización compartida, que además colapsa
    espacios internos. Es estrictamente MÁS TOLERANTE: acepta `"NOTA  FINAL"` con doble espacio,
    que antes se rechazaba. No puede rechazar una cabecera que hoy pasa."""
    return ", ".join(_csv.faltantes(fieldnames, requeridas))
