"""
Tests de la validación de superior (manager_id) contra la empresa del empleado — fakes, sin red.

El WHERE de empresa del UPDATE restringe QUÉ fila se toca, no QUÉ VALOR se escribe: sin
ensure_manager_valido entra igual un manager_id de otra empresa. Importa más allá del
organigrama —el ownership de mandos_medios se resuelve por manager_id, así que un superior
cruzado haría que ids_subordinados atraviese la frontera de empresa—.

Cubre alta y edición: superior ajeno → 404 MANAGER_NOT_FOUND idéntico al del inexistente (no
confirma la existencia de empleados de otra empresa), superior propio → ok, null → ok sin
validar, y que los anti-ciclos intra-empresa siguen detectándose y ahora recorren la cadena
acotados a la empresa.

⚠️ El fake de acá SÍ honra empresa_id en find_by_id — el de test_empleado_service.py la ignora
(devuelve la misma fila siempre), así que con aquel estos tests pasarían sin validar nada.
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
from uuid import UUID, uuid4

import pytest

from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from services.empleado_service import EmpleadoService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
EMPLEADO = UUID("11111111-1111-1111-1111-111111111111")
MGR_PROPIO = UUID("22222222-2222-2222-2222-222222222222")   # empresa A
MGR_AJENO = UUID("33333333-3333-3333-3333-333333333333")    # empresa B
MGR_INEXISTENTE = UUID("44444444-4444-4444-4444-444444444444")
INTERMEDIO = UUID("55555555-5555-5555-5555-555555555555")   # empresa A, para el ciclo indirecto


def _resp(id_: UUID, empresa_id: UUID, manager_id=None) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": "n@k.com",
        "empresa_id": str(empresa_id), "area_id": "22222222-2222-2222-2222-222222222222",
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
        "manager_id": str(manager_id) if manager_id else None,
    })


def _create(**over) -> EmpleadoCreate:
    base = dict(nombre="N", apellido="A", email_corporativo="n@k.com",
                area_id=UUID("22222222-2222-2222-2222-222222222222"), roles=["Analista"],
                tipo_contrato="efectivo", fecha_ingreso=date(2024, 1, 1), empresa_id=EMPRESA_A)
    base.update(over)
    return EmpleadoCreate(**base)


class _Repo:
    """Repo fake que HONRA empresa_id: find_by_id devuelve None si el empleado es de otra
    empresa, igual que el _with_empresa real. Registra los empresa_id recibidos."""

    def __init__(self, extra: dict | None = None) -> None:
        self._emp = {
            str(EMPLEADO): _resp(EMPLEADO, EMPRESA_A),
            str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A),
            str(MGR_AJENO): _resp(MGR_AJENO, EMPRESA_B),
        }
        self._emp.update(extra or {})
        self.guardado = None
        self.actualizado = None
        self.empresas_recibidas: list = []  # empresa_id de cada find_by_id

    def find_by_id(self, id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        emp = self._emp.get(str(id))
        if not emp or (empresa_id and str(emp.empresa_id) != str(empresa_id)):
            return None
        return emp

    def find_by_legajo(self, legajo, empresa_id):
        return None

    def save(self, data, empresa_id):
        self.guardado = (data, empresa_id)
        return _resp(EMPLEADO, empresa_id)

    def update(self, id, data, empresa_id=None):
        self.actualizado = (id, data)
        return _resp(EMPLEADO, EMPRESA_A, data.manager_id)

    def soft_delete(self, id, empresa_id=None):
        return True


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


class _AreaRepoPermisivo:
    """area_repo fake permisivo: este archivo prueba el gate de MANAGER, no el de área
    (ese vive en test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


def _svc(repo) -> EmpleadoService:
    return EmpleadoService(repo=repo, audit=_Audit(), area_repo=_AreaRepoPermisivo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── PUT /empleados/{id} ───────────────────────────────────────────────────────

def test_update_manager_de_otra_empresa_404_y_no_persiste():
    repo = _Repo()
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_AJENO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_NOT_FOUND" and err.status_code == 404
    assert repo.actualizado is None  # cortó antes de escribir


def test_update_manager_ajeno_es_indistinguible_del_inexistente():
    """No debe confirmar que el superior existe en otra empresa: mismo code, mensaje y status."""
    ajeno = _error(lambda: _svc(_Repo()).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_AJENO), EMPRESA_A, "u1"))
    inexistente = _error(lambda: _svc(_Repo()).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_INEXISTENTE), EMPRESA_A, "u1"))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_update_manager_de_la_misma_empresa_ok():
    repo = _Repo()
    out = _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1")
    assert str(out.manager_id) == str(MGR_PROPIO)
    assert repo.actualizado is not None


