"""
Catálogo declarativo de las alertas del dashboard: QUÉ se alerta y con qué texto. El CÓMO se
consulta vive en _dashboard_alertas.py.

El corte es por lo que crece: agregar una alerta es agregar una tupla acá, sin tocar la lógica
de queries ni el orden. Juntos los dos pasaban de 150 líneas.

🔑 El mensaje dice qué NO se puede hacer y dónde cargarlo, no describe el vacío. "No hay ítems
de inventario" es un dato; "no se le puede asignar equipamiento a nadie, cargalos en
Inventario" es una instrucción. La segunda forma es la única que hace que alguien actúe.
"""
from typing import NamedTuple, Optional, Tuple


class Bloqueo(NamedTuple):
    """Una tabla vacía que deja un módulo sin poder usarse. Verificado por FK: la entidad hija
    no se puede crear sin al menos una fila de la padre."""
    tabla: str
    tipo: str
    nivel: str
    mensaje: str
    href: str


# Los cinco bloqueos duros vigentes, contrastados contra el catálogo vivo el 2/8/2026.
# NO están acá, a propósito:
#   · onboarding_templates — dejó de estar vacía (1 plantilla, 1 onboarding en curso), así que
#     la alerta no tendría nada que decir.
#   · ev_ciclos — vacía, pero el módulo ev_* está apagado y sus tablas se limpian en el cutover
#     a AWS. Empujar a RRHH hacia un módulo que no existe es peor que no avisar nada.
BLOQUEOS: Tuple[Bloqueo, ...] = (
    Bloqueo("costos_nomina", "sin_costos_nomina", "warning",
            "No hay costos de nómina cargados: quedan vacíos la masa salarial, el reporte de "
            "presupuesto vs. real y el historial salarial de cada empleado. Importalos en Costos.",
            "/costos"),
    Bloqueo("inventario_items", "sin_items_inventario", "warning",
            "No hay ítems en el catálogo de inventario: no se le puede asignar equipamiento a "
            "nadie. Cargá los ítems en Inventario.",
            "/inventario"),
    Bloqueo("capacitaciones", "sin_capacitaciones", "warning",
            "No hay capacitaciones en el catálogo: no se puede asignar ninguna a un empleado. "
            "Cargalas en Capacitaciones.",
            "/capacitaciones"),
    Bloqueo("presupuesto_areas", "sin_presupuesto", "warning",
            "No hay presupuestos por área cargados: el reporte de presupuesto vs. real no puede "
            "calcular desvío ni % de ejecución. Cargalos en Costos.",
            "/costos"),
    Bloqueo("vacantes", "sin_vacantes", "info",
            "No hay vacantes abiertas: no se pueden cargar candidatos ni asociarlos a una "
            "búsqueda. Abrí una vacante en Vacantes.",
            "/vacantes"),
)


class CampoVacio(NamedTuple):
    """Una columna de `empleados` cuyo vacío bloquea algo concreto.

    🔴 El conteo es sobre `estado = activo`, y el `href_listado` LLEVA ESE MISMO FILTRO. No es
    un detalle: la primera versión contaba `!= baja` y linkeaba a un listado sin filtro de
    estado, así que el mensaje decía "6" y la pantalla mostraba 7. Una alerta agregada cuyo
    número no coincide con su destino es peor que no tenerla — enseña a desconfiar del panel.
    `estado = activo` además es lo que el resto del dashboard ya entiende por "el padrón"
    (`empleados_activos`, el headcount del ausentismo): la excepción era esta."""
    campo: str
    tipo: str
    nivel: str
    falta: str          # completa "no tiene ..." / "N empleados sin ..."
    consecuencia: str   # qué se rompe mientras siga vacío
    href_listado: Optional[str]   # listado filtrado para la forma agregada; None = sin link


# 🔴 Solo van acá los campos ACCIONABLES. Contra el padrón de hoy (19 no-baja) quedaron fuera:
#   · cargo (19/19 vacío) — deprecado por decisión de producto, se resuelve con roles[0].
#   · domicilio_* (19/19 × 6 columnas) y telefono (19/19) — vinieron vacíos del CSV y nadie va
#     a cargarlos a mano; son ~150 alertas que hundirían a las que sí importan.
#   · seniority (15/19) — cosmético: afecta un KPI de distribución, no bloquea nada.
# Si más adelante hace falta otro, se suma de a uno.
CAMPOS_VACIOS: Tuple[CampoVacio, ...] = (
    CampoVacio("manager_id", "empleados_sin_manager", "warning", "superior asignado",
               "un usuario de mandos medios no ve a nadie hasta que se cargue",
               "/empleados?estado=activo&sin_manager=true"),
    # Sin filtro `sin_email` en el listado, la forma agregada no tiene a dónde linkear. No es
    # un olvido: hoy son 0 de 19, así que ese filtro no se paga hasta que haga falta.
    CampoVacio("email_corporativo", "empleado_sin_email", "warning", "email cargado",
               "no se le puede notificar nada", None),
)
