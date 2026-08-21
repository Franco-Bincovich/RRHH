"""
`services/_dashboard_headcount.py` — el reparto de activos por ÁREA (viejo) y por EMPRESA (§6,
21/8/2026). Están en el mismo archivo y en el mismo test porque comparten el criterio de qué
cuenta como activo y difieren en una sola cosa, que es justamente lo que hay que poder desmentir:
**el de áreas descarta filas y el de empresas no puede descartar ninguna.**

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El doble es el `Almacen` de `test_eventos_agenda` (aplica `eq`, `neq` e `in_` de verdad), y el
padrón trae las tres filas que un `group by` ingenuo pierde: alguien SIN área, alguien con un
área INACTIVA, y alguien de una empresa que **no está en el catálogo de `empresas`**. Con un
padrón limpio, "sumar todos" y "sumar los que resolvieron nombre" dan lo mismo y el invariante
no prueba nada.

🔴 El invariante se verifica contra `DashboardService._calcular_kpis` REAL, no contra un conteo
que este test rehaga: la pregunta es si las dos superficies de la MISMA pantalla cierran, y un
total recalculado acá probaría que el test sabe sumar.
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

from datetime import date  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import services._dashboard_headcount as hc  # noqa: E402
import services.dashboard_service as ds  # noqa: E402
from tests.test_eventos_agenda import Almacen  # noqa: E402

_HOY = date(2026, 3, 15)
EMPRESA_A, EMPRESA_B, EMPRESA_HUERFANA = str(uuid4()), str(uuid4()), str(uuid4())
AREA_VIVA, AREA_MUERTA = str(uuid4()), str(uuid4())


def _emp(estado: str, empresa: str, area=None) -> dict:
    return {"id": str(uuid4()), "empresa_id": empresa, "estado": estado, "area_id": area,
            "fecha_ingreso": "2024-01-01", "fecha_egreso": None}


# 6 activos: 3 en A, 2 en B, 1 en una empresa que no está en el catálogo.
_PADRON = [
    _emp("activo", EMPRESA_A, AREA_VIVA),
    _emp("activo", EMPRESA_A, AREA_MUERTA),      # área inactiva → NO cae en el reparto por área
    _emp("activo", EMPRESA_A, None),             # sin área      → NO cae en el reparto por área
    _emp("activo", EMPRESA_B, AREA_VIVA),
    _emp("activo", EMPRESA_B, AREA_VIVA),
    _emp("activo", EMPRESA_HUERFANA, AREA_VIVA),  # empresa fuera del catálogo
    _emp("baja", EMPRESA_A, AREA_VIVA),
    _emp("preingreso", EMPRESA_A, AREA_VIVA),
]

_CATALOGO = {
    "empleados": [dict(e) for e in _PADRON],
    "areas": [{"id": AREA_VIVA, "nombre": "Sistemas", "activo": True, "empresa_id": EMPRESA_A},
              {"id": AREA_MUERTA, "nombre": "Vieja", "activo": False, "empresa_id": EMPRESA_A}],
    # 🔴 B está DESACTIVADA y sus dos activos tienen que aparecer igual.
    "empresas": [{"id": EMPRESA_A, "nombre": "KARSTEC", "activa": True},
                 {"id": EMPRESA_B, "nombre": "DOSUBA", "activa": False}],
}


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({k: [dict(f) for f in v] for k, v in _CATALOGO.items()})
    monkeypatch.setattr(hc, "supabase_admin", a)
    monkeypatch.setattr(ds, "supabase_admin", a)
    return a


class TestHeadcountPorEmpresa:
    def test_la_suma_es_el_total_de_activos(self, almacen) -> None:
        """El test (e) de la sesión, contra el KPI real de "Colaboradores activos".

        Para que falle: filtrar `empresas` por `activa` (perdería los 2 de B), descartar la
        empresa huérfana (perdería 1), o contar bajas/preingresos (sumaría 2 de más).
        """
        filas = hc.calcular_headcount_empresa(None)
        activos = ds.DashboardService()._calcular_kpis(_HOY, None).empleados_activos
        assert sum(f.total for f in filas) == activos == 6

    def test_una_empresa_desactivada_con_gente_adentro_aparece(self, almacen) -> None:
        por_nombre = {f.empresa: f.total for f in hc.calcular_headcount_empresa(None)}
        assert por_nombre["DOSUBA"] == 2

    def test_una_empresa_sin_nombre_no_borra_a_su_gente(self, almacen) -> None:
        """Un nombre que no resuelve es un DERIVADO que falta, no una persona menos."""
        por_nombre = {f.empresa: f.total for f in hc.calcular_headcount_empresa(None)}
        assert por_nombre["Sin nombre"] == 1

    def test_ordena_de_mayor_a_menor(self, almacen) -> None:
        totales = [f.total for f in hc.calcular_headcount_empresa(None)]
        assert totales == sorted(totales, reverse=True)

    def test_con_el_sidebar_en_una_empresa_queda_una_fila(self, almacen) -> None:
        filas = hc.calcular_headcount_empresa(EMPRESA_A)
        assert [(str(f.empresa_id), f.total) for f in filas] == [(EMPRESA_A, 3)]

    def test_sin_activos_devuelve_lista_vacia(self, monkeypatch) -> None:
        monkeypatch.setattr(hc, "supabase_admin", Almacen({"empleados": [], "empresas": []}))
        assert hc.calcular_headcount_empresa(None) == []


class TestElRepartoPorAreaSiDescarta:
    def test_el_de_areas_suma_MENOS_que_el_total(self, almacen) -> None:
        """El contraste que hace que el invariante de arriba signifique algo: los dos cortes NO
        son intercambiables. Áreas deja afuera al que no tiene área y al del área inactiva —y
        está bien que lo haga: "el reparto por área" no es "todos"—, así que si alguien "unifica"
        los dos group by, este test rojea antes de que el dashboard muestre dos totales distintos.
        """
        por_area = sum(f.total for f in hc.calcular_headcount(None))
        por_empresa = sum(f.total for f in hc.calcular_headcount_empresa(None))
        assert por_area == 4 < por_empresa == 6