def test_update_manager_null_no_valida_y_persiste():
    """manager_id=None = 'sin superior': el guard corta en ensure_manager_valido, no consulta."""
    repo = _Repo()
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=None), EMPRESA_A, "u1")
    assert repo.actualizado is not None
    # el único find_by_id es el `prior` del audit — ni validación de manager ni recorrido de ciclos
    assert len(repo.empresas_recibidas) == 1


def test_update_empresa_none_es_consolidado_y_no_restringe():
    """empresa_id None ('Todas las empresas'): cualquier empleado existente sirve de superior."""
    repo = _Repo()
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=MGR_AJENO), None, "u1")
    assert repo.actualizado is not None


# ── Anti-ciclos: siguen detectándose, ahora acotados a la empresa ─────────────

def test_ciclo_directo_intra_empresa_sigue_rechazado():
    """A→B con B→A ya existente. El manager es válido (misma empresa): lo frena el ciclo, no la empresa."""
    repo = _Repo({str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=EMPLEADO)})
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400
    assert repo.actualizado is None


def test_ciclo_indirecto_intra_empresa_sigue_rechazado():
    """A→B→C→A: la cadena se recorre entera y detecta el circuito."""
    repo = _Repo({
        str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=INTERMEDIO),
        str(INTERMEDIO): _resp(INTERMEDIO, EMPRESA_A, manager_id=EMPLEADO),
    })
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400


def test_autorreferencia_sigue_rechazada():
    repo = _Repo()
    err = _error(lambda: _svc(repo).update_empleado(
        EMPLEADO, EmpleadoUpdate(manager_id=EMPLEADO), EMPRESA_A, "u1"))
    assert err.code == "MANAGER_CICLO" and err.status_code == 400


def test_el_recorrido_de_ciclos_va_acotado_a_la_empresa():
    """La cadena de managers ya no se recorre global: cada salto lleva el empresa_id."""
    repo = _Repo({str(MGR_PROPIO): _resp(MGR_PROPIO, EMPRESA_A, manager_id=INTERMEDIO),
                  str(INTERMEDIO): _resp(INTERMEDIO, EMPRESA_A)})
    _svc(repo).update_empleado(EMPLEADO, EmpleadoUpdate(manager_id=MGR_PROPIO), EMPRESA_A, "u1")
    assert repo.empresas_recibidas and all(e == EMPRESA_A for e in repo.empresas_recibidas)


# ── POST /empleados ───────────────────────────────────────────────────────────

def test_create_manager_de_otra_empresa_404_y_no_guarda():
    repo = _Repo()
    err = _error(lambda: _svc(repo).create_empleado(
        _create(manager_id=MGR_AJENO), "u1", EMPRESA_A))
    assert err.code == "MANAGER_NOT_FOUND" and err.status_code == 404
    assert repo.guardado is None


def test_create_manager_ajeno_es_indistinguible_del_inexistente():
    ajeno = _error(lambda: _svc(_Repo()).create_empleado(
        _create(manager_id=MGR_AJENO), "u1", EMPRESA_A))
    inexistente = _error(lambda: _svc(_Repo()).create_empleado(
        _create(manager_id=MGR_INEXISTENTE), "u1", EMPRESA_A))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_create_manager_de_la_misma_empresa_guarda():
    repo = _Repo()
    _svc(repo).create_empleado(_create(manager_id=MGR_PROPIO), "u1", EMPRESA_A)
    assert repo.guardado is not None and repo.guardado[1] == EMPRESA_A


def test_create_manager_null_no_valida_y_guarda():
    repo = _Repo()
    _svc(repo).create_empleado(_create(), "u1", EMPRESA_A)
    assert repo.guardado is not None
    assert repo.empresas_recibidas == []  # el guard cortó: ni una consulta
