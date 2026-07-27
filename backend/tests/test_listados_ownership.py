"""
Tests de wiring del ownership en los listados de vacaciones y ausencias.

Verifican que Service.get_all: (a) admin → find_all sin filtro por empleado
(empleado_ids=None, comportamiento actual intacto); (b) mando → find_all con
[self, *subordinados]; (c) mando sin subordinados → NO consulta la tabla y
devuelve vacío; (d) mando + area_id → intersección. Repos y ownership_repo
fakeados (sin DB).
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

from services.ausencias_service import AusenciasService
from services.vacaciones_service import VacacionesService

_SELF, _S1, _S2 = "e", "s1", "s2"


class _FakeOwn:
    def __init__(self, *, empleado=None, subs=None, area=None) -> None:
        self._e, self._s, self._a = empleado, subs or [], area or []

    def find_by_user_id(self, user_id):
        return self._e

    def ids_subordinados(self, empleado_id):
        return list(self._s)

    def ids_empleados_por_area(self, empresa_id, area_id):
        return list(self._a)


class _FakeVacRepo:
    def __init__(self) -> None:
        self.calls: list = []

    def find_all(self, empresa_id, empleado_ids, page, page_size, estado=None, today=None, *, desde=None, hasta=None):
        # desde/hasta se aceptan y se IGNORAN a propósito: este fake cubre el eje de OWNERSHIP.
        # El eje de fechas lo cubre test_filtro_rango_fechas.py contra el repo real.
        self.calls.append(empleado_ids)
        return [], 0


class _FakeAusRepo:
    def __init__(self) -> None:
        self.calls: list = []

    def find_all(self, empresa_id, empleado_ids, tipo_id, page, page_size, *, desde=None, hasta=None):
        # desde/hasta se aceptan y se IGNORAN a propósito: este fake cubre el eje de OWNERSHIP.
        # El eje de fechas lo cubre test_filtro_rango_fechas.py contra el repo real.
        self.calls.append(empleado_ids)
        return [], 0


# ── Vacaciones ──────────────────────────────────────────────────────────────

def test_vac_admin_find_all_sin_filtro():
    repo = _FakeVacRepo()
    out = VacacionesService(repo=repo, ownership_repo=_FakeOwn()).get_all("u", "admin_rrhh")
    assert repo.calls == [None] and out.total == 0  # None = sin restricción de empleado


def test_vac_mando_filtra_por_self_y_subs():
    repo = _FakeVacRepo()
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1, _S2])
    VacacionesService(repo=repo, ownership_repo=own).get_all("u", "mandos_medios")
    assert repo.calls == [[_SELF, _S1, _S2]]


def test_vac_mando_sin_subs_no_consulta_y_vacio():
    repo = _FakeVacRepo()
    out = VacacionesService(repo=repo, ownership_repo=_FakeOwn(empleado=None)).get_all("u", "mandos_medios")
    assert repo.calls == [] and out.items == [] and out.total == 0  # no tocó la tabla


def test_vac_mando_con_area_interseccion():
    repo = _FakeVacRepo()
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1, _S2], area=[_S2, "x"])
    VacacionesService(repo=repo, ownership_repo=own).get_all("u", "mandos_medios", area_id="a")
    assert repo.calls == [[_S2]]  # solo el que está en subordinados Y en el área


# ── Ausencias ───────────────────────────────────────────────────────────────

def test_aus_admin_find_all_sin_filtro():
    repo = _FakeAusRepo()
    out = AusenciasService(repo=repo, ownership_repo=_FakeOwn()).get_all("u", "gerencia_lectura")
    assert repo.calls == [None] and out.total == 0


def test_aus_mando_filtra_por_self_y_subs():
    repo = _FakeAusRepo()
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1])
    AusenciasService(repo=repo, ownership_repo=own).get_all("u", "mandos_medios")
    assert repo.calls == [[_SELF, _S1]]


def test_aus_mando_sin_subs_no_consulta_y_vacio():
    repo = _FakeAusRepo()
    out = AusenciasService(repo=repo, ownership_repo=_FakeOwn(empleado=None)).get_all("u", "mandos_medios")
    assert repo.calls == [] and out.items == [] and out.total == 0


def test_aus_mando_con_area_interseccion():
    repo = _FakeAusRepo()
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1, _S2], area=[_S1, "x"])
    AusenciasService(repo=repo, ownership_repo=own).get_all("u", "mandos_medios", area_id="a")
    assert repo.calls == [[_S1]]
