"""
Tests del CRUD de EmpleadoService (ficha del empleado) — fakes, sin red.

Cubre: alta (+audit), lectura, update (whitelist de campos +audit), baja (+audit) y los
errores esperados (legajo duplicado, empleado inexistente). Repo y AuditService fakeados
e inyectados por constructor; ningún test toca Supabase.

Nota sobre "DNI duplicado": la unicidad de DNI es una constraint de DB (no un check del
service), así que no es alcanzable con un fake sin simular el error de Postgres. El
duplicado que el service SÍ valida app-level es el legajo (LEGAJO_DUPLICADO) — es el que
se testea acá.

⚠️ _FakeRepo.find_by_id acepta empresa_id y NO lo aplica: es a propósito — este archivo cubre
el CRUD y la auditoría, no el eje de empresa (ese vive en test_empleado_manager_empresa.py y
test_empleado_area_empresa.py, con fakes que sí lo honran). No lo calques para probar empresa.
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

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import pytest

from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from services.empleado_service import EmpleadoService
from utils.errors import AppError

_ID = UUID("11111111-1111-1111-1111-111111111111")
_EMPRESA = UUID("99999999-9999-9999-9999-999999999999")
_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_C = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _resp(**over) -> EmpleadoResponse:
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "nombre": "Ana", "apellido": "García", "email_corporativo": "ana@karstec.com",
        "empresa_id": "e1", "empresa_nombre": None,
        "area_id": "22222222-2222-2222-2222-222222222222",
        "roles": ["Analista"], "modalidad_trabajo": "presencial",
        "tipo_contrato": "efectivo", "fecha_ingreso": "2024-01-01",
        "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    }
    base.update(over)
    return EmpleadoResponse.model_validate(base)


def _create(**over) -> EmpleadoCreate:
    base = dict(
        nombre="Ana", apellido="García", email_corporativo="ana@karstec.com",
        area_id=UUID("22222222-2222-2222-2222-222222222222"),
        roles=["Analista"], tipo_contrato="efectivo", fecha_ingreso=date(2024, 1, 1),
        empresa_id=_EMPRESA,
    )
    base.update(over)
    return EmpleadoCreate(**base)


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeRepo:
    """Repo fake configurable. Captura save/update/soft_delete/find_all para aserción."""
    _SENTINEL = object()

    def __init__(self) -> None:
        self.legajo_existing = None            # find_by_legajo
        self.by_id = None                      # find_by_id (prior + update echo)
        self.by_id_map = None                  # opcional: id→EmpleadoResponse para caminar la cadena de managers
        self.update_returns = self._SENTINEL   # None simula "no encontrado"
        self.soft_delete_returns = True
        self.find_all_returns = ([], 0)
        self.saved = None
        self.updated = None                    # (id, data)
        self.soft_deleted = None
        self.find_all_args = None

    def find_by_legajo(self, legajo, empresa_id):
        return self.legajo_existing

    def save(self, data, empresa_id):
        self.saved = (data, empresa_id)
        return _resp()

    def find_by_id(self, id, empresa_id=None):
        # Con by_id_map, resuelve por id (para caminar la cadena de managers); el resto cae a by_id.
        if self.by_id_map is not None and str(id) in self.by_id_map:
            return self.by_id_map[str(id)]
        return self.by_id

    def update(self, id, data, empresa_id=None):
        self.updated = (id, data)
        return self.by_id if self.update_returns is self._SENTINEL else self.update_returns

    def soft_delete(self, id, empresa_id=None):
        self.soft_deleted = id
        return self.soft_delete_returns

    def find_all(self, page, page_size, empresa_id=None, area_id=None, estado=None, search=None, es_lider=None, proyecto_ids=None, sin_manager=None):
        self.find_all_args = dict(page=page, page_size=page_size, empresa_id=empresa_id,
                                  area_id=area_id, estado=estado, search=search, es_lider=es_lider,
                                  proyecto_ids=proyecto_ids, sin_manager=sin_manager)
        return self.find_all_returns


class _AreaRepoPermisivo:
    """area_repo fake que acepta cualquier área: estos tests son del CRUD, no del gate de área
    (ese vive en test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


def _svc(repo=None, audit=None) -> EmpleadoService:
    return EmpleadoService(repo=repo or _FakeRepo(), audit=audit or _FakeAudit(),
                           area_repo=_AreaRepoPermisivo())


# ─── Alta ───────────────────────────────────────────────────────────────────────

def test_create_persiste_y_audita_alta():
    repo, audit = _FakeRepo(), _FakeAudit()
    out = _svc(repo, audit).create_empleado(_create(), "u1", _EMPRESA)
    assert out.nombre == "Ana"
    assert repo.saved is not None and repo.saved[1] == _EMPRESA
    assert [c["evento"] for c in audit.calls] == ["alta_empleado"]


def test_create_legajo_duplicado_409_no_guarda():
    repo = _FakeRepo()
    repo.legajo_existing = _resp(id="otro-id")  # ya existe ese legajo en la empresa
    with pytest.raises(AppError) as e:
        _svc(repo).create_empleado(_create(legajo="L-001"), "u1", _EMPRESA)
    assert e.value.code == "LEGAJO_DUPLICADO" and e.value.status_code == 409
    assert repo.saved is None  # no persistió


# ─── Lectura ──────────────────────────────────────────────────────────────────────

def test_get_empleado_existente():
    repo = _FakeRepo(); repo.by_id = _resp()
    assert _svc(repo).get_empleado(_ID).nombre == "Ana"


def test_get_empleado_inexistente_404():
    repo = _FakeRepo(); repo.by_id = None
    with pytest.raises(AppError) as e:
        _svc(repo).get_empleado(_ID)
    assert e.value.code == "EMPLEADO_NOT_FOUND" and e.value.status_code == 404


# ─── Update ───────────────────────────────────────────────────────────────────────

def test_update_solo_campos_provistos_y_audita():
    repo, audit = _FakeRepo(), _FakeAudit()
    repo.by_id = _resp()
    _svc(repo, audit).update_empleado(_ID, EmpleadoUpdate(nombre="Ana María"), _EMPRESA, "u1")
    _, data_arg = repo.updated
    # whitelist: solo el campo provisto viaja; los no-seteados no se cuelan
    assert data_arg.model_dump(exclude_none=True) == {"nombre": "Ana María"}
    assert [c["evento"] for c in audit.calls] == ["update_empleado"]


def test_update_inexistente_404():
    repo = _FakeRepo(); repo.update_returns = None  # repo.update no encontró la fila
    with pytest.raises(AppError) as e:
        _svc(repo).update_empleado(_ID, EmpleadoUpdate(nombre="X"), _EMPRESA, "u1")
    assert e.value.code == "EMPLEADO_NOT_FOUND" and e.value.status_code == 404


def test_update_legajo_duplicado_409_no_actualiza():
    repo = _FakeRepo()
    repo.legajo_existing = _resp(id="otro-id")
    with pytest.raises(AppError) as e:
        _svc(repo).update_empleado(_ID, EmpleadoUpdate(legajo="L-009"), _EMPRESA, "u1")
    assert e.value.code == "LEGAJO_DUPLICADO"
    assert repo.updated is None  # cortó antes de tocar el update


# ─── Superior inmediato (manager_id): asignar / anti-ciclos ─────────────────────────

def test_update_asignar_superior_sin_ciclo_ok():
    repo, audit = _FakeRepo(), _FakeAudit()
    repo.by_id = _resp()  # prior + eco del update (el editado cae a by_id)
    repo.by_id_map = {str(_B): _resp(id=str(_B), manager_id=None)}  # el superior no tiene manager → sin ciclo
    _svc(repo, audit).update_empleado(_ID, EmpleadoUpdate(manager_id=_B), _EMPRESA, "u1")
    _, data_arg = repo.updated
    assert str(data_arg.manager_id) == str(_B)
    assert [c["evento"] for c in audit.calls] == ["update_empleado"]


def test_update_autoreferencia_rechazada_400():
    repo = _FakeRepo(); repo.by_id = _resp()
    with pytest.raises(AppError) as e:  # un empleado no puede ser su propio superior
        _svc(repo).update_empleado(_ID, EmpleadoUpdate(manager_id=_ID), _EMPRESA, "u1")
    assert e.value.code == "MANAGER_CICLO" and e.value.status_code == 400
    assert repo.updated is None  # no persistió


def test_update_ciclo_directo_A_B_rechazado_400():
    # Editando A y asignándole a B como superior, con B ya teniendo a A como superior.
    repo = _FakeRepo(); repo.by_id = _resp()
    repo.by_id_map = {str(_B): _resp(id=str(_B), manager_id=str(_ID))}
    with pytest.raises(AppError) as e:
        _svc(repo).update_empleado(_ID, EmpleadoUpdate(manager_id=_B), _EMPRESA, "u1")
    assert e.value.code == "MANAGER_CICLO" and e.value.status_code == 400
    assert repo.updated is None


def test_update_ciclo_indirecto_A_B_C_A_rechazado_400():
    # A→B→C→A: asignar a A el superior B, con la cadena B→C y C→A ya existente.
    repo = _FakeRepo(); repo.by_id = _resp()
    repo.by_id_map = {
        str(_B): _resp(id=str(_B), manager_id=str(_C)),
        str(_C): _resp(id=str(_C), manager_id=str(_ID)),
    }
    with pytest.raises(AppError) as e:
        _svc(repo).update_empleado(_ID, EmpleadoUpdate(manager_id=_B), _EMPRESA, "u1")
    assert e.value.code == "MANAGER_CICLO" and e.value.status_code == 400
    assert repo.updated is None


# ─── Baja (soft delete) ───────────────────────────────────────────────────────────

def test_deactivate_marca_baja_y_audita():
    repo, audit = _FakeRepo(), _FakeAudit()
    repo.by_id = _resp()
    assert _svc(repo, audit).deactivate_empleado(_ID, _EMPRESA, "u1") is True
    assert repo.soft_deleted == str(_ID)
    assert [c["evento"] for c in audit.calls] == ["baja_empleado"]


def test_deactivate_inexistente_404():
    repo = _FakeRepo(); repo.soft_delete_returns = False
    with pytest.raises(AppError) as e:
        _svc(repo).deactivate_empleado(_ID, _EMPRESA, "u1")
    assert e.value.code == "EMPLEADO_NOT_FOUND" and e.value.status_code == 404


# ─── Listado paginado ─────────────────────────────────────────────────────────────

def test_get_empleados_pagina_y_reenvia_filtros():
    repo = _FakeRepo(); repo.find_all_returns = ([_resp(), _resp()], 25)
    out = _svc(repo).get_empleados(2, 10, _EMPRESA, "area-1", "activo", "ana", None)
    assert out.total == 25 and out.page == 2 and out.page_size == 10
    assert out.total_pages == 3  # ceil(25/10)
    assert repo.find_all_args["estado"] == "activo"
    assert repo.find_all_args["search"] == "ana"
    assert repo.find_all_args["area_id"] == "area-1"
