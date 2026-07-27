"""
Validación de area_id contra la empresa del empleado — fakes, sin red.

Hermano de test_empleado_manager_empresa.py (Tanda 1) y último hueco del módulo: el WHERE de
empresa del UPDATE restringe QUÉ fila se toca, no QUÉ VALOR se escribe, así que sin este gate un
empleado quedaba apuntando a un área de otra empresa. Las áreas son POR EMPRESA (schema.sql), y
el área alimenta listados y reportes: un area_id cruzado hace aparecer al empleado bajo el área
de otra organización.

Se pudo cerrar recién ahora porque area_repo.find_by_id no aceptaba empresa_id hasta esta sesión.

⚠️ El fake de ÁREA honra empresa_id; el de EMPLEADO es permisivo a propósito (el eje bajo
prueba acá es el área, no el empleado). Los otros archivos de empleados usan un _AreaRepoPermisivo
a propósito (prueban otras cosas); el único que valida este eje es este.
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
AREA_PROPIA = UUID("22222222-2222-2222-2222-222222222222")   # empresa A
AREA_AJENA = UUID("33333333-3333-3333-3333-333333333333")    # empresa B
AREA_INEXISTENTE = UUID("44444444-4444-4444-4444-444444444444")

_AREAS = {str(AREA_PROPIA): EMPRESA_A, str(AREA_AJENA): EMPRESA_B}


def _resp(id_: UUID, empresa_id: UUID) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": "n@k.com",
        "empresa_id": str(empresa_id), "area_id": str(AREA_PROPIA),
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


def _create(**over) -> EmpleadoCreate:
    base = dict(nombre="N", apellido="A", email_corporativo="n@k.com", area_id=AREA_PROPIA,
                roles=["Analista"], tipo_contrato="efectivo", fecha_ingreso=date(2024, 1, 1),
                empresa_id=EMPRESA_A)
    base.update(over)
    return EmpleadoCreate(**base)


class _EmpRepo:
    def __init__(self) -> None:
        self.guardado = None
        self.actualizado = None

    def find_by_id(self, id, empresa_id=None):
        return _resp(EMPLEADO, EMPRESA_A)

    def find_by_legajo(self, legajo, empresa_id):
        return None

    def save(self, data, empresa_id):
        self.guardado = (data, empresa_id)
        return _resp(EMPLEADO, empresa_id)

    def update(self, id, data, empresa_id=None):
        self.actualizado = (id, data)
        return _resp(EMPLEADO, EMPRESA_A)

    def soft_delete(self, id, empresa_id=None):
        return True


class _AreaRepo:
    """HONRA empresa_id: None si el área es de otra empresa (como el find_by_id real)."""

    def __init__(self) -> None:
        self.consultas: list = []

    def find_by_id(self, id, empresa_id=None):
        self.consultas.append((str(id), empresa_id))
        emp = _AREAS.get(str(id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(id), empresa_id=str(emp))


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


def _svc(emp_repo=None, area_repo=None):
    return EmpleadoService(repo=emp_repo or _EmpRepo(), audit=_Audit(),
                           area_repo=area_repo or _AreaRepo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def _crear(svc, area_id, empresa=EMPRESA_A):
    return svc.create_empleado(_create(area_id=area_id), "u1", empresa)


def _actualizar(svc, area_id, empresa=EMPRESA_A):
    return svc.update_empleado(EMPLEADO, EmpleadoUpdate(area_id=area_id), empresa, "u1")


_OPS = [_crear, _actualizar]
_IDS = ["create", "update"]


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_area_de_otra_empresa_404(llamar):
    err = _error(lambda: llamar(_svc(), AREA_AJENA))
    assert err.code == "AREA_NOT_FOUND" and err.status_code == 404


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_area_ajena_indistinguible_de_inexistente(llamar):
    ajena = _error(lambda: llamar(_svc(), AREA_AJENA))
    inexistente = _error(lambda: llamar(_svc(), AREA_INEXISTENTE))
    assert (ajena.code, ajena.message, ajena.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_area_propia_camino_feliz(llamar):
    assert llamar(_svc(), AREA_PROPIA) is not None


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_consolidado_no_restringe(llamar):
    assert llamar(_svc(), AREA_AJENA, empresa=None) is not None


def test_no_persiste_con_area_ajena():
    """El gate corta antes de escribir, en alta y en edición."""
    emp = _EmpRepo()
    _error(lambda: _crear(_svc(emp), AREA_AJENA))
    assert emp.guardado is None
    emp2 = _EmpRepo()
    _error(lambda: _actualizar(_svc(emp2), AREA_AJENA))
    assert emp2.actualizado is None


def test_update_area_null_no_valida_ni_consulta():
    """area_id=None en un update parcial = 'no se toca el área': el guard corta en el helper."""
    areas = _AreaRepo()
    emp = _EmpRepo()
    _svc(emp, areas).update_empleado(EMPLEADO, EmpleadoUpdate(nombre="X"), EMPRESA_A, "u1")
    assert areas.consultas == []      # ni una consulta al repo de áreas
    assert emp.actualizado is not None  # y el update ocurrió igual
