"""
Las dos reglas duras de la carga pública: la ventana de fechas y el tope de horas por día.

Viven acá y no dentro del service para que se puedan probar como funciones puras —sin repo, sin
red, sin sesión— y para que el service las llame en una línea. Molde: `_periodo_utils.py`, que
hace exactamente esto con el bloqueo por período.

🔴 LAS DOS SON DE CAPA SERVICE, Y NO PUEDEN NO SERLO.
  · La ventana de 30 días compara contra HOY, y un CHECK de Postgres no puede usar `now()` en una
    constraint inmutable.
  · El tope de 12 es una restricción sobre la SUMA DE VARIAS FILAS, y un CHECK solo ve la fila que
    se inserta. La carrera que eso deja abierta está analizada en `migrations/106_horas_idempotencia.sql`:
    el doble tap se cierra con el índice único de idempotencia, y dos cargas DISTINTAS
    simultáneas quedan declaradas como límite conocido, con su motivo y su disparador.
"""
from datetime import date, timedelta

from utils.errors import AppError

# Hasta 30 días hacia atrás, ni un día más viejo ni el futuro.
DIAS_HACIA_ATRAS = 30
# Tope diario, sumando TODAS las cargas de esa persona ese día.
MAX_HORAS_DIA = 12.0


def verificar_ventana(fecha: date, hoy: date) -> None:
    """La fecha tiene que caer en [hoy - 30, hoy]. `hoy` se inyecta para poder testear los bordes.

    Los dos rechazos son SEPARADOS y con mensajes distintos, al revés que el rechazo único de la
    identificación: acá no hay nada que ocultar —el que pregunta ya está autenticado por su
    sesión— y el usuario necesita saber CUÁL de los dos límites tocó para corregirlo. Un mensaje
    genérico lo dejaría probando fechas.

    Raises:
        AppError: FECHA_FUTURA (422) o FECHA_MUY_VIEJA (422).
    """
    if fecha > hoy:
        raise AppError("No se pueden cargar horas de un día que todavía no pasó.",
                       "FECHA_FUTURA", 422)
    if fecha < hoy - timedelta(days=DIAS_HACIA_ATRAS):
        raise AppError(
            f"Solo se pueden cargar los últimos {DIAS_HACIA_ATRAS} días. "
            "Para algo más viejo, hablá con Capital Humano.",
            "FECHA_MUY_VIEJA", 422)


def verificar_tope(horas_nuevas: float, horas_ya_cargadas: float) -> None:
    """El total del día no puede pasar de 12.

    🔴 SUMA LO QUE YA EXISTE. Validar solo `horas_nuevas` contra 12 dejaría cargar 12 + 12 + 12
    en el mismo día en tres envíos, que es exactamente lo que "varias cargas por día permitidas"
    hace posible. El total previo lo trae el caller de la base.

    El mensaje dice el total y cuánto queda: sin eso, alguien con 10 horas cargadas que intenta 4
    no sabe si pedir 2 o si el problema es otro.

    Raises:
        AppError: TOPE_HORAS_DIA (422).
    """
    total = horas_ya_cargadas + horas_nuevas
    if total > MAX_HORAS_DIA:
        disponible = max(0.0, MAX_HORAS_DIA - horas_ya_cargadas)
        raise AppError(
            f"Ese día ya tenés {horas_ya_cargadas:g} horas cargadas y el máximo es "
            f"{MAX_HORAS_DIA:g}. Podés cargar hasta {disponible:g} más.",
            "TOPE_HORAS_DIA", 422)
