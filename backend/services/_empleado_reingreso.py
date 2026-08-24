"""La guarda del REINGRESO: el PUT del legajo no puede resucitar a alguien dado de baja.

Molde: `services/_recategorizacion_egreso.py` — una regla de negocio con nombre propio, en su
archivo, porque `_empleados_write.actualizar` no la admitía sin pasarse de línea y porque una
regla escondida adentro de un `actualizar` es una regla que nadie encuentra cuando falla.

## 🔴 LO QUE SE RECHAZA ES EL CAMBIO DE ESTADO, NO LA EDICIÓN

Editar el legajo de alguien que se fue es **legítimo y frecuente**: corregir un DNI mal tipeado,
un CUIL, un domicilio o un mail para emitir un certificado de trabajo son cosas que se hacen
después del egreso. Prohibir el PUT entero dejaría a Capital Humano sin forma de arreglar un
dato de alguien que ya no está, que es peor que el problema que resuelve.

Lo único que no puede pasar por acá es **volver a poner en actividad a alguien dado de baja**.

## POR QUÉ IMPORTA, MEDIDO

`EstadoEditable` excluye `'baja'` a propósito: el PUT dejó de poder dar de baja el 20/8/2026
porque escribía el estado sin `fecha_egreso` ni motivo, salteándose las dos vías que sí los
escriben. **La dirección inversa quedó abierta**, y es simétricamente mala: verificado en
producción el 23/8/2026, un `PUT {"estado": "activo"}` sobre alguien de baja devolvía **200** y
lo dejaba `activo` **conservando `fecha_egreso` y `motivo_baja`**. El legajo quedaba diciendo
las tres cosas a la vez, la persona volvía a aparecer en el listado de activos y en el
headcount, y **no había forma de deshacerlo por la API** — el PUT ya no puede escribir `'baja'`,
así que hubo que arreglarlo por SQL.

## UN REINGRESO DE VERDAD ES UN ACTO PROPIO, NO UN CAMPO

Reincorporar a alguien tiene que limpiar `fecha_egreso` y `motivo_baja`, decidir si el legajo
sigue siendo el mismo o arranca uno nuevo (cambia la antigüedad, y con ella las vacaciones), y
dejar rastro de quién lo hizo. Nada de eso cabe en un campo de un update parcial. Mientras ese
endpoint no exista, esto rechaza y dice qué hacer.
"""
from typing import Optional

from utils.errors import AppError


def ensure_no_revive(estado_actual: Optional[str], estado_pedido: Optional[str]) -> None:
    """Rechaza reactivar por PUT a un colaborador que está dado de baja.

    Args:
        estado_actual: el `estado` que el colaborador tiene HOY en la base.
        estado_pedido: el `estado` que trae el update, o None si el PUT no lo toca.

    Raises:
        AppError: EMPLEADO_DE_BAJA_NO_SE_REACTIVA (409) al intentar cambiarle el estado a
            alguien de baja. **409 y no 422**: el valor es válido y el request está bien
            formado; lo que no se puede es la transición desde el estado en que está. Mismo
            criterio que `OFFBOARDING_ALREADY_ACTIVE`.
    """
    # Un PUT que no manda `estado` no toca nada de esto: la edición del resto del legajo pasa.
    if estado_pedido is None or estado_actual != "baja":
        return
    raise AppError(
        # Para alguien de Capital Humano: dice qué pasó y cuál es el camino, no el campo.
        "El colaborador está dado de baja y su estado no se puede cambiar desde la ficha. "
        "Para reincorporarlo hace falta darlo de alta de nuevo, así el sistema recalcula la "
        "antigüedad y deja registro del reingreso.",
        "EMPLEADO_DE_BAJA_NO_SE_REACTIVA", 409)
