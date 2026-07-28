"""
Tests de la barrera de empresa sobre el empleado target de onboarding — fakes, sin red.
Primer test del módulo: OnboardingService no tenía ninguno.

`POST /onboarding/{empleado_id}/iniciar` recibe el empleado_id por PATH y el router no tomaba
Request, así que no había forma de acotar a qué empleado se apuntaba: se le arrancaba el
onboarding a un empleado de cualquier empresa.

Ownership de rol NO se testea acá y no es un olvido: Seccion.ONBOARDING no está en
MANDOS_MEDIOS_SECCIONES (utils/permisos.py:68), así que mandos_medios recibe 403 en el gate del
router y nunca llega al service. Solo entran admin_rrhh y gerencia_lectura, para quienes
ids_empleados_visibles devuelve None (sin restricción). Por eso el service usa
ensure_empleado_de_empresa y no ensure_empleado_visible, a diferencia de vacaciones.

⚠️ _TemplatesRepo.get_template y _OnbRepo.get_default_template son permisivos a propósito
(aceptan empresa_id, user_id y rol y no los usan): el eje bajo prueba es el EMPLEADO. La empresa de
la plantilla la cubre test_onboarding_templates_scope.py y la visibilidad
test_onboarding_template_visibilidad.py, cada uno con un fake que sí honra su eje.
El gate de templates se cubre en test_onboarding_templates_scope.py.
⚠️ El fake de empleado SÍ honra empresa_id en find_by_id: dos empresas, None cuando no coincide, como
el _with_empresa real. NO calcar los que lo aceptan y lo ignoran (test_empleado_service.py:97,
test_escrituras_ownership.py:98, test_audit_instrumentacion.py:71) — darían verde sin validar.
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
from schemas.onboarding import InstanciaResponse, TemplateResponse
from services.onboarding_service import OnboardingService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")     # empresa A
AJENO = UUID("22222222-2222-2222-2222-222222222222")      # empresa B
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
TEMPLATE_A = UUID("44444444-4444-4444-4444-444444444444")
TEMPLATE_B = UUID("55555555-5555-5555-5555-555555555555")


def _empleado(id_: UUID, empresa_id: UUID) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": "n@k.com",
        "empresa_id": str(empresa_id), "area_id": "66666666-6666-6666-6666-666666666666",
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


def _template(id_: UUID, empresa_id: UUID) -> TemplateResponse:
    return TemplateResponse.model_validate({
        "id": str(id_), "nombre": "Template", "empresa_id": str(empresa_id),
    })


class _EmpleadoRepo:
    """HONRA empresa_id: None si el empleado es de otra empresa (como _with_empresa)."""

    def __init__(self) -> None:
        self._emp = {
            str(PROPIO): _empleado(PROPIO, EMPRESA_A),
            str(AJENO): _empleado(AJENO, EMPRESA_B),
        }

    def find_by_id(self, id, empresa_id=None):
        emp = self._emp.get(str(id))
        if not emp or (empresa_id and str(emp.empresa_id) != str(empresa_id)):
            return None
        return emp


class _OnbRepo:
    """El template por defecto sale de la empresa del empleado, como el repo real."""

    def __init__(self, con_instancia_activa: bool = False) -> None:
        self._activa = con_instancia_activa
        self.creadas: list = []

    def find_instancia_by_empleado(self, empleado_id, empresa_id=None):
        return object() if self._activa else None

    def get_default_template(self, empresa_id=None, user_id=None, rol=None):
        return _template(TEMPLATE_A if str(empresa_id) == str(EMPRESA_A) else TEMPLATE_B,
                         empresa_id or EMPRESA_A)

    def create_instancia(self, empleado_id, template_id, empresa_id) -> InstanciaResponse:
        self.creadas.append((str(empleado_id), empresa_id))
        return InstanciaResponse.model_validate({
            "id": str(uuid4()), "empleado_id": str(empleado_id), "empresa_id": empresa_id or None,
            "empleado_nombre": "N A", "template_id": str(template_id), "estado": "en_proceso",
            "fecha_inicio": "2026-07-26", "progreso": 0, "tareas_completadas": 0,
            "tareas_total": 0,
        })


class _TemplatesRepo:
    def get_template(self, template_id, empresa_id=None, user_id=None, rol=None):
        return _template(UUID(str(template_id)), EMPRESA_A)


def _svc(onb_repo=None, emp_repo=None):
    return OnboardingService(repo=onb_repo or _OnbRepo(), templates_repo=_TemplatesRepo(),
                             empleado_repo=emp_repo or _EmpleadoRepo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def test_empleado_de_otra_empresa_404_y_no_crea_instancia():
    onb = _OnbRepo()
    err = _error(lambda: _svc(onb).iniciar_onboarding(AJENO, None, EMPRESA_A))
    assert err.code == "EMPLEADO_NOT_FOUND" and err.status_code == 404
    assert onb.creadas == []


def test_empleado_ajeno_es_indistinguible_del_inexistente():
    """No confirma la existencia de empleados de otra empresa: mismo code, mensaje y status."""
    ajeno = _error(lambda: _svc().iniciar_onboarding(AJENO, None, EMPRESA_A))
    inexistente = _error(lambda: _svc().iniciar_onboarding(INEXISTENTE, None, EMPRESA_A))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_empleado_ajeno_con_onboarding_activo_igual_da_404_no_409():
    """El gate va ANTES del chequeo de instancia activa: si fuera después, un empleado ajeno con
    onboarding en curso respondería 409 y delataría su existencia."""
    err = _error(lambda: _svc(_OnbRepo(con_instancia_activa=True))
                 .iniciar_onboarding(AJENO, None, EMPRESA_A))
    assert err.code == "EMPLEADO_NOT_FOUND" and err.status_code == 404


def test_empleado_propio_camino_feliz():
    onb = _OnbRepo()
    out = _svc(onb).iniciar_onboarding(PROPIO, None, EMPRESA_A)
    assert str(out.empleado_id) == str(PROPIO)
    # la empresa de la instancia se sigue derivando del empleado, no del header
    assert onb.creadas == [(str(PROPIO), str(EMPRESA_A))]


def test_empresa_none_es_consolidado_y_no_restringe():
    """None = 'Todas las empresas': el empleado de la otra empresa se puede onboardear."""
    onb = _OnbRepo()
    out = _svc(onb).iniciar_onboarding(AJENO, None, None)
    assert str(out.empleado_id) == str(AJENO)
    assert onb.creadas == [(str(AJENO), str(EMPRESA_B))]  # empresa derivada del empleado


def test_onboarding_activo_del_empleado_propio_sigue_dando_409():
    """El 409 de unicidad no se pierde por haber movido el gate arriba."""
    err = _error(lambda: _svc(_OnbRepo(con_instancia_activa=True))
                 .iniciar_onboarding(PROPIO, None, EMPRESA_A))
    assert err.code == "ONBOARDING_ALREADY_ACTIVE" and err.status_code == 409
