"""
Tests de ownership por fila en las ESCRITURAS de vacaciones y ausencias.

Sensibles: verifican que un mando NO puede crear/cancelar/editar/borrar sobre un
empleado ajeno, y que cuando se deniega la MUTACIÓN NO ocurre. admin/gerencia
gestionan a cualquiera; mando sin empleado vinculado no gestiona a nadie.
Repos/audit/periodo fakeados (sin DB).
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
from uuid import UUID

import pytest

from schemas.ausencias import AusenciaCreate, AusenciaResponse, AusenciaUpdate
from schemas.vacaciones import SolicitudVacacionesCreate, SolicitudVacacionesResponse
from services.ausencias_service import AusenciasService
from services.vacaciones_service import VacacionesService
from utils.errors import AppError

_SELF = "11111111-1111-1111-1111-111111111111"
_SUB1 = "22222222-2222-2222-2222-222222222222"   # subordinado del mando
_SUB2 = "33333333-3333-3333-3333-333333333333"   # AJENO al mando
_ID = "44444444-4444-4444-4444-444444444444"     # id del registro


# ── Dobles ───────────────────────────────────────────────────────────────────

class _Own:
    """Ownership repo fake: el mando es _SELF con subordinado _SUB1 (=> _SUB2 es ajeno)."""
    def __init__(self, *, empleado=None, subs=None) -> None:
        self._e, self._s = empleado, subs or []

    def find_by_user_id(self, user_id):
        return self._e

    def ids_subordinados(self, empleado_id):
        return list(self._s)


class _Periodo:
    def find_cerrados(self, empresa_id, modulo):
        return []


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw):
        self.calls.append(kw)


def _vac_row(empleado_id: str, cancelada: bool = False) -> SolicitudVacacionesResponse:
    return SolicitudVacacionesResponse(
        id=_ID, empresa_id="emp-1", empleado_id=empleado_id, fecha_desde=date(2026, 3, 1),
        fecha_hasta=date(2026, 3, 5), dias=5, tipo="vacaciones", cancelada=cancelada,
        estado="cancelada" if cancelada else "planificada", created_at=datetime(2026, 2, 1, 9, 0, 0),
    )


def _aus_row(empleado_id: str) -> AusenciaResponse:
    return AusenciaResponse(
        id=_ID, empresa_id="emp-1", empleado_id=empleado_id, tipo_id="t-1",
        fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 3, 2), dias=2,
        justificada=True, created_at=datetime(2026, 2, 1, 9, 0, 0),
    )


class _VacRepo:
    def __init__(self, *, row=None) -> None:
        self._row = row
        self.saved = None
        self.cancelled = None

    def find_empresa_for_empleado(self, eid):
        return "emp-1"

    def find_overlapping(self, *a):
        return []

    def save(self, empleado_id, *a):
        self.saved = empleado_id
        return _vac_row(empleado_id)

    def find_by_id(self, id, empresa_id=None):
        # HONRA empresa_id (antes devolvía la fila siempre, tapando el eje de empresa). Los tests
        # de este archivo llaman con empresa_id=None (consolidado), así que el resultado no cambia
        # —lo que cambia es que el fake ya no puede dar verde si el filtro real se rompe.
        if not self._row or (empresa_id and str(self._row.empresa_id) != str(empresa_id)):
            return None
        return self._row

    def cancel(self, id, empresa_id=None):
        self.cancelled = id
        return _vac_row(self._row.empleado_id, cancelada=True)


class _AusRepo:
    def __init__(self, *, row=None) -> None:
        self._row = row
        self.saved = None
        self.updated = None
        self.deleted = None

    def find_empresa_for_empleado(self, eid):
        return "emp-1"

    def save(self, empleado_id, *a):
        self.saved = empleado_id
        return _aus_row(empleado_id)

    def find_by_id(self, id, empresa_id=None):
        # HONRA empresa_id (antes devolvía la fila siempre, tapando el eje de empresa). Los tests
        # de este archivo llaman con empresa_id=None (consolidado), así que el resultado no cambia
        # —lo que cambia es que el fake ya no puede dar verde si el filtro real se rompe.
        if not self._row or (empresa_id and str(self._row.empresa_id) != str(empresa_id)):
            return None
        return self._row

    def update(self, id, empresa_id, payload):
        self.updated = id
        return self._row

    def delete(self, id, empresa_id=None):
        self.deleted = id
        return True


def _vac(repo, own):
    return VacacionesService(repo=repo, audit=_Audit(), periodo_repo=_Periodo(), ownership_repo=own)


def _aus(repo, own):
    return AusenciasService(repo=repo, audit=_Audit(), periodo_repo=_Periodo(), ownership_repo=own)


def _mando():
    return _Own(empleado={"id": _SELF}, subs=[_SUB1])


def _vac_create(empleado_id: str) -> SolicitudVacacionesCreate:
    return SolicitudVacacionesCreate(empleado_id=UUID(empleado_id), fecha_desde=date(2026, 3, 1),
                                     fecha_hasta=date(2026, 3, 5), tipo="vacaciones")


def _aus_create(empleado_id: str) -> AusenciaCreate:
    return AusenciaCreate(empleado_id=UUID(empleado_id), tipo_id=UUID(_ID),
                          fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 3, 2))


# ── VACACIONES — create ──────────────────────────────────────────────────────

def test_vac_create_mando_subordinado_ok():
    repo = _VacRepo()
    _vac(repo, _mando()).create(_vac_create(_SUB1), _SELF, "mandos_medios")
    assert repo.saved == _SUB1


def test_vac_create_mando_ajeno_403_no_muta():
    repo = _VacRepo()
    with pytest.raises(AppError) as e:
        _vac(repo, _mando()).create(_vac_create(_SUB2), _SELF, "mandos_medios")
    assert e.value.code == "OWNERSHIP_DENIED" and e.value.status_code == 403
    assert repo.saved is None                       # la creación NO ocurrió


def test_vac_create_admin_gestiona_cualquiera():
    repo = _VacRepo()
    _vac(repo, _Own()).create(_vac_create(_SUB2), "admin-uid", "admin_rrhh")
    assert repo.saved == _SUB2


def test_vac_create_mando_sin_empleado_403():
    repo = _VacRepo()
    with pytest.raises(AppError) as e:
        _vac(repo, _Own(empleado=None)).create(_vac_create(_SUB1), _SELF, "mandos_medios")
    assert e.value.status_code == 403 and repo.saved is None


# ── VACACIONES — cancel ──────────────────────────────────────────────────────

def test_vac_cancel_mando_subordinado_ok():
    repo = _VacRepo(row=_vac_row(_SUB1))
    _vac(repo, _mando()).cancel(UUID(_ID), None, _SELF, "mandos_medios")
    assert repo.cancelled == _ID


def test_vac_cancel_mando_ajeno_404_no_muta():
    repo = _VacRepo(row=_vac_row(_SUB2))
    with pytest.raises(AppError) as e:
        _vac(repo, _mando()).cancel(UUID(_ID), None, _SELF, "mandos_medios")
    assert e.value.code == "VACACION_NOT_FOUND" and e.value.status_code == 404
    assert repo.cancelled is None                   # la cancelación NO ocurrió


# ── AUSENCIAS — create ───────────────────────────────────────────────────────

def test_aus_create_mando_subordinado_ok():
    repo = _AusRepo()
    _aus(repo, _mando()).create(_aus_create(_SUB1), _SELF, "mandos_medios")
    assert repo.saved == _SUB1


def test_aus_create_mando_ajeno_403_no_muta():
    repo = _AusRepo()
    with pytest.raises(AppError) as e:
        _aus(repo, _mando()).create(_aus_create(_SUB2), _SELF, "mandos_medios")
    assert e.value.code == "OWNERSHIP_DENIED" and e.value.status_code == 403
    assert repo.saved is None


# ── AUSENCIAS — update ───────────────────────────────────────────────────────

def test_aus_update_mando_subordinado_ok():
    repo = _AusRepo(row=_aus_row(_SUB1))
    _aus(repo, _mando()).update(UUID(_ID), AusenciaUpdate(justificada=False), None, _SELF, "mandos_medios")
    assert repo.updated == _ID


def test_aus_update_mando_ajeno_404_no_muta():
    repo = _AusRepo(row=_aus_row(_SUB2))
    with pytest.raises(AppError) as e:
        _aus(repo, _mando()).update(UUID(_ID), AusenciaUpdate(justificada=False), None, _SELF, "mandos_medios")
    assert e.value.code == "AUSENCIA_NOT_FOUND" and e.value.status_code == 404
    assert repo.updated is None


# ── AUSENCIAS — delete ───────────────────────────────────────────────────────

def test_aus_delete_mando_subordinado_ok():
    repo = _AusRepo(row=_aus_row(_SUB1))
    _aus(repo, _mando()).delete(UUID(_ID), None, _SELF, "mandos_medios")
    assert repo.deleted == _ID


def test_aus_delete_mando_ajeno_404_no_muta():
    repo = _AusRepo(row=_aus_row(_SUB2))
    with pytest.raises(AppError) as e:
        _aus(repo, _mando()).delete(UUID(_ID), None, _SELF, "mandos_medios")
    assert e.value.code == "AUSENCIA_NOT_FOUND" and e.value.status_code == 404
    assert repo.deleted is None


def test_aus_delete_inexistente_404():
    repo = _AusRepo(row=None)
    with pytest.raises(AppError) as e:
        _aus(repo, _mando()).delete(UUID(_ID), None, _SELF, "mandos_medios")
    assert e.value.status_code == 404 and repo.deleted is None


def test_aus_delete_admin_gestiona_cualquiera():
    repo = _AusRepo(row=_aus_row(_SUB2))
    _aus(repo, _Own()).delete(UUID(_ID), None, "admin-uid", "admin_rrhh")
    assert repo.deleted == _ID
