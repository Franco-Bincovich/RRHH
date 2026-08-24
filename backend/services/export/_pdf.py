"""Renderer PDF del motor de export (reportlab). Genérico: mapea `datos` por estructura.

escalares → "Resumen"; analisis/contexto_datos → texto; lista de dicts → tabla;
lista de escalares → bullets; dict simple (no '_') → key/value.

La TABLA —anchos de columna, envoltura de celda y hoja apaisada— vive en `_pdf_tabla`:
es donde estaba el bug de las columnas encimadas y tiene su propia explicación.
"""
import io
from typing import Any, Dict

from services.export._formato import celda, etiqueta, titulo_seccion
from services.export._pdf_tabla import necesita_apaisado, tabla_de


def build_pdf(nombre: str, datos: Dict[str, Any]) -> bytes:
    """Genera un PDF a partir de (nombre, datos). datos asume primitivos (sin coerción de tipos)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    )

    buf = io.BytesIO()
    # 🔴 La hoja se elige por el ANCHO de las tablas, no por gusto: ver `_pdf_tabla`.
    hoja = landscape(A4) if necesita_apaisado(datos) else A4
    margen = 1.5 * cm
    doc = SimpleDocTemplate(buf, pagesize=hoja, leftMargin=margen, rightMargin=margen,
                            topMargin=margen, bottomMargin=margen,
                            title=nombre, author="HR Karstec")
    util = hoja[0] - 2 * margen
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("title", parent=styles["Heading1"],
                                 fontSize=16, spaceAfter=4, textColor=colors.HexColor("#1e293b"))
    h2_style = ParagraphStyle("h2", parent=styles["Heading2"],
                              fontSize=11, spaceAfter=3, textColor=colors.HexColor("#334155"))
    body_style = ParagraphStyle("body", parent=styles["Normal"],
                                fontSize=9, leading=14, textColor=colors.HexColor("#475569"))
    label_style = ParagraphStyle("label", parent=styles["Normal"],
                                 fontSize=9, leading=14, textColor=colors.HexColor("#64748b"))
    # Los dos de la tabla: 8pt con interlineado corto, porque una celda envuelta puede
    # ocupar tres renglones y con `leading` de 14 la fila se iría a 42pt de alto.
    celda_style = ParagraphStyle("celda", parent=styles["Normal"], fontName="Helvetica",
                                 fontSize=8, leading=9.5,
                                 textColor=colors.HexColor("#334155"))
    th_style = ParagraphStyle("th", parent=celda_style, fontName="Helvetica-Bold",
                              textColor=colors.white)

    story = [
        Paragraph(nombre, title_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=8),
    ]

    # ── Datos escalares ────────────────────────────────────────────────────────
    scalars = {k: v for k, v in datos.items()
               if not isinstance(v, (list, dict)) and k not in ("titulo",)}
    if scalars:
        story.append(Paragraph("Resumen", h2_style))
        for key, val in scalars.items():
            story.append(Paragraph(f"<b>{etiqueta(key)}:</b>  {celda(val)}", body_style))
        story.append(Spacer(1, 0.4*cm))

    # ── Texto largo (análisis IA) ──────────────────────────────────────────────
    for key in ("analisis", "contexto_datos"):
        if key in datos and isinstance(datos[key], str):
            story.append(Paragraph(etiqueta(key), h2_style))
            for line in datos[key].split("\n"):
                story.append(Paragraph(line or "&nbsp;", body_style))
            story.append(Spacer(1, 0.4*cm))

    # ── Tablas ─────────────────────────────────────────────────────────────────
    for key, val in datos.items():
        if key.startswith("_") or not isinstance(val, list) or not val:
            continue
        # `None` = el encabezado repetiría el título del documento (ver `_formato`)
        seccion = titulo_seccion(key, nombre)
        if seccion:
            story.append(Paragraph(seccion, h2_style))
        if isinstance(val[0], dict):
            tbl, _ = tabla_de(val, util, celda_style, th_style)
            story.append(tbl)
        else:
            for item in val:
                story.append(Paragraph(f"• {celda(item)}", label_style))
        story.append(Spacer(1, 0.4*cm))

    # ── Dicts simples (excluye claves privadas como _sheets) ──────────────────
    for key, val in datos.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        seccion = titulo_seccion(key, nombre)
        if seccion:
            story.append(Paragraph(seccion, h2_style))
        for k, v in val.items():
            story.append(Paragraph(f"<b>{k}:</b>  {celda(v)}", body_style))
        story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    return buf.getvalue()
