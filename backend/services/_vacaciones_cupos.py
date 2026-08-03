"""
Núcleo puro — CUÁNTOS DÍAS LE CORRESPONDEN a alguien por cada período.

🔴 LA FIRMA ES LA GARANTÍA CONTRA EL N+1, NO UNA CONVENCIÓN DE ESTILO.
Ninguna función de este módulo recibe un repo, un `empleado_id` ni nada de lo que se pueda
sacar una consulta. Reciben fechas y enteros y devuelven enteros. Eso hace que el N+1 sea
IMPOSIBLE DE ESCRIBIR acá adentro, no solo desaconsejado: no hay con qué consultar.
Es lo que permite que el mismo cálculo lo usen los dos consumidores sin que ninguno degrade:
  · `_vacaciones_saldo.py`  → datos de UN empleado (pantalla de vacaciones).
  · `reportes/_reporte_vacaciones.py` (R11) → datos de N empleados traídos en queries BATCH.
Molde: `services/_dashboard_kpis.py`, que ya comparte cálculo entre KPIs y reportes, y
`services/_vacaciones_utils.derive_estado`, que es puro por la misma razón.

Los parámetros de la política NO están acá: viven en `config/reglas_vacaciones.py` y entran
como argumento. Ver ese archivo para el porqué.
"""
from datetime import date
from typing import Optional

from config.reglas_vacaciones import REGLAS, ReglasVacaciones
from utils.errors import AppError


def fecha_antiguedad(fecha_ingreso: Optional[date], fecha_reconocida: Optional[date]) -> date:
    """La fecha desde la que se cuenta la antigüedad: la MÁS VIEJA de las dos.

    Reconocer antigüedad SUMA, nunca resta — por eso es `min` y no "la reconocida si está".
    En producción (30/7/2026) hay 6 empleados con `fecha_ingreso_reconocida` y en 5 de ellos
    coincide con `fecha_ingreso`; en el sexto es anterior (17/10/2023 contra 1/12/2023), que
    es el único caso donde la diferencia se ve. Si algún día se cargara una reconocida
    POSTERIOR al ingreso —un dato mal cargado—, `min` la ignora sola en vez de quitarle
    antigüedad a alguien.

    ⚠️ `fecha_ingreso_reconocida` puede mudarse a `cesiones` (nota de la migración 066). Ese
    día se cambia de dónde sale el segundo argumento; esta función no se entera.

    Raises:
        AppError: EMPLEADO_SIN_FECHA_INGRESO (422) si no hay fecha de ingreso. La columna es
            NOT NULL en la base, así que esto no debería poder pasar; el chequeo existe para
            que, si pasa, falle acá con un mensaje que se entiende y no cuatro llamadas más
            abajo con un TypeError comparando None contra un date.
    """
    if fecha_ingreso is None:
        raise AppError(
            "El empleado no tiene fecha de ingreso, sin ella no se puede calcular el cupo de vacaciones",
            "EMPLEADO_SIN_FECHA_INGRESO", 422,
        )
    if fecha_reconocida is None:
        return fecha_ingreso
    return min(fecha_ingreso, fecha_reconocida)


def periodo_de(fecha: date) -> int:
    """El período de vacaciones al que pertenece una fecha.

    🚩 ESTA FUNCIÓN ES EL ÚNICO PUNTO A CAMBIAR SI RRHH ACLARA QUE EL PERÍODO VA DE OCTUBRE A
    SEPTIEMBRE. Hoy devuelve el año calendario, que es la lectura que sostiene el modelo:
    `solicitudes_vacaciones.periodo` es un SMALLINT con CHECK 2000–2100 (un año, no un rango),
    y el comentario de la migración 083 —"una licencia tomada en 2026 puede ser del período
    2025"— ya es compatible con año calendario. La otra lectura ("de octubre a octubre" se
    refiere al período y no a la antigüedad) se implementaría acá con
    `fecha.year if fecha.month >= 10 else fecha.year - 1`, y arrastraría además un cambio de
    etiqueta en la UI ("2025/26" en vez de "2025"). Está aislada para que ese cambio sea uno.
    """
    return fecha.year


