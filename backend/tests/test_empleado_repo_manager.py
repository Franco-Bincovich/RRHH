"""
Test repo-level de EmpleadoRepo.update para el manejo de manager_id: capturar el `patch`
que se envía a Supabase con un fake, sin red. Verifica que un null EXPLÍCITO limpia el
superior (deja de ser no-op), que asignar castea a str, y que omitir el campo no lo toca.
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
from uuid import UUID

import repositories.empleado_repo as empleado_repo
from repositories.empleado_repo import EmpleadoRepo
from schemas.empleado import EmpleadoUpdate

_MGR = UUID("33333333-3333-3333-3333-333333333333")

# Fila cruda que devuelve el "UPDATE ... RETURNING" para que _row la parsee a EmpleadoResponse.
_RAW_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "nombre": "Ana", "apellido": "García", "email_corporativo": "ana@karstec.com",
    "empresa_id": "e1", "area_id": "22222222-2222-2222-2222-222222222222",
    "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
    "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
}


class _FakeQuery:
    """Captura el patch del .update(...) y encadena .eq(...).execute()."""
    def __init__(self, cap: dict) -> None:
        self._cap = cap

    def update(self, patch):
        self._cap["patch"] = patch
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        return SimpleNamespace(data=[_RAW_ROW])


class _FakeSupabase:
    def __init__(self, cap: dict) -> None:
        self._cap = cap

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self._cap)


def _patch_de(monkeypatch, data: EmpleadoUpdate) -> dict:
    cap: dict = {}
    monkeypatch.setattr(empleado_repo, "supabase_admin", _FakeSupabase(cap))
    EmpleadoRepo().update("11111111-1111-1111-1111-111111111111", data)
    return cap["patch"]


def test_update_null_explicito_limpia_manager(monkeypatch):
    # "Sin superior": el front manda manager_id=null; el patch debe llevar manager_id=None (no no-op).
    patch = _patch_de(monkeypatch, EmpleadoUpdate(manager_id=None))
    assert "manager_id" in patch and patch["manager_id"] is None


def test_update_omitir_manager_no_lo_toca(monkeypatch):
    # No tocar el superior: manager_id ausente → no aparece en el patch.
    patch = _patch_de(monkeypatch, EmpleadoUpdate(nombre="Ana María"))
    assert "manager_id" not in patch


def test_update_asignar_manager_castea_str(monkeypatch):
    patch = _patch_de(monkeypatch, EmpleadoUpdate(manager_id=_MGR))
    assert patch["manager_id"] == str(_MGR)
