"""
Tests de la barrera de empresa sobre el empleado target de offboarding — fakes, sin red.
Primer test del módulo: OffboardingService no tenía ninguno.

`POST /api/offboarding` recibe el empleado_id por BODY. La empresa en la que se escribe se
deriva del empleado (decisión de diseño documentada, no se toca); lo que se valida acá es a
QUÉ empleado se puede apuntar. Sin la barrera, un empleado_id de otra empresa arrancaba su
offboarding.

⚠️ Este encabezado decía además "y —peor— le disparaba la baja (dar_de_baja, que se acota con la
empresa DERIVADA del propio empleado ajeno, así que no lo frenaba)". **Eso dejó de ser cierto**:
iniciar un offboarding ya no da de baja a nadie — la baja se efectiviza aparte. Los asserts sobre
`bajas` se conservan igual de vivos, pero ahora afirman lo contrario: que sigue en `[]` también en
el camino feliz. Ver `test_empleado_propio_camino_feliz`.

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
from schemas.offboarding import OffboardingCreate, OffboardingResponse
from services.offboarding_service import OffboardingService
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
        self.bajas: list = []

    def find_by_id(self, id, empresa_id=None):
        emp = self._emp.get(str(id))
        if not emp or (empresa_id and str(emp.empresa_id) != str(empresa_id)):
            return None
        return emp

    def dar_de_baja(self, empleado_id, fecha_egreso, empresa_id=None, motivo=None):
        self.bajas.append(str(empleado_id))
        return True


class _OffRepo:
    def __init__(self) -> None:
        self.creados: list = []

    def find_by_empleado(self, empleado_id, empresa_id=None):
        return None  # sin offboarding activo previo

    def create_offboarding(self, data, empresa_id) -> OffboardingResponse:
        self.creados.append((str(data.empleado_id), empresa_id))
        return OffboardingResponse.model_validate({
            "id": str(uuid4()), "empleado_id": str(data.empleado_id),
            "empresa_id": empresa_id or None, "empleado_nombre": "N A",
            "motivo": data.motivo, "estado": "en_proceso",
            "fecha_inicio": "2026-07-26", "progreso": 0,
        })


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


def _svc(emp_repo, off_repo):
    return OffboardingService(repo=off_repo, empleado_repo=emp_repo, audit=_Audit())


def _body(empleado_id: UUID) -> OffboardingCreate:
    return OffboardingCreate(empleado_id=empleado_id, motivo="renuncia")


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def test_empleado_de_otra_empresa_404_y_no_crea_ni_da_de_baja():
    emp, off = _EmpleadoRepo(), _OffRepo()
    err = _error(lambda: _svc(emp, off).iniciar_offboarding(_body(EMP_AJENO), EMPRESA_A, "u1"))
    assert err.code == "EMPLEADO_NOT_FOUND" and err.status_code == 404
    assert off.creados == []   # no arrancó el offboarding
    assert emp.bajas == []     # y no lo dio de baja (el riesgo real de este endpoint)


def test_empleado_ajeno_es_indistinguible_del_inexistente():
    """No confirma la existencia de empleados de otra empresa: mismo code, mensaje y status."""
    ajeno = _error(lambda: _svc(_EmpleadoRepo(), _OffRepo())
                   .iniciar_offboarding(_body(EMP_AJENO), EMPRESA_A, "u1"))
    inexistente = _error(lambda: _svc(_EmpleadoRepo(), _OffRepo())
                         .iniciar_offboarding(_body(EMP_INEXISTENTE), EMPRESA_A, "u1"))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_empleado_propio_camino_feliz():
    emp, off = _EmpleadoRepo(), _OffRepo()
    out = _svc(emp, off).iniciar_offboarding(_body(EMP_PROPIO), EMPRESA_A, "u1")
    assert str(out.empleado_id) == str(EMP_PROPIO)
    # la empresa en la que se escribe sigue derivándose del empleado, no del header
    assert off.creados == [(str(EMP_PROPIO), str(EMPRESA_A))]
    # 🔴 CAMBIÓ DE SENTIDO: antes esto afirmaba `== [str(EMP_PROPIO)]`, o sea que iniciar el
    # trámite daba de baja al empleado en el acto. Ese era EL BUG. Ahora el camino feliz NO toca
    # al empleado: la baja la escribe `POST /{id}/efectivizar`, y esta línea es lo que impide que
    # alguien la reponga sin darse cuenta.
    assert emp.bajas == []


def test_empresa_none_es_consolidado_y_no_restringe():
    """None = 'Todas las empresas': el empleado de la otra empresa se puede procesar."""
    emp, off = _EmpleadoRepo(), _OffRepo()
    out = _svc(emp, off).iniciar_offboarding(_body(EMP_AJENO), None, "u1")
    assert str(out.empleado_id) == str(EMP_AJENO)
    assert off.creados == [(str(EMP_AJENO), str(EMPRESA_B))]  # empresa derivada del empleado
