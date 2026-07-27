"""
Tests del análisis por área de sucesión (get_analisis_posicion) tras cerrar el N+1: los scores de
assessment se resuelven con UN solo lookup batch (`.in_`), no una query por empleado.

Qué se fija acá:
- El shape de la respuesta no cambió (área con resultados, sin resultados, mixta, vacía).
- Con varios resultados por empleado gana el más reciente por `completado_en`, resuelto en Python
  (no se asume que Supabase respete el orden dentro del `in_`).
- **El conteo de queries**: una sola consulta a assessment_resultados sin importar cuántos
  empleados tenga el área. Ese es el test que evita que el N+1 vuelva.

⚠️ El fake de acá SÍ honra empresa_id (filtra por `.eq("empresa_id", ...)` como el `_with_empresa`
real): sin eso, un test de scope pasaría en verde sin validar nada.
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

from types import SimpleNamespace
from uuid import uuid4

import pytest

import repositories.sucesion_repo as repo_mod
from repositories.sucesion_repo import SucesionRepo

EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())
AREA, AREA_VACIA = str(uuid4()), str(uuid4())


def _emp(id_: str, nombre: str, empresa_id: str = EMPRESA_A, area_id: str = AREA) -> dict:
    return {"id": id_, "empresa_id": empresa_id, "area_id": area_id, "estado": "activo",
            "nombre": nombre, "apellido": "Test", "roles": ["Analista"],
            "potencial": "alto", "desempeno": "medio"}


def _res(empleado_id: str, general, completado_en) -> dict:
    return {"empleado_id": empleado_id, "puntuacion": {"general": general},
            "completado_en": completado_en}


class _FakeTable:
    """Aplica de verdad eq/neq/in_ sobre las filas canned (incluido empresa_id)."""

    def __init__(self, rows: list, log: list, tabla: str) -> None:
        self._rows, self._log, self._tabla = list(rows), log, tabla

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if str(r.get(col)) == str(val)]
        return self

    def neq(self, col, val):
        self._rows = [r for r in self._rows if str(r.get(col)) != str(val)]
        return self

    def in_(self, col, vals):
        self._log.append((self._tabla, "in_", col, list(vals)))
        vals = {str(v) for v in vals}
        self._rows = [r for r in self._rows if str(r.get(col)) in vals]
        return self

    def order(self, *_a, **_k):  # si alguien vuelve al patrón viejo, el conteo lo delata igual
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _FakeSupabase:
    """Filas canned por tabla; registra cada tabla consultada (para contar queries)."""

    def __init__(self, por_tabla: dict) -> None:
        self._por_tabla, self.consultadas, self.filtros = por_tabla, [], []

    def table(self, name: str) -> _FakeTable:
        self.consultadas.append(name)
        return _FakeTable(self._por_tabla.get(name, []), self.filtros, name)

    def queries_a(self, tabla: str) -> int:
        return self.consultadas.count(tabla)


def _repo(monkeypatch, empleados: list, resultados: list) -> tuple:
    fake = _FakeSupabase({"empleados": empleados, "assessment_resultados": resultados})
    monkeypatch.setattr(repo_mod, "supabase_admin", fake)
    return SucesionRepo(), fake


E1, E2, E3 = str(uuid4()), str(uuid4()), str(uuid4())


def test_area_con_resultados_devuelve_scores_ordenados(monkeypatch):
    repo, fake = _repo(monkeypatch,
                       [_emp(E1, "Uno"), _emp(E2, "Dos")],
                       [_res(E1, 70, "2026-01-01T00:00:00Z"), _res(E2, 90, "2026-01-01T00:00:00Z")])
    out = repo.get_analisis_posicion(AREA, EMPRESA_A)
    assert [(o.nombre, o.score) for o in out] == [("Dos", 90), ("Uno", 70)]
    assert out[0].cargo == "Analista" and out[0].potencial == "alto" and out[0].desempeno == "medio"
    assert fake.queries_a("assessment_resultados") == 1


def test_empleados_sin_resultado_score_none_y_van_al_final(monkeypatch):
    """Comportamiento preservado: sin fila de assessment el score es None, no un error ni un 0."""
    repo, _ = _repo(monkeypatch, [_emp(E1, "Uno"), _emp(E2, "Dos")], [])
    out = repo.get_analisis_posicion(AREA, EMPRESA_A)
    assert [(o.nombre, o.score) for o in out] == [("Uno", None), ("Dos", None)]


def test_area_mixta_los_sin_score_quedan_ultimos(monkeypatch):
    repo, _ = _repo(monkeypatch,
                    [_emp(E1, "Uno"), _emp(E2, "Dos"), _emp(E3, "Tres")],
                    [_res(E2, 55, "2026-01-01T00:00:00Z")])
    out = repo.get_analisis_posicion(AREA, EMPRESA_A)
    assert [(o.nombre, o.score) for o in out] == [("Dos", 55), ("Uno", None), ("Tres", None)]


def test_area_vacia_no_dispara_query_de_assessment(monkeypatch):
    """Sin empleados no se llama al lookup con lista vacía (traería filas de TODA la base)."""
    repo, fake = _repo(monkeypatch, [_emp(E1, "Uno")], [_res(E1, 70, "2026-01-01T00:00:00Z")])
    assert repo.get_analisis_posicion(AREA_VACIA, EMPRESA_A) == []
    assert fake.queries_a("assessment_resultados") == 0


def test_varios_resultados_gana_el_mas_reciente(monkeypatch):
    """El orden llega desordenado a propósito: el desempate se resuelve en Python."""
    repo, _ = _repo(monkeypatch, [_emp(E1, "Uno")],
                    [_res(E1, 40, "2025-01-01T00:00:00Z"),
                     _res(E1, 95, "2026-06-01T00:00:00Z"),
                     _res(E1, 60, "2025-12-31T23:59:59Z")])
    assert [o.score for o in repo.get_analisis_posicion(AREA, EMPRESA_A)] == [95]


def test_resultado_sin_completado_en_no_le_gana_al_completado(monkeypatch):
    repo, _ = _repo(monkeypatch, [_emp(E1, "Uno")],
                    [_res(E1, 10, None), _res(E1, 80, "2026-06-01T00:00:00Z")])
    assert [o.score for o in repo.get_analisis_posicion(AREA, EMPRESA_A)] == [80]


def test_puntuacion_ilegible_o_sin_general_score_none(monkeypatch):
    """Preserva el criterio viejo: 'total' como fallback, y basura → None (no rompe el endpoint)."""
    repo, _ = _repo(monkeypatch, [_emp(E1, "Uno"), _emp(E2, "Dos"), _emp(E3, "Tres")], [
        {"empleado_id": E1, "puntuacion": {"total": 77}, "completado_en": "2026-01-01T00:00:00Z"},
        {"empleado_id": E2, "puntuacion": {"otra_cosa": 5}, "completado_en": "2026-01-01T00:00:00Z"},
        {"empleado_id": E3, "puntuacion": {"general": "no-es-numero"},
         "completado_en": "2026-01-01T00:00:00Z"},
    ])
    out = {o.nombre: o.score for o in repo.get_analisis_posicion(AREA, EMPRESA_A)}
    assert out == {"Uno": 77, "Dos": None, "Tres": None}


def test_puntuacion_como_string_json_se_parsea(monkeypatch):
    """Supabase puede devolver el JSONB como string; el parseo sigue vivo tras el batch."""
    repo, _ = _repo(monkeypatch, [_emp(E1, "Uno")],
                    [{"empleado_id": E1, "puntuacion": '{"general": 88}',
                      "completado_en": "2026-01-01T00:00:00Z"}])
    assert [o.score for o in repo.get_analisis_posicion(AREA, EMPRESA_A)] == [88]


def test_empleado_de_otra_empresa_no_entra_ni_al_lookup(monkeypatch):
    """El scope de empresa (Fase 2) se mantiene: el ajeno no sale ni sus ids se piden."""
    repo, fake = _repo(monkeypatch,
                       [_emp(E1, "Propio"), _emp(E2, "Ajeno", empresa_id=EMPRESA_B)],
                       [_res(E1, 70, "2026-01-01T00:00:00Z"), _res(E2, 99, "2026-01-01T00:00:00Z")])
    out = repo.get_analisis_posicion(AREA, EMPRESA_A)
    assert [(o.nombre, o.score) for o in out] == [("Propio", 70)]
    pedidos = [f for f in fake.filtros if f[0] == "assessment_resultados"][0][3]
    assert pedidos == [E1]


def test_empresa_none_es_consolidado(monkeypatch):
    """None = 'Todas las empresas': entran las dos, siempre con una sola query de assessment."""
    repo, fake = _repo(monkeypatch,
                       [_emp(E1, "Propio"), _emp(E2, "Ajeno", empresa_id=EMPRESA_B)],
                       [_res(E1, 70, "2026-01-01T00:00:00Z"), _res(E2, 99, "2026-01-01T00:00:00Z")])
    out = repo.get_analisis_posicion(AREA, None)
    assert [(o.nombre, o.score) for o in out] == [("Ajeno", 99), ("Propio", 70)]
    assert fake.queries_a("assessment_resultados") == 1


def test_empleado_dado_de_baja_queda_afuera(monkeypatch):
    baja = _emp(E2, "Baja")
    baja["estado"] = "baja"
    repo, _ = _repo(monkeypatch, [_emp(E1, "Uno"), baja], [_res(E2, 99, "2026-01-01T00:00:00Z")])
    assert [o.nombre for o in repo.get_analisis_posicion(AREA, EMPRESA_A)] == ["Uno"]


@pytest.mark.parametrize("cantidad", [1, 20, 200])
def test_una_sola_query_de_assessment_sea_cual_sea_la_dotacion(cantidad):
    """EL test anti-regresión del N+1: con 200 empleados eran 201 requests; ahora son 2."""
    empleados = [_emp(str(uuid4()), f"Emp{i}") for i in range(cantidad)]
    resultados = [_res(e["id"], 50, "2026-01-01T00:00:00Z") for e in empleados]
    fake = _FakeSupabase({"empleados": empleados, "assessment_resultados": resultados})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(repo_mod, "supabase_admin", fake)
        out = SucesionRepo().get_analisis_posicion(AREA, EMPRESA_A)
    assert len(out) == cantidad
    assert fake.queries_a("assessment_resultados") == 1
    assert fake.consultadas == ["empleados", "assessment_resultados"]  # 2 queries en total
