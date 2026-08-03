"""
La aritmética del cupo y del saldo de vacaciones, contra fechas FIJAS.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
No hay fake que valga: el núcleo (`_vacaciones_cupos` / `_vacaciones_fifo`) es puro, así que
acá se le pasan datos y se compara el número que devuelve. No hay ninguna capa intermedia que
pueda "aceptar el parámetro e ignorarlo", que es el modo de falla que arruinó los fakes de
este repo cinco veces. Cada test rompe si se toca la regla que nombra, y varios rompen además
si se toca la de al lado — los bordes están puestos justamente ahí.

Fechas fijas y NUNCA `date.today()`: un test de vencimiento anclado a hoy empieza a probar
otra cosa cada 1° de enero, y uno de antigüedad cambia de tramo solo con que pase el tiempo.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from dataclasses import replace
from datetime import date

import pytest

from config.reglas_vacaciones import REGLAS
from services._vacaciones_cupos import (
    cupos_por_periodo, dias_por_antiguedad, fecha_antiguedad,
)
from services._vacaciones_fifo import Consumo, esta_vencido, saldo
from utils.errors import AppError


def _cupo(ingreso: date, periodo: int, reconocida=None, override=None) -> int:
    return cupos_por_periodo(ingreso, reconocida, override, [periodo]).get(periodo, 0)


# ── Los tres tramos, y sus bordes exactos ────────────────────────────────────────

@pytest.mark.parametrize("anios,dias", [
    (0, 14), (3, 14), (4, 14),      # 4 es el último año del primer tramo
    (5, 21), (7, 21), (14, 21),     # 5 abre el segundo, 14 lo cierra
    (15, 28), (20, 28), (40, 28),   # 15 abre el tercero
])
def test_los_tres_tramos_y_sus_bordes(anios, dias):
    """3→14 · 7→21 · 20→28, y los bordes 4/5 y 14/15, que es donde un `>` en vez de un `>=`
    pasa desapercibido: con solo 3, 7 y 20 el error de un año no se vería."""
    assert dias_por_antiguedad(anios) == dias


def test_la_antiguedad_se_mide_en_octubre_no_en_diciembre():
    """El tramo del período P se decide al 1/10 de P. Quien cumple 5 años DESPUÉS de octubre
    cobra 21 recién en el período siguiente. Para que falle: medir al 31/12 o al 1/1."""
    nov = date(2020, 11, 20)                    # cumple 5 años el 20/11/2025
    assert _cupo(nov, 2025) == 14, "al 1/10/2025 todavía tenía 4 años"
    assert _cupo(nov, 2026) == 21
    sep = date(2020, 9, 20)                     # cumple 5 años el 20/9/2025
    assert _cupo(sep, 2025) == 21, "al 1/10/2025 ya tenía 5"


# ── El corte de julio del año de ingreso ─────────────────────────────────────────

@pytest.mark.parametrize("ingreso,esperado", [
    (date(2024, 1, 10), 14), (date(2024, 6, 30), 14),   # antes del corte → completo
    (date(2024, 7, 1), 5), (date(2024, 12, 31), 5),     # desde el corte → tardío
])
def test_corte_del_anio_de_ingreso(ingreso, esperado):
    """El 30/6 y el 1/7 son el borde exacto con la constante por default `(7, 1)`."""
    assert _cupo(ingreso, 2024) == esperado


def test_el_corte_solo_afecta_al_anio_de_ingreso():
    """Quien entró en julio se lleva 5 ese año, pero el completo desde el siguiente. Para que
    falle: aplicar el corte a todos los períodos en vez de solo al de ingreso."""
    assert _cupo(date(2024, 8, 1), 2024) == 5
    assert _cupo(date(2024, 8, 1), 2025) == 14


def test_el_corte_de_julio_es_configurable_y_no_un_if():
    """🚩 RRHH todavía no cerró si el 15/7 son 5 días o 14. Este test prueba que las tres
    respuestas posibles son un cambio de CONSTANTE: mover `corte_ingreso` mueve el borde sin
    tocar una línea de código. Para que falle: volver a escribir `if fecha.month <= 7`."""
    quince = date(2024, 7, 15)
    assert cupos_por_periodo(quince, None, None, [2024], REGLAS)[2024] == 5
    medio_mes = replace(REGLAS, corte_ingreso=(7, 16))
    assert cupos_por_periodo(quince, None, None, [2024], medio_mes)[2024] == 14
    agosto = replace(REGLAS, corte_ingreso=(8, 1))
    assert cupos_por_periodo(quince, None, None, [2024], agosto)[2024] == 14


# ── Antigüedad reconocida y override ─────────────────────────────────────────────

def test_la_antiguedad_reconocida_suma_pero_nunca_resta():
    """min(ingreso, reconocida). El caso real de producción es el primero (17/10/2023 contra
    1/12/2023). El segundo cubre un dato mal cargado: una reconocida POSTERIOR no puede
    quitarle antigüedad a nadie. Para que falle: usar `reconocida or ingreso`."""
    assert fecha_antiguedad(date(2023, 12, 1), date(2023, 10, 17)) == date(2023, 10, 17)
    assert fecha_antiguedad(date(2020, 1, 1), date(2024, 1, 1)) == date(2020, 1, 1)
    assert fecha_antiguedad(date(2020, 1, 1), None) == date(2020, 1, 1)


def test_sin_fecha_de_ingreso_es_un_error_explicito():
    """La columna es NOT NULL, así que esto no debería pasar. Si pasa, tiene que fallar acá y
    no cuatro llamadas más abajo con un TypeError comparando None contra un date."""
    with pytest.raises(AppError) as exc:
        fecha_antiguedad(None, None)
    assert exc.value.code == "EMPLEADO_SIN_FECHA_INGRESO" and exc.value.status_code == 422


def test_override_gana_sobre_la_regla_y_null_la_deja_actuar():
    """La regla de la migración 085. Para que falle: leer el override como "si es None usá 0"
    (que es lo que hacía la rama "Sin asignar" del reporte viejo) o ignorarlo cuando existe."""
    ingreso = date(2010, 1, 1)                       # 15+ años → la regla daría 28
    assert _cupo(ingreso, 2025, override=None) == 28
    assert _cupo(ingreso, 2025, override=7) == 7     # el override gana aunque sea MENOR
    assert _cupo(ingreso, 2025, override=40) == 40


# ── Acumulación y vencimiento ────────────────────────────────────────────────────

def test_acumulacion_tres_anios_sin_tomar_suman():
    """Para que falle: que el saldo devuelva solo el período corriente."""
    cupos = cupos_por_periodo(date(2015, 1, 10), None, None, [2023, 2024, 2025])
    assert cupos == {2023: 21, 2024: 21, 2025: 21}
    assert saldo(cupos, [], date(2026, 1, 1)).disponibles == 63


def test_vencimiento_el_31_12_de_P_mas_4_todavia_cuenta_y_el_1_1_no():
    """🔴 EL BORDE EXACTO. Para que falle: un `>=` en vez de un `>` en `esta_vencido`, o
    vencer a fin de P+3 o de P+5. El período 2021 vence el 31/12/2025."""
    cupos = {2021: 21}
    assert saldo(cupos, [], date(2025, 12, 31)).disponibles == 21
    ya = saldo(cupos, [], date(2026, 1, 1))
    assert ya.disponibles == 0 and ya.vencidos == 21
    assert not esta_vencido(2021, date(2025, 12, 31))
    assert esta_vencido(2021, date(2026, 1, 1))


def test_lo_vencido_sale_de_asignados_pero_lo_gozado_no_se_borra():
    """Un período vencido deja de aportar cupo disponible, pero los días que SÍ se gozaron
    siguen contados: la historia no se reescribe al vencer."""
    s = saldo({2021: 21, 2025: 14}, [Consumo(dias=6, periodo=2021, tomado=True)], date(2026, 6, 1))
    assert s.gozados == 6
    assert s.asignados == 14 and s.disponibles == 14
    assert s.vencidos == 15, "los 15 que sobraron de 2021 se perdieron, no los 21 enteros"


# ── FIFO e imputación ────────────────────────────────────────────────────────────

def test_una_licencia_con_periodo_declarado_descuenta_de_ESE_periodo():
    """🔴 Es la razón de ser de la columna `periodo` (migración 083): una licencia tomada en
    2026 puede ser del período 2025. Para que falle: imputar todo al más viejo, o al año de
    `fecha_desde`."""
    s = saldo({2023: 21, 2024: 21}, [Consumo(dias=5, periodo=2024, tomado=True)], date(2025, 6, 1))
    por_p = {f.periodo: f.disponibles for f in s.por_periodo}
    assert por_p == {2023: 21, 2024: 16}, "los 5 días salen de 2024, NO del 2023 más viejo"


def test_un_consumo_sin_periodo_va_al_mas_viejo_disponible():
    """🚩 POLÍTICA ABIERTA CON RRHH, elegida y aislada en `imputar_consumo_sin_periodo`.
    Hoy: FIFO desde el más viejo no vencido con saldo. Es la misma regla que el vencimiento
    ("de atrás para adelante") y la conservadora (gasta primero lo que está por vencer).
    Para que falle: cambiar esa función — que es exactamente el punto de tenerla aparte."""
    s = saldo({2023: 21, 2024: 21}, [Consumo(dias=5, periodo=None, tomado=True)], date(2025, 6, 1))
    por_p = {f.periodo: f.disponibles for f in s.por_periodo}
    assert por_p == {2023: 16, 2024: 21}


def test_los_declarados_se_aplican_antes_que_los_sin_periodo():
    """Si el sin-período se imputara primero, agotaría 2023 y el declarado de 2023 lo dejaría
    en negativo teniendo 2024 libre. El orden importa y no es incidental."""
    consumos = [Consumo(dias=21, periodo=2023, tomado=True), Consumo(dias=5, periodo=None, tomado=True)]
    por_p = {f.periodo: f.disponibles for f in saldo({2023: 21, 2024: 21}, consumos, date(2025, 6, 1)).por_periodo}
    assert por_p == {2023: 0, 2024: 16}


def test_un_periodo_excedido_se_muestra_en_negativo_no_se_esconde():
    """Mismo criterio que el flag `excedido` del reporte: un descuadre se ve."""
    s = saldo({2024: 14}, [Consumo(dias=20, periodo=2024, tomado=True)], date(2025, 6, 1))
    assert s.por_periodo[0].disponibles == -6 and s.disponibles == -6


def test_gozados_y_pedidos_descuentan_los_dos():
    """Un pedido a futuro reserva días: no puede volver a pedirlos. Para que falle: contar
    solo lo tomado."""
    s = saldo({2025: 21}, [Consumo(dias=4, periodo=2025, tomado=True),
                           Consumo(dias=3, periodo=2025, tomado=False)], date(2025, 6, 1))
    assert (s.gozados, s.pedidos, s.disponibles) == (4, 3, 14)


def test_un_pendiente_sin_liquidar_no_inventa_un_periodo():
    """Un pendiente con `dias_liquidados = 0` no consume nada, y por eso `consumos_de` lo
    OMITE en vez de mandar un Consumo en cero.

    La diferencia no se ve en los totales —sumar 0 no cambia ninguna suma—, y por eso el
    mutation check descubrió que sacar esa guarda dejaba la suite en verde. Sí se ve en la
    FORMA del resultado: un Consumo de 0 días contra un período fuera de la ventana le crea a
    ese período una fila con cupo 0, o sea un período fantasma en la pantalla del empleado.
    Para que falle: devolver el pendiente sin liquidar como Consumo(dias=0)."""
    from services._vacaciones_saldo import consumos_de

    class _PenSinLiquidar:
        periodo, dias, dias_liquidados = 2019, 10, 0

    assert consumos_de([], [_PenSinLiquidar()], date(2025, 1, 1)) == []
    # Y el efecto que se evita, comprobado sobre el núcleo: un Consumo de 0 contra un período
    # sin cupo agrega la fila igual.
    fantasma = saldo({2025: 21}, [Consumo(dias=0, periodo=2019, tomado=True)], date(2025, 6, 1))
    assert [f.periodo for f in fantasma.por_periodo] == [2019, 2025]
    limpio = saldo({2025: 21}, [], date(2025, 6, 1))
    assert [f.periodo for f in limpio.por_periodo] == [2025]


def test_no_hay_cupo_por_periodos_anteriores_al_ingreso():
    """Se OMITEN en vez de devolverse en 0: un 0 dice "existe y está agotado"."""
    assert cupos_por_periodo(date(2024, 1, 1), None, None, [2022, 2023, 2024]) == {2024: 14}


# ── La ventana de períodos ───────────────────────────────────────────────────────
# Estos tres los agregó el MUTATION CHECK del rearmado: `periodos_a_calcular` es la única
# función que hubo que reconstruir (su cuerpo nunca llegó a disco) y era la única sin una sola
# aserción encima. Romperle la parte que estira la ventana dejaba los 1632 tests en verde.


def test_la_ventana_llega_hasta_el_borde_de_la_acumulacion():
    """Sin consumos, la ventana son los `anios_acumulacion` + el período en curso: los que
    todavía no vencieron. Para que falle: generar uno de más o uno de menos en cualquier punta."""
    from services._vacaciones_saldo import periodos_a_calcular
    assert periodos_a_calcular(date(2010, 1, 1), date(2026, 6, 1), []) == [2022, 2023, 2024, 2025, 2026]


def test_un_consumo_declarado_MAS_VIEJO_QUE_LA_VENTANA_la_estira():
    """🔴 ES LA RAZÓN POR LA QUE `consumos` ES UN PARÁMETRO DE ESA FUNCIÓN.

    Una licencia imputada a un período ya vencido tiene que poder verse en el desglose: si el
    período no se genera, `saldo()` lo agrega igual con cupo 0 (por el `setdefault`) y la fila
    sale con disponible NEGATIVO — o sea, un descuadre inventado por la ventana, no por el dato.

    Para que falle: sacar `declarados` del cálculo de `desde`, que es exactamente la mutación
    que sobrevivió a la suite entera."""
    from services._vacaciones_saldo import periodos_a_calcular
    viejo = [Consumo(dias=5, periodo=2018, tomado=True)]
    assert periodos_a_calcular(date(2010, 1, 1), date(2026, 6, 1), viejo)[0] == 2018
    assert 2022 in periodos_a_calcular(date(2010, 1, 1), date(2026, 6, 1), viejo), \
        "estirar hacia atrás no puede perder los períodos vigentes"


def test_la_ventana_nunca_arranca_antes_del_ingreso():
    """Ni por consumos viejos: un consumo imputado a un período anterior al ingreso es un dato
    malo, y generarle cupo lo convertiría en un derecho. Para que falle: sacar el `max(...)`."""
    from services._vacaciones_saldo import periodos_a_calcular
    consumos = [Consumo(dias=5, periodo=2015, tomado=True)]
    assert periodos_a_calcular(date(2024, 3, 1), date(2026, 6, 1), consumos)[0] == 2024


# ── El contrato de salida contra la migración 090 ────────────────────────────────


def test_la_lectura_de_empleado_ACEPTA_el_null_de_dias_vacaciones():
    """🔴 ES EL TEST DEL ORDEN DE DEPLOY, y lo agregó el mutation check: devolver
    `dias_vacaciones_asignados` a `int = 14` en `schemas/empleado_out.py` no rompía NADA en los
    1632 tests, y sin embargo es el cambio que decide si la migración 090 se puede correr.

    Después de la 090 la columna es nullable y NULL es el caso NORMAL. Si el schema de salida
    no lo admite, el ValidationError se convierte en 500 y NO solo en vacaciones: este modelo
    es la salida de TODA lectura de empleado (listado, ficha, export, dashboard). Por eso el
    código va ANTES que la migración, y por eso esto se prueba acá y no en la pantalla.

    Para que falle: volver a `int = 14`, o a cualquier tipo que no acepte None."""
    from schemas.empleado_out import EmpleadoResponse

    emp = EmpleadoResponse.model_validate({
        "id": "e1", "nombre": "Ana", "apellido": "G", "area_id": "a1", "empresa_id": "c1",
        "roles": ["Dev"], "modalidad_trabajo": "remoto", "tipo_contrato": "indeterminado",
        "fecha_ingreso": "2020-01-15", "estado": "activo",
        "created_at": "2024-01-01T00:00:00Z", "dias_vacaciones_asignados": None,
    })
    assert emp.dias_vacaciones_asignados is None, "el NULL no puede completarse con un default"
