"""
Tests del export de vacaciones: columnas legibles (sin UUIDs crudos) y filtro
por empleado con ownership.

Cubre: (a) construir_filas_export omite id/empresa_id/empleado_id/area_id y deja
headers legibles + cancelada Sí/No + fechas dd/mm/aaaa; (b) resolver_empleado_ids
estrecha por empleado respetando el alcance (mando pidiendo un ajeno → vacío);
(c) VacacionesService.exportar por empleado usa el listado general (find_all, todos
los tipos + canceladas), NO el endpoint parcial de la ficha.
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

from datetime import date, datetime

from schemas.vacaciones import SolicitudVacacionesResponse
from services._ownership_filter import resolver_empleado_ids
from services._vacaciones_export import construir_filas_export
from services.vacaciones_service import VacacionesService

_SELF, _S1, _S2 = "e-self", "s1", "s2"

_HEADERS = ["Empresa", "Empleado", "Área", "Fecha desde", "Fecha hasta",
            "Días", "Tipo", "Comentario", "Estado", "Cancelada", "Creada"]
_UUID_KEYS = {"id", "empresa_id", "empleado_id", "area_id"}


def _sol(**over) -> SolicitudVacacionesResponse:
    base = dict(
        id="11111111-1111-1111-1111-111111111111",
        empresa_id="22222222-2222-2222-2222-222222222222",
        empresa_nombre="Karstec", empleado_id="33333333-3333-3333-3333-333333333333",
        empleado_nombre="Ana Lopez", area_id="44444444-4444-4444-4444-444444444444",
        area_nombre="Tecnología", fecha_desde=date(2026, 1, 10), fecha_hasta=date(2026, 1, 20),
        dias=11, tipo="dia_free", comentario="ok", cancelada=True, estado="cancelada",
        created_at=datetime(2026, 1, 5, 14, 30, 45),
    )
    base.update(over)
    return SolicitudVacacionesResponse(**base)


# ── Parte 1: columnas legibles ───────────────────────────────────────────────

def test_export_omite_columnas_de_id_crudo():
    fila = construir_filas_export([_sol()])[0]
    assert list(fila.keys()) == _HEADERS               # orden y headers exactos
    assert _UUID_KEYS.isdisjoint(fila.keys())          # ningún UUID crudo


def test_export_formatea_cancelada_y_fechas():
    fila = construir_filas_export([_sol()])[0]
    assert fila["Cancelada"] == "Sí"                   # booleano → Sí/No
    assert fila["Creada"] == "05/01/2026"              # sin hora/microsegundos
    assert fila["Fecha desde"] == "10/01/2026" and fila["Fecha hasta"] == "20/01/2026"
    assert fila["Empresa"] == "Karstec" and fila["Empleado"] == "Ana Lopez"
    assert fila["Días"] == 11 and fila["Tipo"] == "dia_free"


def test_export_cancelada_false_es_no():
    assert construir_filas_export([_sol(cancelada=False, estado="tomada")])[0]["Cancelada"] == "No"


# ── Parte 2: resolver_empleado_ids (ownership + empleado) ─────────────────────

class _FakeOwn:
    def __init__(self, *, empleado=None, subs=None, area=None) -> None:
        self._e, self._s, self._a = empleado, subs or [], area or []

    def find_by_user_id(self, user_id):
        return self._e

    def ids_subordinados(self, empleado_id):
        return list(self._s)

    def ids_empleados_por_area(self, empresa_id, area_id):
        return list(self._a)


def test_admin_acota_a_empleado_puntual():
    ids, vacio = resolver_empleado_ids("u", "admin_rrhh", None, None, _S1, _FakeOwn())
    assert (ids, vacio) == ([_S1], False)              # admin exporta a un empleado concreto


def test_admin_sin_empleado_sin_restriccion():
    ids, vacio = resolver_empleado_ids("u", "admin_rrhh", None, None, None, _FakeOwn())
    assert (ids, vacio) == (None, False)               # sin empleado → como hoy


def test_mando_exporta_su_subordinado():
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1, _S2])
    ids, vacio = resolver_empleado_ids("u", "mandos_medios", None, None, _S1, own)
    assert (ids, vacio) == ([_S1], False)              # está en su alcance


def test_mando_exporta_ajeno_recibe_vacio():
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1])
    ids, vacio = resolver_empleado_ids("u", "mandos_medios", None, None, _S2, own)
    assert (ids, vacio) == (None, True)                # ajeno → vacío (fail-closed)


def test_mando_sin_subs_exporta_cualquiera_vacio():
    ids, vacio = resolver_empleado_ids("u", "mandos_medios", None, None, _S1, _FakeOwn(empleado=None))
    assert (ids, vacio) == (None, True)


# ── Parte 2: wiring del service.exportar ──────────────────────────────────────

class _FakeRepo:
    def __init__(self) -> None:
        self.find_all_calls: list = []
        self.parcial_calls: list = []

    def find_all(self, empresa_id, empleado_ids, page, page_size, estado=None, today=None, *, desde=None, hasta=None):
        # desde/hasta se aceptan y se IGNORAN a propósito: este fake cubre el eje de OWNERSHIP.
        # El eje de fechas lo cubre test_filtro_rango_fechas.py contra el repo real.
        self.find_all_calls.append(empleado_ids)
        return [], 0

    def find_vacaciones_empleado(self, empleado_id, empresa_id=None):
        # Firma alineada con el repo real (Tanda 1b.2 le sumó empresa_id): si el service llamara
        # a este atajo con 2 args, el fake tiene que fallar por la ASERCIÓN de abajo, no por un
        # TypeError que enmascare qué se rompió.
        self.parcial_calls.append(empleado_id)          # NO debería llamarse en el export
        return []


def _svc(repo, own):
    return VacacionesService(repo=repo, ownership_repo=own)


def test_exportar_por_empleado_usa_listado_general_no_parcial():
    repo = _FakeRepo()
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1])
    _svc(repo, own).exportar("u", "mandos_medios", None, "excel", None, _S1)
    assert repo.find_all_calls == [[_S1]]               # listado general (todos los tipos + canceladas)
    assert repo.parcial_calls == []                     # NUNCA el endpoint parcial de la ficha


def test_exportar_mando_ajeno_no_consulta_la_tabla():
    repo = _FakeRepo()
    own = _FakeOwn(empleado={"id": _SELF}, subs=[_S1])
    d = _svc(repo, own).exportar("u", "mandos_medios", None, "excel", None, _S2)
    assert repo.find_all_calls == []                    # vacío → no se consultó
    assert d.filename.endswith(".xlsx")                 # igual devuelve un archivo (vacío)


def test_exportar_admin_acota_a_empleado():
    repo = _FakeRepo()
    _svc(repo, _FakeOwn()).exportar("u", "admin_rrhh", None, "excel", None, _S2)
    assert repo.find_all_calls == [[_S2]]
