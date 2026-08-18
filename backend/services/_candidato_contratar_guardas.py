"""
LAS GUARDAS del puente candidato → empleado: qué tiene que ser cierto para que la contratación
proceda.

Extraído de `services/_candidato_contratar.py`, que seguía en 160/150 después de sacarle el
mapeo. **El corte mejora el original y no sólo lo acorta**: la sección de abajo justifica una
línea concreta —`if fecha_ingreso < date.today()`— y en el archivo del acto vivía a noventa
líneas de la guarda que explica. Acá quedan pegadas.

📄 **EL ACTO vive en `services/_candidato_contratar.py`**: la orquestación, la doble comprobación
de empresa (candidato contra el header, vacante contra la empresa del candidato) y el límite
conocido de no tener transacción.
📄 **EL MAPEO vive en `services/_candidato_contratar_mapeo.py`**: de dónde sale cada campo del
alta, con las dos trampas (`email_personal` vs `email_corporativo`, y `tipo_contrato`).

🔴 ACÁ ESTÁN CINCO DE LAS SEIS SALIDAS POR ERROR del puente: el 404 de la barrera de empresa y
las cuatro de estado. La sexta (`VACANTE_NOT_FOUND`) se queda en el acto porque no es una guarda
sobre el candidato sino el resultado del lookup que el acto necesita para armar el payload.

═══════════════════════════════════════════════════════════════════════════════════════════

Este endpoint **exige `fecha_ingreso >= hoy`** y `POST /api/empleados/{id}/activar` exige lo
CONTRARIO (que la fecha de ingreso ya haya ocurrido). No es una inconsistencia: es el ciclo.

    contratar  → crea la ficha en `preingreso` con la fecha ACORDADA (todavía no pasó nada)
    activar    → la pasa a `activo` el día que la persona efectivamente entró

Contratar registra un **acuerdo hacia adelante**. Si la persona ya entró, este no es el camino:
el alta normal (`POST /api/empleados`) crea la ficha directamente en `activo`. Un puente que
aceptara fechas pasadas crearía un preingreso que ya debería estar activo, o sea una ficha que
no cuenta en el headcount de alguien que está trabajando — el mismo agujero que
`_empleado_activar` documenta con el signo cambiado.
"""
from datetime import date

from utils.errors import AppError

_ETAPA_CONTRATABLE = "oferta"
_ESTADO_CONTRATABLE = "activo"


def candidato_o_404(candidato):
    """Literal ÚNICO del 404 del puente: "no existe" y "es de otra empresa" son el mismo caso."""
    if not candidato:
        raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
    return candidato


def validar(cand, fecha_ingreso: date) -> None:
    """Las cuatro guardas de estado, en orden. Ninguna escritura ocurre antes de todas ellas.

    El orden importa igual que en `_offboarding_efectivizar`: la barrera de empresa ya corrió
    (la aplicó `_candidato_o_404` sobre el lookup), después el estado (409) y **al final la forma
    de la fecha (400)**. Al revés, un 400 sobre un candidato de otra empresa confirmaría que
    existe — el oráculo de enumeración que el 404 único cierra.
    """
    if not cand.vacante_id:
        raise AppError("El candidato no está asociado a ninguna búsqueda",
                       "CANDIDATO_SIN_VACANTE", 409)
    if cand.etapa_pipeline != _ETAPA_CONTRATABLE:
        raise AppError(
            f"Solo se puede contratar a un candidato en etapa '{_ETAPA_CONTRATABLE}', y este "
            f"está en '{cand.etapa_pipeline}'", "CANDIDATO_NO_ESTA_EN_OFERTA", 409)
    if cand.estado != _ESTADO_CONTRATABLE:
        raise AppError(
            f"El candidato ya no está disponible: su postulación está en '{cand.estado}'",
            "CANDIDATO_NO_CONTRATABLE", 409)
    if fecha_ingreso < date.today():
        raise AppError(
            "La fecha de ingreso no puede ser anterior a hoy. Contratar registra un acuerdo "
            "hacia adelante; si la persona ya entró, el camino es el alta de empleado.",
            "FECHA_INGRESO_PASADA", 400)
