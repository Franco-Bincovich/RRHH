"""
KPI "Masa salarial del mes" (§6) — `services/_dashboard_masa_salarial.py`.

Cubre las DOS decisiones de la tanda del 21/8/2026:
  1. **Cuál de las dos masas salariales sobrevivió**: la que suma `costos_nomina.total` (el costo
     laboral) y no `salario_bruto` (el sueldo). Hasta ese día el dashboard mostraba las dos.
  2. **"Sin base de comparación" ≠ "no cambió"**: la variación es `None`, no `0.0`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

🔴 Las filas del padrón tienen **`total` y `salario_bruto` con valores DISTINTOS**, y eso es todo
el test de la decisión 1: con las dos columnas iguales —que es como se ven las filas reales
mientras nadie cargue bonos— sumar una o la otra da el mismo número y el test no puede distinguir
la fórmula que sobrevivió de la que se borró. El fake no inventa la diferencia: la hace visible.

Y no se falsea `generate_costos`: se falsea la BASE debajo de él. Un doble del generador probaría
que el KPI sabe restar dos números que le dictó el test, no de qué columna salen.

El contraste de la decisión 2 es `test_dos_meses_iguales_dicen_cero_de_verdad`: sin él, devolver
`None` SIEMPRE pasaría los dos tests de "no dice 0%".
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

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import services._dashboard_masa_salarial as masa  # noqa: E402
import services.reportes._reporte_costos as costos  # noqa: E402
from tests.test_eventos_agenda import Almacen  # noqa: E402

EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())


def _fila(anio: int, mes: int, bruto: float, total: float, empresa: str = EMPRESA_A) -> dict:
    """Una fila de `costos_nomina`. 🔴 `total` NO es `bruto`: es lo que separa las dos fórmulas.

    En la base `total` es GENERADA (`bruto + cargas + bonos + otros`); acá se escribe a mano
    porque lo que se prueba es cuál de las dos columnas LEE el KPI, no cómo se calcula la suma.
    """
    return {"id": str(uuid4()), "empresa_id": empresa, "anio": anio, "mes": mes,
            "salario_bruto": bruto, "total": total, "empleados": None}


def _db(monkeypatch, filas: list) -> None:
    monkeypatch.setattr(costos, "supabase_admin",
                        Almacen({"costos_nomina": filas, "presupuesto_areas": []}))


class TestQueColumnaEsLaMasaSalarial:
    def test_suma_total_y_no_salario_bruto(self, monkeypatch) -> None:
        """700 de sueldos, 1000 de costo laboral. La masa salarial son los 1000.

        Para que falle: volver a `salario_bruto` (daría 700), que es la card "Costo total nómina"
        que esta tanda borró del dashboard.
        """
        _db(monkeypatch, [_fila(2026, 3, 400, 600), _fila(2026, 3, 300, 400)])
        actual, _, _ = masa.masa_salarial(2026, 3, None)
        assert actual == 1000.0

    def test_filtra_por_la_empresa_del_sidebar(self, monkeypatch) -> None:
        _db(monkeypatch, [_fila(2026, 3, 400, 600), _fila(2026, 3, 300, 400, EMPRESA_B)])
        assert masa.masa_salarial(2026, 3, EMPRESA_A)[0] == 600.0


class TestSinBaseDeComparacionNoDiceCero:
    """🔴 El test (f) de la sesión, el que más importa.

    Con `costos_nomina` vacía —que es el estado de producción hoy— el cálculo viejo devolvía
    `0.0`, el front lo pintaba con signo y la pantalla AFIRMABA "+0% vs mes anterior": una
    afirmación sobre un dato que no existe, y la más creíble de todas.
    """

    def test_sin_mes_anterior_la_variacion_es_None(self, monkeypatch) -> None:
        _db(monkeypatch, [_fila(2026, 3, 400, 600)])          # marzo sí, febrero no
        actual, anterior, variacion = masa.masa_salarial(2026, 3, None)
        assert (actual, anterior) == (600.0, 0.0)
        assert variacion is None, "sin base de comparación no se puede afirmar una variación"

    def test_con_las_dos_tablas_vacias_tampoco_dice_cero(self, monkeypatch) -> None:
        """El caso de producción: no hay NADA cargado. Ni siquiera ahí la pantalla puede decir
        que la masa salarial no cambió."""
        _db(monkeypatch, [])
        assert masa.masa_salarial(2026, 3, None) == (0.0, 0.0, None)

    def test_un_mes_anterior_cargado_en_CERO_tambien_da_None(self, monkeypatch) -> None:
        """Declarado, no accidental: de un cero no se puede calcular variación porcentual, así
        que "cargado en 0" y "sin cargar" tienen la misma respuesta."""
        _db(monkeypatch, [_fila(2026, 3, 400, 600), _fila(2026, 2, 0, 0)])
        assert masa.masa_salarial(2026, 3, None)[2] is None

    def test_dos_meses_iguales_dicen_cero_de_verdad(self, monkeypatch) -> None:
        """EL CONTRASTE. `0.0` sigue siendo una respuesta legítima —y distinta de `None`— cuando
        hay base y la masa efectivamente no se movió. Sin este test, devolver `None` siempre
        pasaría todo lo de arriba."""
        _db(monkeypatch, [_fila(2026, 3, 400, 600), _fila(2026, 2, 400, 600)])
        assert masa.masa_salarial(2026, 3, None)[2] == 0.0

    @pytest.mark.parametrize("total_anterior,esperado", [(500.0, 20.0), (1200.0, -50.0)])
    def test_con_base_calcula_la_variacion_real(self, monkeypatch, total_anterior, esperado) -> None:
        _db(monkeypatch, [_fila(2026, 3, 400, 600), _fila(2026, 2, 400, total_anterior)])
        assert masa.masa_salarial(2026, 3, None)[2] == esperado

    def test_enero_compara_contra_diciembre_del_ano_anterior(self, monkeypatch) -> None:
        """El mes anterior de enero no es el mes 0: es diciembre del año pasado."""
        _db(monkeypatch, [_fila(2026, 1, 400, 600), _fila(2025, 12, 400, 500)])
        assert masa.masa_salarial(2026, 1, None) == (600.0, 500.0, 20.0)
