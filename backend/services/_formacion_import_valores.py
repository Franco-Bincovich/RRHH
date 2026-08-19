"""
Cómo se lee el CONTENIDO de una celda del Excel de Formación: las fechas derivadas y la
duración. Mismo corte que `_objetivos_import_valores.py` respecto de su transforms: el
vocabulario de columnas vive en `_formacion_import_transforms.py` (que quedaba en 159/150 con
esto adentro) y el valor de una celda acá.
"""
from datetime import date
from typing import Optional, Tuple

from services._formacion_import_transforms import _sin_acentos

# "setiembre" es la variante rioplatense; las dos son la misma celda escrita por una persona.
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
         "diciembre": 12}


def derivar_fechas(anio: str, mes: str, estado: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """(fecha_asignacion, fecha_completado, aviso). Primer día del mes, ISO.

    `fecha_completado` solo si el estado quedó `completado`. Si el año no es numérico o el mes
    no está en el diccionario, las fechas quedan en None y el aviso lo dice: la fila ENTRA
    igual (decisión 3) pero invisible para los dos reportes que filtran por fecha
    (`_reporte_capacitacion` por fecha_asignacion, `_reporte_anual_metricas` por
    fecha_completado).
    """
    numero_mes = MESES.get(" ".join(_sin_acentos(mes).casefold().split()))
    if not anio.isdigit() or numero_mes is None:
        que = "mes" if anio.isdigit() else ("año y mes" if not numero_mes else "año")
        return None, None, (f"sin fecha derivable ({que} ilegible o ausente): no va a aparecer "
                            "en el reporte de formación por área ni en el anual")
    fecha = date(int(anio), numero_mes, 1).isoformat()
    return fecha, (fecha if estado == "completado" else None), None


def duracion_horas(crudo: str) -> Optional[float]:
    """"6" / "6.0" / "6,5" → float; vacío o ilegible → None (no rechaza: es dato del catálogo)."""
    t = crudo.replace(",", ".")
    try:
        return float(t) if t else None
    except ValueError:
        return None
