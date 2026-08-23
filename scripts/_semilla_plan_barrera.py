"""
QUÉ FILAS SON DE LA FASE `barrera`. La mitad de resolución del plan de borrado, para los
recursos que `_semilla_fases_barrera.py` siembra EN LAS DOS EMPRESAS.

🔴 ARCHIVO PROPIO Y NO DOS FUNCIONES MÁS EN `_semilla_plan_borrado.py`, por la misma razón por la
que ese archivo se separó de `limpiar_semilla.py`: son preguntas distintas. Allá la clave natural
es el legajo `SMK-xx` y el dominio del mail —la identidad de una PERSONA—; acá es el prefijo
literal `SMK ·` en el nombre de un catálogo y, para lo que cuelga, el id del padre sembrado.
Mezclarlas dejaba un archivo de 190 líneas donde la parte delicada —"¿esto es real o lo sembré
yo?"— se leía como una lista más.

🔴 EL ORDEN DE LAS FKs NO VIVE ACÁ: vive en `ORDEN` de `_semilla_plan_borrado.py`, entero y en un
solo lugar. Partirlo entre dos archivos haría que nadie pueda leer de una sola pasada por qué
`horas_proyecto` va antes que `proyectos` — que es exactamente lo que un limpiador no puede
equivocar.

⚠️ `periodos_cerrados` ES EL ÚNICO SIN NOMBRE PROPIO. Un período es un rango de fechas y nada
más: no hay dónde poner la marca `SMK ·`. Su clave natural son las fechas literales de
`_semilla_catalogo_barrera.PERIODO` (enero de 2019), elegidas justamente para que ninguna carga real
pueda coincidir. Si algún día RRHH cierra enero de 2019, este limpiador se lo borraría — por eso
el rango está declarado como constante y no escrito a mano acá.
"""
from typing import Dict, List

from _semilla_catalogo_barrera import (
    AREA, ITEM, PERIODO, PLANTILLA_CLAVE, PROYECTO, TEMPLATE, TIPO_AUSENCIA,
)
from integrations.supabase_client import supabase_admin

# (tabla, recurso del manifiesto). El ORDEN de borrado NO está acá: ver el encabezado.
RECURSOS: List[tuple] = [
    ("horas_proyecto", "horas_proyecto_barrera"),
    ("proyecto_asignaciones", "asignaciones_proyecto_barrera"),
    ("inventario_asignaciones", "inventario_asignaciones_barrera"),
    ("cesiones", "cesiones_barrera"),
    ("onboarding_progreso", "onboarding_progreso_barrera"),
    ("onboarding_instancias", "onboarding_instancias_barrera"),
    ("onboarding_tareas", "onboarding_tareas_barrera"),
    ("tipos_ausencia", "tipos_ausencia_barrera"),
    ("inventario_items", "inventario_items_barrera"),
    ("onboarding_templates", "onboarding_templates_barrera"),
    ("proyectos", "proyectos_barrera"),
    ("plantillas_mail", "plantillas_barrera"),
    ("periodos_cerrados", "periodos_barrera"),
    ("areas", "areas_barrera"),
]


def _por(tabla: str, columna: str, valores: list) -> List[str]:
    if not valores:
        return []
    res = supabase_admin.table(tabla).select("id").in_(columna, valores).execute()
    return [r["id"] for r in (res.data or [])]


def plan_barrera(datos: dict, ids_manifiesto, empleados: List[str]) -> Dict[str, List[str]]:
    """`{tabla: [ids]}` de la fase, uniendo manifiesto con clave natural.

    `ids_manifiesto` y `empleados` los pasa `_semilla_plan_borrado`: el primero es su helper (un
    recurso puede tener el centinela `"hecho"`, que no es un id) y el segundo la lista ya
    resuelta de colaboradores sembrados, de la que cuelgan las cesiones. Recibirlos en vez de
    recalcularlos evita que las dos mitades del plan lleguen a conclusiones distintas sobre
    quiénes son los colaboradores de la semilla.
    """
    def anotados(recurso: str) -> set:
        return set(ids_manifiesto(datos, recurso))

    areas = sorted(anotados("areas_barrera") | set(_por("areas", "nombre", [AREA])))
    proyectos = sorted(anotados("proyectos_barrera") | set(_por("proyectos", "nombre", [PROYECTO])))
    items = sorted(anotados("inventario_items_barrera") |
                   set(_por("inventario_items", "nombre", [ITEM])))
    templates = sorted(anotados("onboarding_templates_barrera") |
                       set(_por("onboarding_templates", "nombre", [TEMPLATE])))
    asignaciones = sorted(anotados("asignaciones_proyecto_barrera") |
                          set(_por("proyecto_asignaciones", "proyecto_id", proyectos)))
    return {
        # Cuelgan del proyecto sembrado: se alcanzan por `proyecto_id` con el manifiesto perdido.
        "horas_proyecto": sorted(anotados("horas_proyecto_barrera") |
                                 set(_por("horas_proyecto", "proyecto_id", proyectos))),
        "proyecto_asignaciones": asignaciones,
        "inventario_asignaciones": sorted(anotados("inventario_asignaciones_barrera") |
                                          set(_por("inventario_asignaciones", "item_id", items))),
        # La cesión no tiene nombre: su clave natural es el colaborador sembrado del que cuelga.
        "cesiones": sorted(anotados("cesiones_barrera") |
                           set(_por("cesiones", "empleado_id", empleados))),
        "onboarding_tareas": sorted(anotados("onboarding_tareas_barrera") |
                                    set(_por("onboarding_tareas", "template_id", templates))),
        # La instancia y su progreso cuelgan del COLABORADOR, no del template: un onboarding
        # iniciado con la plantilla sembrada podría haberse hecho sobre alguien real, y al revés.
        # Por eso la clave natural acá es `empleado_id`, igual que en las cesiones.
        "onboarding_instancias": sorted(anotados("onboarding_instancias_barrera") |
                                        set(_por("onboarding_instancias", "empleado_id", empleados))),
        "onboarding_progreso": sorted(_por("onboarding_progreso", "instancia_id",
                                           sorted(anotados("onboarding_instancias_barrera") |
                                                  set(_por("onboarding_instancias", "empleado_id", empleados))))),
        # 🔴 SOLO los propios de una empresa. Los 5 tipos BASE tienen `empresa_id NULL` y son
        # datos del sistema: el filtro por nombre ya los excluye, pero vale escribirlo.
        "tipos_ausencia": sorted(anotados("tipos_ausencia_barrera") |
                                 set(_por("tipos_ausencia", "nombre", [TIPO_AUSENCIA]))),
        "inventario_items": items,
        "onboarding_templates": templates,
        "proyectos": proyectos,
        "plantillas_mail": sorted(anotados("plantillas_barrera") |
                                  set(_por("plantillas_mail", "clave", [PLANTILLA_CLAVE]))),
        # Ver el encabezado: el único sin nombre propio, se reconoce por sus fechas literales.
        "periodos_cerrados": sorted(anotados("periodos_barrera") |
                                    set(_por("periodos_cerrados", "desde", [PERIODO[0]]))),
        "areas": areas,
    }
