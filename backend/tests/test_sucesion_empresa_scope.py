"""
Tests de la barrera de empresa sobre el empleado target de un plan de carrera — fakes, sin red.
Primer test del módulo: SucesionService no tenía ninguno.

`POST /api/sucesion/planes` recibe el empleado_id por BODY. La empresa del plan se hereda del
empleado (decisión de diseño documentada, no se toca); lo que se valida acá es a QUÉ empleado
se puede apuntar. Sin la barrera se le creaba un plan de carrera a un empleado de otra empresa,
y el plan quedaba colgando de la empresa ajena.

⚠️ El fake de acá SÍ honra empresa_id en find_by_id: modela dos empresas y devuelve None
cuando no coincide, como el _with_empresa real. NO calcar los fakes de vacaciones
(test_escrituras_ownership.py:98, test_audit_instrumentacion.py:71) ni el _FakeRepo de
empleados (test_empleado_service.py:97): todos aceptan empresa_id y lo ignoran, así que estos
tests pasarían en verde sin validar nada.
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

from uuid import UUID, uuid4

import pytest

from schemas.empleado import EmpleadoResponse
from schemas.sucesion import PlanCarreraCreate, PlanCarreraResponse
from services.sucesion_service import SucesionService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
EMP_PROPIO = UUID("11111111-1111-1111-1111-111111111111")   # empresa A
EMP_AJENO = UUID("22222222-2222-2222-2222-222222222222")    # empresa B
EMP_INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")


def _empleado(id_: UUID, empresa_id: UUID) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": "n@k.com",
        "empresa_id": str(empresa_id), "area_id": "44444444-4444-4444-4444-444444444444",
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


class _EmpleadoRepo:
    """HONRA empresa_id: None si el empleado es de otra empresa (como _with_empresa)."""

    def __init__(self) -> None:
        self._emp = {
            str(EMP_PROPIO): _empleado(EMP_PROPIO, EMPRESA_A),
            str(EMP_AJENO): _empleado(EMP_AJENO, EMPRESA_B),
        }

    def find_by_id(self, id, empresa_id=None):
        emp = self._emp.get(str(id))
        if not emp or (empresa_id and str(emp.empresa_id) != str(empresa_id)):
            return None
        return emp


class _PlanesRepo:
    def __init__(self) -> None:
        self.creados: list = []

    def get_plan_by_empleado(self, empleado_id):
        return None  # sin plan activo previo

    def create_plan(self, data, empresa_id) -> PlanCarreraResponse:
        self.creados.append((str(data.empleado_id), empresa_id))
        return PlanCarreraResponse.model_validate({
            "id": str(uuid4()), "empleado_id": str(data.empleado_id),
            "empresa_id": empresa_id or None, "empleado_nombre": "N A",
            "cargo_objetivo": data.cargo_objetivo, "readiness": data.readiness,
            "hitos_completados": 0, "hitos_total": 0,
        })


def _svc(emp_repo, planes_repo):
    return SucesionService(planes_repo=planes_repo, empleado_repo=emp_repo)


def _body(empleado_id: UUID) -> PlanCarreraCreate:
    return PlanCarreraCreate(empleado_id=empleado_id, cargo_objetivo="Jefe de Área")


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def test_empleado_de_otra_empresa_404_y_no_crea_plan():
    planes = _PlanesRepo()
    err = _error(lambda: _svc(_EmpleadoRepo(), planes)
                 .create_plan_carrera(_body(EMP_AJENO), EMPRESA_A))
    assert err.code == "EMPLEADO_NOT_FOUND" and err.status_code == 404
    assert planes.creados == []


def test_empleado_ajeno_es_indistinguible_del_inexistente():
    """No confirma la existencia de empleados de otra empresa: mismo code, mensaje y status."""
    ajeno = _error(lambda: _svc(_EmpleadoRepo(), _PlanesRepo())
                   .create_plan_carrera(_body(EMP_AJENO), EMPRESA_A))
    inexistente = _error(lambda: _svc(_EmpleadoRepo(), _PlanesRepo())
                         .create_plan_carrera(_body(EMP_INEXISTENTE), EMPRESA_A))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_empleado_propio_camino_feliz():
    planes = _PlanesRepo()
    out = _svc(_EmpleadoRepo(), planes).create_plan_carrera(_body(EMP_PROPIO), EMPRESA_A)
    assert str(out.empleado_id) == str(EMP_PROPIO)
    # la empresa del plan sigue heredándose del empleado, no del header
    assert planes.creados == [(str(EMP_PROPIO), str(EMPRESA_A))]


def test_empresa_none_es_consolidado_y_no_restringe():
    """None = 'Todas las empresas': el empleado de la otra empresa se puede planificar."""
    planes = _PlanesRepo()
    out = _svc(_EmpleadoRepo(), planes).create_plan_carrera(_body(EMP_AJENO), None)
    assert str(out.empleado_id) == str(EMP_AJENO)
    assert planes.creados == [(str(EMP_AJENO), str(EMPRESA_B))]  # empresa derivada del empleado
