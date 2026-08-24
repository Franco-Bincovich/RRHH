"""La TABLA del PDF: anchos de columna y celdas que envuelven.

🔴 POR QUÉ EXISTE ESTE ARCHIVO — el bug que cerró.

`build_pdf` armaba la tabla con **strings pelados** y `colWidths` **iguales**
(`17cm / n_columnas`). Un string en una celda de reportlab **no se envuelve**: se dibuja
entero desde el borde de su celda y se mete encima de la siguiente. Con 15 columnas la
columna medía 34pt y "Objetivo padre" mide 52pt, así que cada celda pisaba a su vecina.
Eso es lo que en el archivo se lee como **"Carla ZabaletaSALUD"** y **"semi_seniorsenior"**,
y lo que convertía el encabezado "Seniority nueva" en "Senity nueva": no es un typo del
código, son dos textos superpuestos.

Las dos mitades del arreglo, y las dos hacen falta:
  1. **cada celda es un `Paragraph`** → reportlab la envuelve DENTRO de su columna;
  2. **los anchos son proporcionales al contenido** → una columna de fechas no ocupa lo mismo
     que una de nombres de empresa, y con anchos iguales la de nombres envolvía en 6 renglones
     mientras la de días desperdiciaba la mitad.

Y una tercera que no es del ancho sino de la hoja: con más de 6 columnas el PDF sale
**apaisado**. En A4 vertical, 15 columnas dan 1,1cm por columna: aun envolviendo bien, eso es
una letra por renglón.
"""
from typing import Any, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph, Table, TableStyle

from services.export._formato import celda, etiqueta

FUENTE, TAMANO = "Helvetica", 8
PADDING = 4                  # a cada lado; el ancho útil de una celda es ancho - 2*PADDING
MIN_COL = 1.4 * cm           # abajo de esto no entra ni una palabra corta
UMBRAL_APAISADO = 6          # columnas a partir de las cuales A4 vertical no alcanza


def necesita_apaisado(datos: Dict[str, Any]) -> bool:
    """¿Alguna tabla del documento tiene más columnas de las que entran en A4 vertical?"""
    return any(isinstance(v, list) and v and isinstance(v[0], dict)
               and len(v[0]) > UMBRAL_APAISADO for v in datos.values())


def _anchos(filas: List[List[str]], util: float) -> List[float]:
    """Anchos proporcionales al contenido, con un piso, sumando exactamente `util`.

    El peso de una columna es el ancho del texto MÁS LARGO que tiene que mostrar, acotado a
    un tope: una celda de 300pt (una descripción) no puede llevarse media hoja y dejar a las
    otras catorce en el mínimo.
    """
    n = len(filas[0])
    tope = util / 2
    pesos = [min(tope, max(stringWidth(f[i], FUENTE, TAMANO) for f in filas) + 2 * PADDING)
             for i in range(n)]

    # el piso se reparte primero; lo que sobra se prorratea por peso
    if MIN_COL * n >= util:
        return [util / n] * n
    sobrante = util - MIN_COL * n
    total = sum(pesos) or 1.0
    return [MIN_COL + sobrante * (p / total) for p in pesos]


def tabla_de(val: List[dict], util: float, estilo_celda, estilo_encabezado) -> Tuple[Table, None]:
    """Una lista de dicts → un `Table` de reportlab que NO se pisa y NO dice "None"."""
    claves = list(val[0].keys())
    crudas = [[etiqueta(k) for k in claves]] + [[celda(f.get(k)) for k in claves] for f in val]
    anchos = _anchos(crudas, util)

    cuerpo = [[Paragraph(t, estilo_encabezado) for t in crudas[0]]]
    cuerpo += [[Paragraph(t, estilo_celda) for t in fila] for fila in crudas[1:]]

    tbl = Table(cuerpo, colWidths=anchos, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), PADDING),
        ("BOTTOMPADDING", (0, 0), (-1, -1), PADDING),
        ("LEFTPADDING", (0, 0), (-1, -1), PADDING),
        ("RIGHTPADDING", (0, 0), (-1, -1), PADDING),
    ]))
    return tbl, None
