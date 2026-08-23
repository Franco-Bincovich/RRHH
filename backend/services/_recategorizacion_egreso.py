"""
La guarda del EGRESO: una recategorización no puede ser efectiva después de que la persona se fue.

Molde: `services/_tipos_jerarquia.py` — una regla de negocio con nombre propio, en su archivo,
porque el write path (`_recategorizaciones_write.py`, 127/150) no la admitía sin pasarse y porque
una regla escondida adentro de un `crear` de 15 líneas es una regla que nadie encuentra cuando
falla.

## 🔴 LO QUE SE RECHAZA ES LO IMPOSIBLE, NO LO RETROACTIVO

La tentación es "no se puede recategorizar a alguien de baja", y **está mal**: cargar tarde una
recategorización que SÍ ocurrió mientras la persona trabajaba es un caso legítimo y frecuente —
RRHH carga el histórico después, y a veces después de que la persona se fue. Prohibirlo dejaría
sin registrar un hecho real.

Lo que no puede existir es una recategorización **efectiva DESPUÉS del egreso**: nadie cambia de
puesto en una empresa en la que ya no trabaja. Por eso la comparación es contra
`fecha_efectiva`, no contra `estado`.

## POR QUÉ IMPORTA, MEDIDO

Sin esta guarda el sistema aceptaba (verificado en producción el 23/8/2026, sembrando datos de
prueba) una recategorización efectiva **trece meses después** del egreso, respondía **201** y
además **le reescribía el puesto al legajo de alguien que ya no está**: `aplicar_al_empleado`
solo mira si la fila es la más reciente de esa persona, no si la persona sigue en la empresa. Y
esa fila **cuenta en el KPI "Recategorizaciones del mes"** del dashboard, así que el número que
Capital Humano lee incluye movimientos de gente que no trabaja más.

## `fecha_egreso` NULL PASA, y no es un agujero

Sin egreso no hay nada con qué comparar: la persona está activa, en licencia, suspendida o es un
preingreso. Los cuatro casos son legítimos para recategorizar. La guarda es una comparación de
fechas, no un chequeo de estado — ver arriba.

⚠️ **NO hay CHECK de base que respalde esto**, y no puede haberlo: `fecha_egreso` vive en
`empleados` y el CHECK de una fila de `recategorizaciones` no puede consultar otra tabla. La
alternativa sería un trigger, descartada por el mismo criterio que en `_tipos_jerarquia`: la
migración 058 dropeó los triggers de lógica para no tener reglas de negocio escondidas en la
base. 🚩 Consecuencia asumida: por SQL directo se puede insertar igual.
"""
from datetime import date
from typing import Optional

from utils.errors import AppError


def ensure_efectiva_antes_del_egreso(fecha_efectiva: date,
                                     fecha_egreso: Optional[date]) -> None:
    """Rechaza una recategorización efectiva después del egreso del colaborador.

    Args:
        fecha_efectiva: la fecha desde la que rige la recategorización.
        fecha_egreso: el egreso del colaborador, o None si no se fue. None siempre pasa.

    Raises:
        AppError: RECATEGORIZACION_POSTERIOR_AL_EGRESO (422) si es posterior al egreso.
            **422 y no 400**: el valor está bien formado y el request es válido; lo que no cierra
            es la regla de negocio entre dos datos. Mismo criterio que
            `RECATEGORIZACION_SIN_CAMBIOS`, el otro rechazo de este módulo.
    """
    if fecha_egreso is None or fecha_efectiva <= fecha_egreso:
        return
    raise AppError(
        # El mensaje es para alguien de Capital Humano, no para un dev: dice las dos fechas que
        # no cierran y qué se puede hacer, en vez de nombrar el campo que falló.
        f"La fecha de la recategorización ({fecha_efectiva.strftime('%d/%m/%Y')}) es posterior "
        f"a la baja del colaborador ({fecha_egreso.strftime('%d/%m/%Y')}). Si el cambio ocurrió "
        "mientras trabajaba, corregí la fecha; si no, no corresponde registrarlo.",
        "RECATEGORIZACION_POSTERIOR_AL_EGRESO", 422)


def egreso_de(empleado) -> Optional[date]:
    """`fecha_egreso` del empleado, normalizada a `date`.

    Existe porque el valor llega de dos formas según por dónde entró la fila: `EmpleadoResponse`
    lo tipa `Optional[date]`, pero un doble de test —o una lectura cruda de PostgREST— lo puede
    traer como el string ISO que viaja por la red. Comparar un `str` con un `date` levanta
    `TypeError`, que saldría como 500 desde una guarda cuyo trabajo es producir un 422 legible.
    """
    valor = getattr(empleado, "fecha_egreso", None)
    if valor is None or isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])
