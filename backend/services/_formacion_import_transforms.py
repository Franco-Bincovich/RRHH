"""
Vocabulario de columnas del Excel de Formación y las traducciones puras del import.

Molde: `_objetivos_import_transforms.py`. Sin I/O: los VALORES llegan como string desde
`_import_excel`, que ya resolvió `None`, floats (el Año viaja como "2026", no "2026.0") y
fechas. Acá vive el vocabulario y las tres traducciones; el matcheo de personas está en
`_formacion_matcheo.py` (otra clase de cosa: consulta un padrón, esto es puro texto).

Las DECISIONES que este módulo implementa (cerradas el 19/8/2026 — implementar, no rediscutir):
  · ESTADO por diccionario EXPLÍCITO. "Finalizado"→completado, "Sin iniciar"→pendiente, y los
    tres valores canónicos del CHECK entran tal cual. **Cualquier otro valor RECHAZA la fila,
    nunca cae a un default**: la columna tiene DEFAULT 'pendiente', así que un estado nuevo del
    Excel ("En pausa") entraría como pendiente en silencio — y el CHECK de la base
    (pendiente|en_curso|completado) haría fallar el INSERT de los dos valores reales del archivo.
  · FECHAS derivadas de Año + Fecha (el MES en castellano, caja mezclada: "marzo"/"Marzo"):
    primer día del mes. `fecha_asignacion` siempre que se pueda; `fecha_completado` solo si el
    estado quedó completado. Sin mes, la fila ENTRA sin fecha y CON aviso: el reporte de
    formación filtra por `fecha_asignacion` (`_reporte_capacitacion.py`) y el anual por
    `fecha_completado` (`_reporte_anual_metricas.py`) — una fila sin fecha existe pero no
    aparece en ninguno de los dos, y eso el usuario lo tiene que saber al importar.
  · Las filas que traen SOLO el Año (11 de 53 en el archivo real) se rechazan con motivo.
  · "Área / Equipo" y "Puesto" NO se importan: salen del empleado. Copiados como texto, el día
    que alguien cambia de área el registro histórico empieza a mentir (decisión de la mig 116).
"""
import unicodedata
from typing import List, Optional

from services._import_csv import normalizar_header


def _sin_acentos(s: str) -> str:
    """"Título" → "titulo" (tras normalizar_header). Descompone y descarta lo no-ASCII."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


# Nombres tal como están en el archivo real (encabezados CON acento donde lo llevan).
COL_ANIO = "Año"
COL_MES = "Fecha"                       # el archivo la llama "Fecha" pero trae el MES a mano
COL_PROYECTO = "Proyecto"
COL_COLABORADOR = "Colaborador"
COL_TIPO = "Tipo de capacitación"
COL_TITULO = "Título"
COL_ENTIDAD = "Entidad capacitadora"
COL_MODALIDAD = "Modalidad"
COL_DURACION = "Duración (hs)"
COL_ESTADO = "Estado"
# Presentes en el archivo y a propósito IGNORADAS: "Área / Equipo", "Puesto", "Observaciones".

REQUERIDAS: List[str] = [COL_TITULO, COL_COLABORADOR, COL_ESTADO]

# Estado del Excel (normalizado) → estado del CHECK. Ver el encabezado: explícito, sin default.
TRADUCCION_ESTADO = {
    "finalizado": "completado", "sin iniciar": "pendiente",
    "pendiente": "pendiente", "en curso": "en_curso", "en_curso": "en_curso",
    "completado": "completado",
}

def _get(fila: dict, columna: str) -> str:
    """Valor por nombre normalizado; si no matchea exacto reintenta SIN acentos.

    Mismo reintento local que `_objetivos_import_transforms._get` y por el mismo motivo: el
    archivo real escribe "Título"/"Año"/"Duración (hs)" con acento, y `normalizar_header` no
    los saca — sin esto, una copia tipeada sin acentos perdería esas columnas EN SILENCIO.
    """
    normal = normalizar_header(columna)
    if normal in fila:
        return (fila.get(normal) or "").strip()
    buscada = _sin_acentos(normal)
    clave = next((k for k in fila if _sin_acentos(k) == buscada), None)
    return (fila.get(clave) or "").strip() if clave else ""


def faltantes(headers: List[str]) -> List[str]:
    """Las REQUERIDAS que no están, comparando SIN acentos — a diferencia de
    `_import_excel.faltantes`, que compara con `normalizar_header` a secas. Es la falla que
    objetivos dejó declarada (su "Titulo" requerida rebota un export con "Título"): acá las
    requeridas nacen con acento porque el archivo real lo trae, y un chequeo sensible a acentos
    rechazaría el archivo tipeado a mano que dice "Titulo"."""
    presentes = {_sin_acentos(normalizar_header(h)) for h in headers if h}
    return [c for c in REQUERIDAS if _sin_acentos(normalizar_header(c)) not in presentes]


def traducir_estado(crudo: str) -> Optional[str]:
    """Estado del Excel → estado del CHECK, o None si no está en el diccionario (rechazo)."""
    return TRADUCCION_ESTADO.get(" ".join(_sin_acentos(crudo).casefold().split()))


def parsear_fila(fila: dict) -> dict:
    """Fila cruda → campos del import. No valida: eso lo hace `clasificar`.

    Las fechas y la duración se leen en `_formacion_import_valores` (el corte de "valor de una
    celda", igual que en objetivos); el import es local para no armar un ciclo — valores importa
    `_sin_acentos` de acá."""
    from services._formacion_import_valores import duracion_horas
    return {
        "anio": _get(fila, COL_ANIO), "mes": _get(fila, COL_MES),
        "proyecto": _get(fila, COL_PROYECTO) or None,
        "colaborador": _get(fila, COL_COLABORADOR), "titulo": _get(fila, COL_TITULO),
        "tipo": _get(fila, COL_TIPO) or None, "entidad": _get(fila, COL_ENTIDAD) or None,
        "modalidad": _get(fila, COL_MODALIDAD) or None,
        "duracion": duracion_horas(_get(fila, COL_DURACION)),
        "estado_crudo": _get(fila, COL_ESTADO),
    }


def clasificar(f: dict) -> Optional[str]:
    """El motivo de rechazo de una fila parseada, o None si es importable.

    El caso "solo Año" se distingue de "falta el Título" a propósito: son 11 filas del archivo
    real y RRHH tiene que poder reconocerlas como filas vacías arrastradas, no como errores de
    tipeo. El estado fuera del diccionario nombra el valor Y el vocabulario aceptado — un
    rechazo que no dice qué se acepta obliga a adivinar.
    """
    if not f["titulo"] and not f["colaborador"] and not f["estado_crudo"]:
        return "la fila solo trae el Año: sin Título ni Colaborador no hay nada que importar"
    if not f["titulo"]:
        return "falta el Título"
    if not f["colaborador"]:
        return "falta el Colaborador"
    if not f["estado_crudo"]:
        return "falta el Estado (la columna existe pero la celda está vacía)"
    if traducir_estado(f["estado_crudo"]) is None:
        return (f"estado «{f['estado_crudo']}» no reconocido. Valores aceptados: Finalizado, "
                "Sin iniciar, Pendiente, En curso, Completado")
    return None


def identificador(f: dict) -> str:
    """Cómo se nombra la fila en el reporte: colaborador + título, que es lo que se reconoce
    mirando la planilla. Vacíos → un marcador, nunca cadena vacía."""
    partes = [p for p in (f.get("colaborador"), f.get("titulo")) if p]
    return " — ".join(partes) or "(fila vacía)"
