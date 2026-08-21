"""
KPI "Antigüedad promedio" (§6) — `services/_dashboard_antiguedad.py`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El doble es el `Almacen` de `test_eventos_agenda`, importado y no reescrito: aplica `eq` de
verdad, así que el filtro de estado y el de empresa se ejercitan (un fake que devolviera el
padrón entero dejaría en verde un KPI que promedia a los que se fueron).

Y el padrón está elegido para que **promedio y mediana den números DISTINTOS** (4,3 vs 2,0). Con
un padrón simétrico los dos coinciden y devolver el promedio dos veces —o llamar dos veces a la
misma función— pasaría el test sin que nadie calcule una mediana. Es la única forma de que el
"decidimos mostrar las dos" quede probado y no solo declarado.

Cada exclusión lleva su fila en el padrón: una baja MUY vieja (si el filtro de estado se cae, el
promedio se dispara a 10 años), un preingreso con fecha futura (restaría), y una empresa B con
gente de otra antigüedad (si el `eq` de empresa se cae, el consolidado se filtra en el corte).
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

import services._dashboard_antiguedad as ant  # noqa: E402
from tests.test_eventos_agenda import Almacen  # noqa: E402

_HOY = date(2026, 3, 15)
EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())


def _emp(estado: str, dias_de_antiguedad: int, empresa: str = EMPRESA_A) -> dict:
    """Un empleado que ingresó hace `dias_de_antiguedad` días (negativo = ingreso futuro)."""
    return {"id": str(uuid4()), "empresa_id": empresa, "estado": estado,
            "fecha_ingreso": str(_HOY - timedelta(days=dias_de_antiguedad))}


# 365 · 730 · 3650 → promedio 1581,67 días = 4,3 años · mediana 730 días = 2,0 años.
_PADRON = [
    _emp("activo", 365),
    _emp("activo", 730),
    _emp("activo", 3650),                      # el que separa el promedio de la mediana
    _emp("baja", 10000),                       # se fue: no es antigüedad de la dotación
    _emp("preingreso", -60),                   # no entró: su antigüedad sería NEGATIVA
    _emp("activo", 40, EMPRESA_B),             # otra empresa: mueve el número si el eq se cae
]


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({"empleados": [dict(e) for e in _PADRON]})
    monkeypatch.setattr(ant, "supabase_admin", a)
    return a


def test_promedio_y_mediana_no_son_el_mismo_numero(almacen) -> None:
    """El corazón del KPI: con el padrón conocido, los dos valores son los esperados Y difieren.

    Para que falle: devolver el promedio en los dos lugares, calcular la mediana como promedio,
    o cambiar el divisor de años.
    """
    promedio, mediana = ant.antiguedad(_HOY, EMPRESA_A)
    assert (promedio, mediana) == (4.3, 2.0)


def test_no_promedia_a_los_que_no_son_dotacion(almacen) -> None:
    """La baja de 10.000 días y el preingreso de fecha futura quedan afuera.

    Si el `.eq("estado", "activo")` desapareciera, el promedio de la empresa A pasaría de 4,3 a
    ~9,4 años: la baja sola pesa más que todos los activos juntos.
    """
    promedio, _ = ant.antiguedad(_HOY, EMPRESA_A)
    assert promedio == 4.3, "entró alguien que no está en la dotación"


def test_filtra_por_la_empresa_del_sidebar(almacen) -> None:
    """El dashboard es VISTA: respeta el selector, y los tres cortes dan tres números distintos.

    🔴 El consolidado NO es "la empresa más grande": mete al de 40 días de la empresa B y baja
    las dos medidas. Es el caso que hace que este KPI necesite la mediana al lado del promedio.
    Con B sola queda una persona, y ahí promedio y mediana coinciden por construcción (n=1).
    """
    assert ant.antiguedad(_HOY, EMPRESA_A) == (4.3, 2.0)
    assert ant.antiguedad(_HOY, EMPRESA_B) == (0.1, 0.1)
    assert ant.antiguedad(_HOY, None) == (3.3, 1.5)


def test_sin_activos_devuelve_ceros_y_no_revienta(monkeypatch) -> None:
    """Empty state: es el estado REAL de cualquier empresa recién creada. Un ZeroDivisionError
    acá se comería el KPI entero vía el `_safe` de `calcular_extras` y nadie vería por qué."""
    monkeypatch.setattr(ant, "supabase_admin", Almacen({"empleados": []}))
    assert ant.antiguedad(_HOY, None) == (0.0, 0.0)
