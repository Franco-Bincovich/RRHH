"""El TÍTULO humano de cada reporte del catálogo.

Sale de `reporte_service` porque es una tabla de texto, no lógica: mezclada con el dispatch de
generadores empujaba el service sobre su límite de 150 líneas, y un renglón de copy no tiene
por qué competir por espacio con las reglas del módulo.

⚠️ Es el nombre que se PERSISTE en `reportes_generados.nombre` y el que encabeza el PDF y el
Excel. Cambiar uno acá NO renombra los reportes ya generados: la fila se guarda con el texto
del día en que se generó, a propósito (un histórico que se renombra solo deja de ser histórico).
"""
from typing import Optional


def nombre_de(tipo: str, mes: int, anio: int, periodo_str, prompt: Optional[str] = None) -> str:
    """El título del reporte, o el `tipo` crudo si no está en la tabla (no puede pasar: el
    caller ya validó contra el dispatch de generadores, que tiene las mismas claves)."""
    nombres = {
        "headcount":         f"Headcount — {periodo_str(mes, anio)}",
        "rotacion":          f"Rotación — {periodo_str(mes, anio)}",
        "altas_bajas":       f"Altas y bajas — {periodo_str(mes, anio)}",
        "distribucion":      "Distribución de plantilla",
        "costos":        f"Costos — {periodo_str(mes, anio)}",
        "vacantes":          "Pipeline de Vacantes",
        "onboarding":        "Progreso de Onboarding",
        "adhoc":         f"Análisis IA: {(prompt or '')[:60]}",
        "anual_consolidado": f"Informe Anual {anio}",
        "saldos_vacaciones": f"Saldos de vacaciones — {periodo_str(mes, anio)}",
        "ausentismo":        f"Ausentismo por área — {periodo_str(mes, anio)}",
        "listado_vac_aus":   f"Vacaciones y ausencias — {periodo_str(mes, anio)}",
        "presupuesto":       f"Presupuesto vs real — {periodo_str(mes, anio)}",
        "capacitacion":      f"Formación por área — {periodo_str(mes, anio)}",
        "auditoria":         f"Auditoría — {periodo_str(mes, anio)}",
    }
    return nombres.get(tipo, tipo)
