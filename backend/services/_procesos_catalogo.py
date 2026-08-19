"""
El CATÁLOGO del Panel de Procesos: qué procesos muestra y qué estados cuenta cada uno.

Extraído de `services/procesos_service.py`, que quedó en 153 contra un tope de 150 al documentar
por qué las listas de estado tienen que ser el CHECK completo. El corte cae donde el archivo
CRECE: `_META` y `_ESTADOS` suman una entrada cada vez que el panel incorpora un proceso, y las
dos se tocan juntas; la clase de al lado es maquinaria estable (`get_procesos`, `_build_proceso`,
`_count`) que no cambia con un proceso nuevo.

Molde del corte: `tests/_columnas_candidatos.py` separándose de su barrido.

🔴 `_ESTADOS` ESTÁ INDEXADO POR NOMBRE DE TABLA, y eso no es un detalle de implementación: es lo
único que hace verificable este catálogo. `tests/test_procesos_estados.py` puede contrastar cada
lista contra el CHECK real de `db/schema.sql` porque la tabla es la CLAVE del dict y no hay que
adivinarla. Un barrido genérico sobre listas de literales de estado no se pudo escribir por
exactamente eso (está medido en `docs/DEUDA-TECNICA.md`). Si alguna vez se aplana esta estructura,
se pierde el test.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from typing import List

# (tabla, proceso_id, label)
#
# 🔴 EVALUACIONES NO ESTÁ ACÁ, Y NO ES UN OLVIDO. Hasta el 2026-08-11 el panel contaba
# `ev_ciclos` y `ev_instancias`; se sacaron con el módulo `ev_*` (bloque J5a). NO se
# reapuntaron al módulo de evaluaciones VIVO (`evaluacion_lotes`) porque un lote importado
# no tiene el eje que este panel muestra: no hay `abierto`/`cerrado` ni `iniciada`/`finalizada`
# que contar — un lote existe o no existe. Meterlo con estados inventados daría un tablero
# que se lee igual que los otros seis y significa otra cosa.
_META: List[tuple[str, str, str]] = [
    ("onboarding_instancias", "onboarding", "Onboarding"),
    ("offboarding_instancias", "offboarding", "Offboarding"),
    ("vacantes", "vacantes", "Vacantes"),
    ("empleado_capacitacion", "capacitaciones", "Formación"),
    ("objetivos", "objetivos", "Objetivos"),
]

# 🔴 CADA LISTA TIENE QUE SER EL CHECK COMPLETO DE SU TABLA, NI DE MÁS NI DE MENOS.
# No es prolijidad: `_build_proceso` calcula `total = sum(conteo de cada estado declarado)`, así
# que **un estado que falta no deja una categoría vacía — falsea el total del proceso**, y un
# estado inventado agrega una fila que dice 0 para siempre. Las dos fallas son mudas: no hay
# error, no hay log, el número simplemente no es el que dice ser.
#
# Estaba mal en TRES de las cinco tablas (medido contra el catálogo el 18/8/2026):
#   · `vacantes`               — declaraba `en_revision`, que NO está en el CHECK, y le faltaban
#                                `en_proceso` y `con_candidatos`. O sea: una fila fija en 0 y el
#                                total sin las dos etapas del medio del pipeline, que son donde
#                                están las búsquedas vivas.
#   · `onboarding_instancias`  — le faltaba `pendiente`.
#   · `offboarding_instancias` — le faltaba `en_proceso`.
# `empleado_capacitacion` y `objetivos` ya estaban completas.
#
# `tests/test_procesos_estados.py` contrasta las cinco listas contra los CHECK reales de
# `db/schema.sql` en las DOS direcciones, así que esto no puede volver a divergir en silencio.
_ESTADOS: dict[str, List[tuple[str, str]]] = {
    "onboarding_instancias": [
        ("pendiente", "Pendiente"),
        ("en_progreso", "En progreso"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ],
    "offboarding_instancias": [
        ("iniciado", "Iniciado"),
        ("en_proceso", "En proceso"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ],
    # Las etiquetas son LAS MISMAS que las de `services/_vacantes_export._ESTADO_LABEL`, para que
    # el panel y el archivo exportado no le pongan dos nombres distintos al mismo estado.
    "vacantes": [
        ("nueva", "Nueva"),
        ("en_proceso", "En proceso"),
        ("con_candidatos", "Con candidatos"),
        ("cerrada", "Cerrada"),
    ],
    "empleado_capacitacion": [
        ("pendiente", "Pendiente"),
        ("en_curso", "En curso"),
        ("completado", "Completado"),
    ],
    "objetivos": [
        ("por_hacer", "Por hacer"),
        ("haciendo", "En curso"),
        ("terminado", "Terminado"),
    ],
}
