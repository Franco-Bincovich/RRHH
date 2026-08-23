"""
QUÉ FILAS SON DE LA SEMILLA: la construcción del plan de borrado. La mitad que hay que auditar.

Separado de `limpiar_semilla.py` —que quedó con el CLI y la ejecución— porque son dos preguntas
distintas y solo una es delicada: **"¿qué se borra?" decide si el limpiador deja basura o toca
algo real; "¿cómo se borra?" es un DELETE por lotes.** Un archivo que mezcle las dos hace que la
primera se lea como plomería.

🔴 CÓMO SE DISTINGUE LO SEMBRADO DE LO REAL — DOS CAPAS, y el plan es la UNIÓN de las dos:
  1. **El manifiesto**: el id exacto de cada fila creada. Es la única capa que sirve para
     `costos_nomina`, porque esas filas cuelgan de colaboradores REALES y una tabla de montos no
     admite marca de agua — nada distingue una fila sembrada de una que cargue RRHH el mismo mes.
  2. **La clave natural**, para cuando el manifiesto se perdió (otra máquina, otro clon): el
     legajo `SMK-xx` y el dominio `@semilla.hrkarstec.site` en los colaboradores, los nombres y
     títulos literales en los catálogos, y el `empleado_id` para todo lo que cuelga de una
     persona sembrada.

Se UNEN y no se elige una: un manifiesto incompleto —una corrida cortada a la mitad— igual
limpia todo, y una clave natural que no encuentre nada no deja filas sin dueño.

⚠️ VERIFICADO EL 23/8/2026 con los datos puestos: el plan listó exactamente lo sembrado en las
trece tablas y CERO filas reales — ni los 31 colaboradores, ni la vacante "Analista contable",
ni el objetivo "búsqueda líder de equipo", ni los 3 candidatos reales.
"""
from typing import List

from _semilla_catalogo import (
    CAPACITACIONES, EVENTOS, NOMBRES_LIBRES, OBJETIVOS, PERFILES, VACANTES,
)
from _semilla_padron import DOMINIO, PERSONAS
from _semilla_plan_barrera import plan_barrera
from integrations.supabase_client import supabase_admin


# `offboarding_instancias.empleado_id` son ON DELETE **RESTRICT**: con una sola fila viva de
# cualquiera de las dos, el DELETE del colaborador falla. `empleado_capacitacion` cuelga de las
# dos puntas (capacitación y colaborador) y por eso encabeza.
#
# 🔴 LAS DOCE TABLAS DE LA FASE `barrera` ESTÁN INTERCALADAS ACÁ Y NO AGRUPADAS AL FINAL, porque
# el orden que manda es el de las FKs y no el de la fase que las sembró: `horas_proyecto` tiene
# que caer antes que `proyectos`, `cesiones` antes que `empleados` y `tipos_ausencia` DESPUÉS de
# `solicitudes_ausencia` (que lo referencia por `tipo_id`). Agruparlas al final rompía tres de
# esas relaciones a la vez. Qué filas son de la semilla en cada una lo resuelve
# `_semilla_plan_barrera.py`; acá vive el orden, entero y de una sola lectura.
ORDEN = [
    ("horas_proyecto", "horas_proyecto_barrera"),
    ("proyecto_asignaciones", "asignaciones_proyecto_barrera"),
    ("inventario_asignaciones", "inventario_asignaciones_barrera"),
    ("cesiones", "cesiones_barrera"),
    ("onboarding_progreso", "onboarding_progreso_barrera"),
    ("onboarding_instancias", "onboarding_instancias_barrera"),
    ("onboarding_tareas", "onboarding_tareas_barrera"),
    ("empleado_capacitacion", "asignaciones_formacion"),
    ("solicitudes_ausencia", "ausencias"),
    ("solicitudes_vacaciones", "vacaciones"),
    ("tipos_ausencia", "tipos_ausencia_barrera"),
    ("capacitaciones", "capacitaciones"),
    ("costos_nomina", "costos_nomina"),
    ("recategorizaciones", "recategorizaciones"),
    ("offboarding_instancias", "offboarding"),
    ("candidatos", "candidatos"),
    ("vacantes", "vacantes"),
    ("objetivos", "objetivos"),
    ("eventos_agenda", "eventos_agenda"),
    ("inventario_items", "inventario_items_barrera"),
    ("onboarding_templates", "onboarding_templates_barrera"),
    ("proyectos", "proyectos_barrera"),
    ("plantillas_mail", "plantillas_barrera"),
    ("periodos_cerrados", "periodos_barrera"),
    ("perfiles_puesto", "perfiles_puesto"),
    ("empleados", "empleados"),
    # `areas` va DESPUÉS de `empleados`: `empleados.area_id` la referencia. El área sembrada no
    # tiene a nadie adentro, pero el orden no se escribe para el caso feliz.
    ("areas", "areas_barrera"),
]


