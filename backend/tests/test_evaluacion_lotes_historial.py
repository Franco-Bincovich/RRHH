"""
Test del enriquecimiento del historial de lotes (enriquecer_lotes): que cada lote salga con
nombre de empresa, nombre de quién importó (o None) y conteo de evaluados, resueltos con
lookups batch sobre un fake de supabase (sin red). Verifica también que no dispara queries con
lista vacía.
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

import repositories._evaluacion_lotes_enrich as enrich


class _FakeTable:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def in_(self, *_a, **_k):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _FakeSupabase:
    """Devuelve filas canned por tabla y registra qué tablas se consultaron."""
    def __init__(self, por_tabla: dict) -> None:
        self._por_tabla = por_tabla
        self.consultadas: list = []

    def table(self, name: str) -> _FakeTable:
        self.consultadas.append(name)
        return _FakeTable(self._por_tabla.get(name, []))


def test_enriquecer_lotes_agrega_empresa_usuario_y_conteo(monkeypatch):
    emp, usuario = str(uuid4()), str(uuid4())
    l1, l2 = str(uuid4()), str(uuid4())
    rows = [
        {"id": l1, "empresa_id": emp, "periodo": "Julio 2026", "importado_por": usuario,
         "created_at": "2026-07-01T10:00:00+00:00"},
        {"id": l2, "empresa_id": emp, "periodo": "Junio 2026", "importado_por": None,
         "created_at": "2026-06-01T10:00:00+00:00"},
    ]
    fake = _FakeSupabase({
        "empresas": [{"id": emp, "nombre": "DOSUBA"}],
        "users": [{"id": usuario, "nombre": "Ana", "apellido": "Pérez"}],
        "evaluacion_evaluados": [{"lote_id": l1}] * 10,  # 10 evaluados en l1, 0 en l2
    })
    monkeypatch.setattr(enrich, "supabase_admin", fake)

    out = enrich.enriquecer_lotes(rows)

    por_id = {str(o.id): o for o in out}
    assert por_id[l1].empresa_nombre == "DOSUBA"
    assert por_id[l1].importado_por_nombre == "Ana Pérez"
    assert por_id[l1].evaluados == 10
    # importado_por NULL → nombre None; sin evaluados → conteo 0
    assert por_id[l2].importado_por_nombre is None
    assert por_id[l2].evaluados == 0
    assert por_id[l2].empresa_nombre == "DOSUBA"


def test_enriquecer_lotes_vacio_no_consulta(monkeypatch):
    fake = _FakeSupabase({})
    monkeypatch.setattr(enrich, "supabase_admin", fake)
    assert enrich.enriquecer_lotes([]) == []
    assert fake.consultadas == []  # sin filas no dispara ningún lookup
