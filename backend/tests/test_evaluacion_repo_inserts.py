"""
Test repo-level: crear_evaluados / crear_resultados deben levantar AppError (DB_ERROR) si el
insert no devuelve TODAS las filas esperadas (parcial o vacío), en vez de devolver []/corto en
silencio. Es lo que hace confiable la verificación por conteo del import. Sin red: fake supabase.
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

import pytest

# 🔄 El insert en lote (`insert_completo`) se mudó de `evaluacion_repo` a `_evaluacion_insert`
# al partirse el repo por entidad: parchear el repo ya no lo alcanza, y sin este import los
# tests salían a la red de verdad en vez de contra el fake.
import repositories._evaluacion_insert as insert_mod
import repositories.evaluacion_repo as evaluacion_repo
from repositories.evaluacion_repo import EvaluacionRepo
from utils.errors import AppError


class _FakeInsert:
    def __init__(self, data): self.data = data
    def insert(self, _filas): return self
    def execute(self): return SimpleNamespace(data=self.data)


class _FakeSupa:
    """table().insert().execute() devuelve `data` fijo — simula el resultado del insert."""
    def __init__(self, data): self._data = data
    def table(self, _name): return _FakeInsert(self._data)


def test_crear_evaluados_insert_vacio_levanta(monkeypatch):
    monkeypatch.setattr(insert_mod, "supabase_admin", _FakeSupa([]))  # 0 filas devueltas
    with pytest.raises(AppError) as e:
        EvaluacionRepo().crear_evaluados([{"a": 1}, {"a": 2}])
    assert e.value.code == "DB_ERROR" and e.value.status_code == 500


def test_crear_evaluados_insert_parcial_levanta(monkeypatch):
    monkeypatch.setattr(insert_mod, "supabase_admin", _FakeSupa([{"x": 1}]))  # 1 de 2
    with pytest.raises(AppError) as e:
        EvaluacionRepo().crear_evaluados([{"a": 1}, {"a": 2}])
    assert e.value.code == "DB_ERROR"


def test_crear_resultados_insert_vacio_levanta(monkeypatch):
    monkeypatch.setattr(insert_mod, "supabase_admin", _FakeSupa([]))
    with pytest.raises(AppError) as e:
        EvaluacionRepo().crear_resultados([{"a": 1}])
    assert e.value.code == "DB_ERROR"


def test_crear_evaluados_sin_filas_no_es_error(monkeypatch):
    # entrada vacía = nada que insertar → [] (no toca supabase, no es error)
    monkeypatch.setattr(insert_mod, "supabase_admin", _FakeSupa([]))
    assert EvaluacionRepo().crear_evaluados([]) == []
    assert EvaluacionRepo().crear_resultados([]) == []
