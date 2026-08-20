"""
Helper del export de asignaciones de capacitación: proyecta a columnas legibles
(sin UUIDs crudos), con fechas dd/mm/aaaa, estado prettificado y certificado Sí/No.
Los headers del Excel son las keys de cada dict (el motor genérico las capitaliza);
por eso las keys YA son el header legible. Molde _ausencias_export.

Lee SOLO atributos ya resueltos por AsignacionRepo._build (joins en batch); no
dispara ninguna query nueva.
"""
from typing import List

from schemas.capacitacion import AsignacionResponse

# Estado crudo → label RRHH. Fallback al crudo (.get(v, v)): un estado nuevo nunca
# desaparece del archivo en silencio.
_ESTADO_LABEL = {"pendiente": "Pendiente", "en_curso": "En curso", "completado": "Completado"}

# 🔴 CÓMO SE DISTINGUE UN NOMBRE VINCULADO DE UNO SUELTO — decisión, no detalle.
# Desde la migración 116 una fila puede no tener empleado: el Excel de formación trae 41 nombres
# escritos a mano contra 31 colaboradores cargados, y lo que no matchea entra igual con
# `nombre_libre`. En el archivo los dos casos caen en la MISMA columna "Colaborador", así que sin
# marca RRHH ve dos nombres idénticos y no sabe cuál está vinculado a alguien del sistema.
# La marca va en una COLUMNA APARTE y no como sufijo dentro de la celda ("Perez Juan (sin
# vincular)"): un sufijo ensucia el dato, rompe el ordenamiento alfabético y no se puede filtrar
# ni pivotear en Excel, que es lo que RRHH hace con estos archivos. Mismo criterio y mismos
# literales que `_evaluaciones_resultados_export.py` ("Empleado asignado": "Sí"/"No"), que
# resuelve exactamente este problema con nombres importados de un CSV.
# ⚠️ La columna "Área" también sale vacía en esas filas —el área sale del empleado— y esta
# columna es lo que explica por qué, en vez de dejarlo como un hueco sin motivo.


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[AsignacionResponse]) -> List[dict]:
    """Proyecta las asignaciones a las columnas legibles del export (sin UUIDs crudos)."""
    return [
        {
            "Empresa": a.empresa_nombre,
            "Colaborador": a.empleado_nombre or a.nombre_libre or "",
            "Colaborador vinculado": "Sí" if a.empleado_id else "No",
            "Área": a.area_nombre,
            "Formación": a.capacitacion_nombre,
            # Los tres del Excel de formación (mig 116). `anio`/`mes` salen como el texto que la
            # base guarda ("2026", "marzo"): formatearlos acá inventaría una normalización que el
            # dato no tiene.
            "Proyecto": a.proyecto,
            "Año": a.anio,
            "Mes": a.mes,
            "Estado": _ESTADO_LABEL.get(a.estado, a.estado),
            "Fecha asignación": _fecha(a.fecha_asignacion),
            "Fecha límite": _fecha(a.fecha_limite),
            "Fecha completado": _fecha(a.fecha_completado),
            "Certificado": "Sí" if a.certificado_url else "No",
        }
        for a in items
    ]