def _ids_manifiesto(datos: dict, recurso: str) -> list:
    """Los ids anotados de un recurso. Los valores centinela ("hecho") no son ids: se filtran."""
    return sorted({v for v in (datos.get(recurso) or {}).values()
                   if isinstance(v, str) and v != "hecho"})


def _empleados_por_clave_natural() -> list:
    """Los colaboradores sembrados, por legajo `SMK-xx` Y por el dominio del mail.

    Los DOS criterios y no uno: el legajo es único por empresa (no globalmente) y el mail es
    único en todo el sistema, así que juntos cubren el caso de un legajo repetido entre las dos
    sociedades. Es la red que salva si el manifiesto se perdió.
    """
    legajos = [p["legajo"] for p in PERSONAS]
    por_legajo = supabase_admin.table("empleados").select("id").in_("legajo", legajos).execute()
    por_mail = (supabase_admin.table("empleados").select("id")
                .ilike("email_corporativo", f"%@{DOMINIO}").execute())
    return sorted({r["id"] for r in (por_legajo.data or []) + (por_mail.data or [])})


def usuarios_sembrados(datos: dict) -> list:
    """Los tres usuarios de prueba: `[{id, username, email, rol, activo}]`, los de baja incluidos.

    🔴 VAN APARTE DEL PLAN Y NO ENTRAN EN `ORDEN`, y no es un olvido: **no se borran, se dan de
    baja, y por la API**. El porqué está en el encabezado de `limpiar_semilla.py`. Acá solo se
    RESUELVE quiénes son; darlos de baja es de `_semilla_baja_usuarios.py`.

    Las dos capas de siempre: el manifiesto (`usuarios`) y la clave natural, que acá es el
    dominio del mail — el mismo que marca a los colaboradores. `activo` viaja para que el plan en
    seco pueda decir cuáles YA están dados de baja y cuáles no, que es la única forma de que una
    segunda corrida del limpiador no parezca que no hizo nada.
    """
    anotados = _ids_manifiesto(datos, "usuarios")
    res = (supabase_admin.table("users")
           .select("id, username, email, rol, activo")
           .ilike("email", f"%@{DOMINIO}").execute())
    por_id = {r["id"]: r for r in (res.data or [])}
    for uid in anotados:                       # el manifiesto puede tener uno que el mail no
        if uid not in por_id:
            fila = (supabase_admin.table("users")
                    .select("id, username, email, rol, activo").eq("id", uid).execute())
            for r in (fila.data or []):
                por_id[r["id"]] = r
    return sorted(por_id.values(), key=lambda r: r.get("username") or "")


def _hijas_de(tabla: str, columna: str, ids: list) -> list:
    if not ids:
        return []
    res = supabase_admin.table(tabla).select("id").in_(columna, ids).execute()
    return [r["id"] for r in (res.data or [])]


