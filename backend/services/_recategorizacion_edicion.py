"""La REGLA 3 del módulo de recategorizaciones: los `*_anterior` al EDITAR.

Sale de `_recategorizacion_anteriores.py` —donde viven las reglas del ALTA— porque es una regla
DISTINTA y con nombre propio, y porque juntas ese archivo se pasaba del límite de 150. Las del
alta responden "¿de dónde salen los valores anteriores?"; ésta responde "¿qué pasa cuando la
fila que los tiene ya modificó al colaborador?".

─────────────────────────────────────────────────────────────────────────────────────────────
REGLA 3 — al EDITAR, si no hay previa, los `*_anterior` NO se recalculan: se CONSERVAN
─────────────────────────────────────────────────────────────────────────────────────────────
La REGLA 1 dice que sin previa el estado anterior sale del empleado. En un ALTA eso es cierto.
En una EDICIÓN es **circular y destructivo**: si la fila es la primera de esa persona, ya le
pisó el legajo vía `aplicar_al_empleado`, así que leer al empleado devuelve **los valores nuevos
de la propia fila**.

Medido en producción el 23/8/2026 sobre un legajo limpio: alta `C1 → C3` correcta; un PUT que
cambiaba **sólo el motivo** dejaba `categoria_anterior = C3`. La fila pasaba a decir "de C3 a
C3" — el cambio que existía para registrar desaparecía, y el módulo no tiene DELETE para
corregirlo. Es justo la invariante que el docstring de `schemas/recategorizacion.py` dice
proteger cuando explica por qué los `*_anterior` no se aceptan del cliente.

Lo único que sabe cómo era el mundo antes de esa fila es **la fila misma**. Por eso al editar
sin previa se conservan sus `*_anterior`, que es además la fuente que se usó para reparar a
mano el dato que este bug ensució.

⚠️ Con previa NO aplica: ahí la cadena tiene de dónde leer y recalcular es lo correcto (mover
`fecha_efectiva` cambia cuál es la previa, y ese es el caso que la REGLA 1 cubre).
"""
from typing import Optional

from schemas.empleado import EmpleadoResponse
from schemas.recategorizacion import RecategorizacionResponse


def anteriores_al_editar(previa: Optional[RecategorizacionResponse],
                         prior: RecategorizacionResponse,
                         empleado: EmpleadoResponse) -> dict:
    """Los `*_anterior` de una recategorización que se EDITA. Ver REGLA 3 en el encabezado.

    Args:
        previa: la última recategorización anterior a la fecha, EXCLUYENDO la que se edita.
        prior: la fila tal como estaba ANTES de esta edición.
        empleado: se conserva por simetría con `resolver_anteriores` y para el mensaje de
            error de los callers; esta función NO lo lee (ver el comentario del cuerpo).

    Returns:
        dict con los tres `*_anterior`.
    """
    # 🔴 EL FALLBACK POR CAMPO ES `prior`, NUNCA EL EMPLEADO — y vale también CON previa.
    # La REGLA 1 resuelve cada campo por separado: una previa que sólo cambió el rol deja
    # `seniority_nueva` en NULL y ahí cae al fallback. En el ALTA ese fallback es el empleado y
    # está bien; en una EDICIÓN el empleado ya fue pisado por ESTA fila, así que caer ahí trae
    # de vuelta el valor nuevo disfrazado de anterior. Medido: con una previa sin seniority, la
    # fila quedaba diciendo `semi_senior → semi_senior`. Lo que la fila ya registró como
    # anterior es el único dato que no se contaminó.
    if previa is None:
        return {"rol_anterior": prior.rol_anterior,
                "seniority_anterior": prior.seniority_anterior,
                "categoria_anterior": prior.categoria_anterior}
    return {
        "rol_anterior": (previa.rol_nuevo if previa.rol_nuevo is not None
                         else prior.rol_anterior),
        "seniority_anterior": (previa.seniority_nueva if previa.seniority_nueva is not None
                               else prior.seniority_anterior),
        "categoria_anterior": (previa.categoria_nueva if previa.categoria_nueva is not None
                               else prior.categoria_anterior),
    }