def anios_antiguedad(desde: date, periodo: int, reglas: ReglasVacaciones = REGLAS) -> int:
    """Años cumplidos al momento en que se mide la antigüedad para el período dado.

    La medición NO es al 31/12 sino al día 1 de `reglas.mes_cierre_antiguedad` del año del
    período — es la parte de "de octubre a octubre" que sí quedó confirmada. Consecuencia
    práctica: quien cumple 5 años en noviembre de 2026 recibe 14 días por el período 2026 y
    recién 21 por el 2027.

    Puede dar negativo para períodos anteriores al ingreso; quien decide qué hacer con eso es
    `cupos_por_periodo`, que directamente no genera esos períodos.
    """
    corte = date(periodo, reglas.mes_cierre_antiguedad, 1)
    anios = corte.year - desde.year
    if (corte.month, corte.day) < (desde.month, desde.day):
        anios -= 1
    return anios


def dias_por_antiguedad(anios: int, reglas: ReglasVacaciones = REGLAS) -> int:
    """Días del tramo que le corresponde a esa cantidad de años cumplidos.

    Recorre la escala de mayor a menor y devuelve el primer tramo que alcanza. Con la escala
    por default: 0–4 años → 14 · 5–14 → 21 · 15+ → 28. Si ningún tramo alcanza (antigüedad
    negativa) devuelve 0, que es lo correcto: no hay cupo antes de existir.
    """
    for minimo, dias in reglas.escala_antiguedad:
        if anios >= minimo:
            return dias
    return 0


def dias_anio_de_ingreso(fecha_ingreso: date, dias_completos: int,
                         reglas: ReglasVacaciones = REGLAS) -> int:
    """Días del PERÍODO DEL AÑO DE INGRESO, que tiene su propia regla.

    No es proporcional día por día: es un CORTE. Quien entró antes del corte se lleva el cupo
    completo del tramo; quien entró en el corte o después se lleva `dias_ingreso_tardio`.

    🚩 El umbral entra como `(mes, día)` desde las reglas y NO está escrito acá como
    `if fecha.month <= 7`. Es a propósito: RRHH todavía no cerró si alguien que ingresa el 15
    de julio son 5 días o 14, y con el par configurable las tres respuestas posibles
    (1/7, 15/7, 1/8) son un cambio de constante en `config/reglas_vacaciones.py`. Con el `if`
    hardcodeado, dos de las tres exigirían reescribir esta función.
    """
    return dias_completos if (fecha_ingreso.month, fecha_ingreso.day) < reglas.corte_ingreso \
        else reglas.dias_ingreso_tardio


def cupos_por_periodo(fecha_ingreso: Optional[date], fecha_reconocida: Optional[date],
                      override: Optional[int], periodos: list[int],
                      reglas: ReglasVacaciones = REGLAS) -> dict[int, int]:
    """Cuántos días le corresponden por CADA uno de los períodos pedidos.

    Args:
        fecha_ingreso: `empleados.fecha_ingreso` (NOT NULL en la base).
        fecha_reconocida: `empleados.fecha_ingreso_reconocida`, o None.
        override: `empleados.dias_vacaciones_asignados`. None (el caso normal desde la
            migración 085) = se aplica la regla por antigüedad. Un entero GANA sobre la regla
            para todos los períodos y no caduca: es una excepción declarada por RRHH sobre esa
            persona, no un dato a recalcular.
        periodos: los años a calcular. Los ANTERIORES AL INGRESO SE OMITEN del resultado en
            vez de devolverse en 0 — un 0 y un "no corresponde" se ven igual en un total pero
            no en una pantalla, y devolver el período diría que existe y está agotado.
        reglas: la política. Ver `config/reglas_vacaciones.py`.

    Returns:
        {período: días}. Solo los períodos que existen para esa persona.
    """
    desde = fecha_antiguedad(fecha_ingreso, fecha_reconocida)
    periodo_ingreso = periodo_de(desde)
    cupos: dict[int, int] = {}
    for p in periodos:
        if p < periodo_ingreso:
            continue
        if override is not None:
            cupos[p] = override
            continue
        completos = dias_por_antiguedad(anios_antiguedad(desde, p, reglas), reglas)
        cupos[p] = dias_anio_de_ingreso(desde, completos, reglas) if p == periodo_ingreso else completos
    return cupos
