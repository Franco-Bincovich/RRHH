"""
Los dos KPIs del bloque "Operación" de §6 que se calculan en `services/_dashboard_operacion.py`:
**recategorizaciones del mes** y **rotación 12 meses**.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El doble es el `Almacen` de `test_eventos_agenda` —importado, no reescrito— y eso es lo que hace
que estos tests midan algo: compara `gte`/`lte` **como strings ISO igual que PostgREST**, aplica
`eq`, y devuelve `count` solo cuando la query pidió `count="exact"`. Un fake que ignorara los
rangos dejaría en verde una ventana de 12 meses que en realidad trae la tabla entera, que es
justo el número que nadie puede verificar a ojo.

🔴 Las recategorizaciones se prueban **contra el repo REAL**, no contra un doble del repo. Es el
punto: el KPI no tiene query propia —usa `RecategorizacionRepo.find_all`— y un fake del repo que
devolviera un total inventado probaría la aritmética del KPI (que no tiene) en vez de la única
pregunta que importa, que es si el rango de fechas que el KPI arma corta donde tiene que cortar.

Cada criterio lleva su CONTRASTE en el padrón: una baja de hace 13 meses (la ventana), una fila
con `fecha_egreso` cargada pero `estado='licencia'` (la fecha sola no es una baja), una baja con
fecha futura (el techo), una recategorización del mes pasado y otra del que viene.
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

from datetime import date, timedelta  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories._recategorizacion_row as recat_row  # noqa: E402
import repositories.recategorizacion_repo as recat_repo  # noqa: E402
import services._dashboard_operacion as op  # noqa: E402
from tests.test_eventos_agenda import Almacen  # noqa: E402

_HOY = date(2026, 3, 15)
EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())


def _dias(n: int) -> str:
    return str(_HOY + timedelta(days=n))


def _baja(dias: int, empresa: str = EMPRESA_A, estado: str = "baja") -> dict:
    return {"id": str(uuid4()), "empresa_id": empresa, "estado": estado,
            "fecha_egreso": _dias(dias), "fecha_ingreso": "2020-01-01"}


def _activo(empresa: str = EMPRESA_A) -> dict:
    return {"id": str(uuid4()), "empresa_id": empresa, "estado": "activo",
            "fecha_egreso": None, "fecha_ingreso": "2020-01-01"}


# 8 activos + 2 bajas que cuentan → tasa 2 / (8 + 2) = 20,0 %
_PADRON_ROTACION = (
    [_activo() for _ in range(8)]
    + [
        _baja(-30),                        # hace un mes: cuenta
        _baja(-364),                       # hace casi 12 meses: cuenta (el borde de adentro)
        _baja(-400),                       # hace 13 meses: NO cuenta
        _baja(-10, estado="licencia"),     # fecha cargada sin ser baja: NO cuenta
        _baja(5),                          # baja programada a futuro: todavía no ocurrió
    ]
)


@pytest.fixture
def rotacion_db(monkeypatch) -> Almacen:
    a = Almacen({"empleados": [dict(e) for e in _PADRON_ROTACION]})
    monkeypatch.setattr(op, "supabase_admin", a)
    return a


class TestRotacion12Meses:
    def test_cuenta_las_bajas_del_ultimo_ano_y_no_las_de_hace_trece_meses(self, rotacion_db) -> None:
        """El test (b) de la sesión. Las cinco filas de baja del padrón difieren en UN criterio
        cada una, así que cualquier filtro que se caiga cambia el número."""
        bajas, _ = op.rotacion_12m(_HOY, None)
        assert bajas == 2

    def test_la_tasa_se_divide_por_activos_mas_bajas(self, rotacion_db) -> None:
        """Misma forma que el reporte R6: `bajas / (activos + bajas)`. Con 8 activos y 2 bajas
        da 20 %; dividir por los activos solos daría 25 %."""
        _, tasa = op.rotacion_12m(_HOY, None)
        assert tasa == 20.0

    def test_sin_nadie_la_tasa_es_cero_y_no_divide_por_cero(self, monkeypatch) -> None:
        monkeypatch.setattr(op, "supabase_admin", Almacen({"empleados": []}))
        assert op.rotacion_12m(_HOY, None) == (0, 0.0)

    def test_filtra_por_la_empresa_del_sidebar(self, monkeypatch) -> None:
        """Las dos queries llevan el filtro: si lo llevara solo una, la tasa mezclaría las bajas
        de una empresa con los activos de las dos y saldría más chica de lo que es."""
        monkeypatch.setattr(op, "supabase_admin", Almacen({"empleados": [
            _activo(EMPRESA_A), _baja(-30, EMPRESA_A),
            _activo(EMPRESA_B), _activo(EMPRESA_B), _activo(EMPRESA_B),
        ]}))
        assert op.rotacion_12m(_HOY, EMPRESA_A) == (1, 50.0)


# ── Recategorizaciones del mes ────────────────────────────────────────────────────

def _recat(fecha: str, empresa: str = EMPRESA_A) -> dict:
    return {"id": str(uuid4()), "empresa_id": empresa, "empleado_id": str(uuid4()),
            "fecha_efectiva": fecha, "rol_anterior": None, "rol_nuevo": None,
            "seniority_anterior": None, "seniority_nueva": None, "categoria_anterior": None,
            "categoria_nueva": None, "motivo": "Promoción", "impacto_salarial": None,
            "registrado_por": None, "created_at": "2026-03-01T00:00:00+00:00", "updated_at": None}


@pytest.fixture
def recat_db(monkeypatch) -> Almacen:
    a = Almacen({"recategorizaciones": [
        _recat("2026-03-01"),                 # primer día del mes: cuenta
        _recat("2026-03-31"),                 # último día del mes: cuenta
        _recat("2026-02-28"),                 # mes pasado: NO cuenta
        _recat("2026-04-01"),                 # mes que viene: NO cuenta
        _recat("2026-03-10", EMPRESA_B),      # otra empresa: cuenta en consolidado, no en A
    ]})
    # Los DOS módulos del repo: `find_all` consulta desde `recategorizacion_repo` y los nombres
    # los resuelve `_recategorizacion_row._mapa`. Sin el segundo, el mapper llama al cliente real.
    monkeypatch.setattr(recat_repo, "supabase_admin", a)
    monkeypatch.setattr(recat_row, "supabase_admin", a)
    return a


class TestRecategorizacionesDelMes:
    def test_no_cuenta_las_del_mes_pasado_ni_las_del_que_viene(self, recat_db) -> None:
        """El test (c) de la sesión. Los dos bordes del mes están en el padrón (día 1 y día 31)
        junto con sus vecinos de afuera, así que un rango corrido un día ya rojea."""
        assert op.recategorizaciones_mes(2026, 3, None) == 3

    def test_el_total_es_el_del_filtro_y_no_el_de_la_pagina(self, recat_db) -> None:
        """🔴 El KPI pide `page_size=1`. Si leyera `len(items)` diría SIEMPRE 1, y con la tabla
        vacía diría 0 — o sea que parecería andar justo hoy, que es cuando la tabla está en 0."""
        assert op.recategorizaciones_mes(2026, 3, None) > 1

    def test_filtra_por_la_empresa_del_sidebar(self, recat_db) -> None:
        assert op.recategorizaciones_mes(2026, 3, EMPRESA_A) == 2

    def test_un_mes_sin_recategorizaciones_da_cero(self, recat_db) -> None:
        assert op.recategorizaciones_mes(2026, 1, None) == 0
