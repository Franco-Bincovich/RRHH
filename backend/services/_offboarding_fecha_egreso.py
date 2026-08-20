"""
Las dos guardas de FORMA de la fecha de egreso: ni anterior al ingreso, ni futura.

Salió de `_offboarding_efectivizar.py` el 20/8/2026, que estaba en 149/150 y no admitía la
copia del motivo. El corte sigue la frontera que aquel archivo ya declaraba en su encabezado:
sus guardas son de ESTADO —empresa, instancia abierta, el empleado no es baja ni preingreso—
y estas dos son del VALOR de un campo. `_validar_fecha` ya vivía separada del cuerpo "solo por
largo"; esto es el mismo corte un paso más.

⚠️ El ORDEN de los gates sigue siendo load-bearing y NO cambió: esto se llama al final, después
de las cinco guardas de estado. Un rechazo de fecha sobre una instancia de otra empresa
confirmaría que existe, que es el oráculo que el 404 único cierra.
"""
from datetime import date

from utils.errors import AppError


def validar_fecha(fecha_egreso: date, fecha_ingreso: date) -> None:
    """Las dos guardas de fecha. Separadas del cuerpo solo por largo; el orden no importa entre sí.

    🔴 LA DE FECHA FUTURA NO ES UNA VALIDACIÓN DE FORMA — ES EL BUG QUE ESTE MÓDULO ARREGLA.
    Aceptar una fecha que todavía no ocurrió reinstala exactamente el comportamiento viejo: alguien
    cargaría el egreso previsto para dentro de un mes, el empleado quedaría `estado='baja'` hoy, y
    volveríamos a tener gente trabajando que no cuenta en el headcount. La baja se efectiviza
    cuando ocurrió, no cuando se sabe que va a ocurrir; para lo segundo está `fecha_ultimo_dia`,
    que se carga al abrir el trámite y no toca el estado de nadie.
    """
    if fecha_egreso < fecha_ingreso:
        raise AppError(
            "La fecha de egreso no puede ser anterior a la fecha de ingreso",
            "FECHA_EGRESO_INVALIDA", 400,
        )
    if fecha_egreso > date.today():
        raise AppError(
            "La fecha de egreso no puede ser futura: la baja se efectiviza cuando ocurrió",
            "FECHA_EGRESO_FUTURA", 400,
        )
