"""Renderer CSV del motor de export (stdlib csv). Aplana `datos` por secciones concatenadas.

CSV es una sola tabla plana: no soporta multi-hoja ni estilos. Regla:
título → escalares ("Campo,Valor") → cada lista de dicts como tabla etiquetada →
dicts simples ("clave,valor") → texto largo en celda citada. Si hay `_sheets`,
se apilan verticalmente, cada hoja con su nombre como etiqueta. BOM UTF-8 para Excel.
"""
import csv
import io
from typing import Any, Dict

from services.export._formato import celda, etiqueta, titulo_seccion


def build_csv(nombre: str, datos: Dict[str, Any]) -> bytes:
    """Genera un CSV a partir de (nombre, datos). datos asume primitivos."""
    buf = io.StringIO()
    writer = csv.writer(buf)

    sheets = datos.get("_sheets")
    if isinstance(sheets, dict):
        for sheet_name, sheet_datos in sheets.items():
            writer.writerow([sheet_name])
            _escribir_datos(writer, sheet_datos, sheet_name)
            writer.writerow([])
    else:
        writer.writerow([nombre])
        _escribir_datos(writer, datos, nombre)

    return ("﻿" + buf.getvalue()).encode("utf-8")


def _escribir_datos(writer: Any, datos: Dict[str, Any], nombre: str = "") -> None:
    """Vuelca un dict de datos al writer aplicando la regla de secciones concatenadas."""
    # ── Escalares ────────────────────────────────────────────────────────────
    for key, val in datos.items():
        if not isinstance(val, (list, dict)) and key != "titulo":
            writer.writerow([etiqueta(key), val])

    # ── Texto largo ──────────────────────────────────────────────────────────
    for key in ("analisis", "contexto_datos"):
        if isinstance(datos.get(key), str):
            writer.writerow([])
            writer.writerow([etiqueta(key)])
            writer.writerow([datos[key]])

    # ── Tablas (listas) ──────────────────────────────────────────────────────
    for key, val in datos.items():
        if key.startswith("_") or not isinstance(val, list) or not val:
            continue
        writer.writerow([])
        # `None` = el encabezado repetiría el título del documento (ver `_formato`)
        seccion = titulo_seccion(key, nombre)
        if seccion:
            writer.writerow([seccion])
        if isinstance(val[0], dict):
            headers = list(val[0].keys())
            writer.writerow([etiqueta(h) for h in headers])
            for item in val:
                writer.writerow([celda(item.get(h)) for h in headers])
        else:
            for item in val:
                writer.writerow([item])

    # ── Dicts simples ────────────────────────────────────────────────────────
    for key, val in datos.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        writer.writerow([])
        seccion = titulo_seccion(key, nombre)
        if seccion:
            writer.writerow([seccion])
        for k, v in val.items():
            writer.writerow([k, v])
