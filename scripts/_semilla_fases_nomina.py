"""
LA FASE DE NÓMINA — la ÚNICA de la semilla que escribe sobre los colaboradores REALES.

Está sola en su archivo por eso, no por líneas: es la excepción a la regla que gobierna todo lo
demás, y una excepción escondida al final de un archivo de cuatro fases es una excepción que
nadie ve.

🔴 QUÉ SIGNIFICA EXACTAMENTE "ESCRIBE SOBRE LOS REALES", porque la diferencia importa: NO los
MUTA. `costos_nomina` es una tabla HIJA; la fila referencia al colaborador y no le cambia una
sola columna del legajo. Borrarla lo devuelve al estado exacto de antes. Es lo contrario de una
recategorización o de una baja, que sí escriben en `empleados` y por eso van sobre gente
sembrada (ver `_semilla_guarda.py`).

🔴 Y ES LO QUE SE PIDIÓ: la masa salarial del dashboard sale de esta tabla, que está en CERO. Con
filas solo sobre nueve colaboradores inventados, el número que muestra la pantalla no sería el de
Karstec y el recorrido no probaría nada.
"""
import random
from datetime import date, timedelta
from typing import List

HOY = date.today()
# Semilla fija: dos corridas producen los MISMOS sueldos. Sin esto, volver a sembrar sobre un
# mes ya cargado (el endpoint es un upsert) cambiaría la masa salarial sin que nadie lo pidiera.
_AZAR = random.Random(20260823)

# Sueldos brutos de referencia por seniority, en pesos de 2026. El neto sale de restar el 17%
# de aportes, que es lo que `_nomina_write_repo` guarda como `cargas_sociales`.
_BRUTO = {"junior": 1_150_000, "semi_senior": 1_680_000, "senior": 2_450_000,
          "lider": 3_200_000, None: 1_500_000}
_APORTES = 0.17
# El mes actual sale ~4% por encima del anterior: sin diferencia, la variación de la masa
# salarial diría 0% y no se podría distinguir de "no hay con qué comparar" (que el backend
# devuelve como `None` desde la tanda del 21/8).
_AJUSTE_MES_ACTUAL = 1.04


def sembrar_nomina(cli, reales: List[dict]) -> int:
    """Nómina de los 31 colaboradores REALES, mes actual y anterior.

    🔴 NO USA `obtener_o_crear` Y SÍ ANOTA CADA FILA, y las dos mitades tienen su motivo. No lo
    usa porque el endpoint YA es idempotente solo: es un upsert sobre `UNIQUE (empleado_id,
    anio, mes)` (`_nomina_write_repo.guardar`), así que reenviar la misma fila la pisa con el
    MISMO id en vez de duplicarla. Anota igual porque **ésta es la única fase que escribe sobre
    colaboradores reales**, y el id devuelto es lo ÚNICO que después distingue una fila sembrada
    de una que cargue RRHH en el mismo período: no hay marca de agua posible en una tabla de
    montos. Sin ese anotado, limpiar sería borrar el período entero.
    """
    print("→ costos de nómina (mes actual y anterior)")
    primero = HOY.replace(day=1)
    anterior = primero - timedelta(days=1)
    periodos = [(anterior.year, anterior.month, 1.0), (primero.year, primero.month, _AJUSTE_MES_ACTUAL)]
    escritas = 0
    for anio, mes, ajuste in periodos:
        for e in reales:
            base = _BRUTO.get(e.get("seniority"), _BRUTO[None])
            bruto = round(base * ajuste * _AZAR.uniform(0.88, 1.14), -3)
            cuerpo = {"empleado_id": e["id"], "anio": anio, "mes": mes,
                      "monto_bruto": bruto, "monto_neto": round(bruto * (1 - _APORTES), -3)}
            try:
                fila = cli.pedir("POST", "/api/costos/nomina", json_body=cuerpo,
                                 empresa=e["empresa_id"])
                cli.manifiesto.anotar("costos_nomina", f"{e['id']}@{anio}-{mes:02d}",
                                      str(fila["id"]))
                escritas += 1
            except Exception as exc:  # noqa: BLE001 — una fila mala no corta el período
                cli.anotar_fallo("costos_nomina", f"{e['id']} {mes}/{anio}", exc)
        print(f"    {mes:02d}/{anio} · {escritas} filas acumuladas")
    return escritas