def _por_nombre(tabla: str, columna: str, valores: list) -> list:
    res = supabase_admin.table(tabla).select("id").in_(columna, valores).execute()
    return [r["id"] for r in (res.data or [])]


def plan_de_borrado(datos: dict) -> dict:
    """`{tabla: [ids]}`. Une lo anotado con lo que la clave natural encuentra: la unión es lo que
    hace que un manifiesto incompleto (corrida cortada a la mitad) igual limpie todo."""
    empleados = sorted(set(_ids_manifiesto(datos, "empleados")) | set(_empleados_por_clave_natural()))
    caps = sorted(set(_ids_manifiesto(datos, "capacitaciones")) |
                  set(_por_nombre("capacitaciones", "nombre", [c["nombre"] for c in CAPACITACIONES])))
    vacantes = sorted(set(_ids_manifiesto(datos, "vacantes")) |
                      set(_por_nombre("vacantes", "titulo", [v["titulo"] for v in VACANTES])))
    asignaciones = sorted(set(_ids_manifiesto(datos, "asignaciones_formacion")) |
                          set(_hijas_de("empleado_capacitacion", "capacitacion_id", caps)) |
                          set(_hijas_de("empleado_capacitacion", "empleado_id", empleados)) |
                          set(_por_nombre("empleado_capacitacion", "nombre_libre", NOMBRES_LIBRES)))
    return {
        "empleado_capacitacion": asignaciones,
        # Cuelgan del colaborador: la clave natural es su `empleado_id`, así que se alcanzan
        # igual con el manifiesto perdido.
        "solicitudes_ausencia": sorted(set(_ids_manifiesto(datos, "ausencias")) |
                                       set(_hijas_de("solicitudes_ausencia", "empleado_id", empleados))),
        "solicitudes_vacaciones": sorted(set(_ids_manifiesto(datos, "vacaciones")) |
                                         set(_hijas_de("solicitudes_vacaciones", "empleado_id", empleados))),
        "capacitaciones": caps,
        # 🔴 SOLO POR MANIFIESTO. Estas filas cuelgan de colaboradores REALES: no hay clave
        # natural que las separe de una carga de RRHH del mismo mes. Sin manifiesto no se tocan.
        "costos_nomina": _ids_manifiesto(datos, "costos_nomina"),
        "recategorizaciones": sorted(set(_ids_manifiesto(datos, "recategorizaciones")) |
                                     set(_hijas_de("recategorizaciones", "empleado_id", empleados))),
        "offboarding_instancias": sorted(set(_ids_manifiesto(datos, "offboarding")) |
                                         set(_hijas_de("offboarding_instancias", "empleado_id", empleados))),
        "candidatos": sorted(set(_ids_manifiesto(datos, "candidatos")) |
                             set(_hijas_de("candidatos", "vacante_id", vacantes))),
        "vacantes": vacantes,
        "objetivos": sorted(set(_ids_manifiesto(datos, "objetivos")) |
                            set(_por_nombre("objetivos", "titulo", [o["titulo"] for o in OBJETIVOS]))),
        "eventos_agenda": sorted(set(_ids_manifiesto(datos, "eventos_agenda")) |
                                 set(_por_nombre("eventos_agenda", "nombre", [e["nombre"] for e in EVENTOS]))),
        "perfiles_puesto": sorted(set(_ids_manifiesto(datos, "perfiles_puesto")) |
                                  set(_por_nombre("perfiles_puesto", "nombre", [p["nombre"] for p in PERFILES]))),
        "empleados": empleados,
        # Las doce de la fase `barrera`. Se resuelven en su propio archivo (ver el encabezado de
        # `_semilla_plan_barrera.py`) y se le pasan los colaboradores YA resueltos: las cesiones
        # cuelgan de ellos y las dos mitades del plan no pueden diferir sobre quiénes son.
        **plan_barrera(datos, _ids_manifiesto, empleados),
    }
