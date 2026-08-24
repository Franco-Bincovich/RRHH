"""
Barrera de empresa en los 4 endpoints de hitos/readiness de sucesión — fakes, sin red.

Los hitos se alcanzan por plan_id (get_hitos, create_hito, update_readiness), así que la barrera
va sobre el PLAN; completar_hito entra por hito_id y el hito lleva empresa_id propio, así que ahí
el filtro va en el WHERE del update.

Bug extra que cierra create_hito: antes, un plan inexistente o ajeno caía en empresa_id_str=""
y creaba el hito igual, huérfano de empresa. Ahora corta con 404.

⚠️ El fake HONRA empresa_id. No calcar los que la aceptan y la ignoran (test_empleado_service.py:97,
test_escrituras_ownership.py:98): darían verde sin validar nada.
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

from schemas.sucesion import HitoBodyCreate, HitoResponse, PlanCarreraResponse
from services.sucesion_service import SucesionService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PLAN_PROPIO = UUID("11111111-1111-1111-1111-111111111111")
PLAN_AJENO = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
HITO_PROPIO = UUID("44444444-4444-4444-4444-444444444444")
HITO_AJENO = UUID("55555555-5555-5555-5555-555555555555")


def _plan(id_: UUID, empresa_id: UUID) -> PlanCarreraResponse:
    return PlanCarreraResponse.model_validate({
        "id": str(id_), "empleado_id": str(uuid4()), "empresa_id": str(empresa_id),
        "empleado_nombre": "N A", "cargo_objetivo": "Jefe", "readiness": 0,
        "hitos_completados": 0, "hitos_total": 0,
    })


class _PlanesRepo:
    """HONRA empresa_id en get_plan_by_id y en el WHERE de completar_hito."""

    def __init__(self) -> None:
        self._planes = {str(PLAN_PROPIO): _plan(PLAN_PROPIO, EMPRESA_A),
                        str(PLAN_AJENO): _plan(PLAN_AJENO, EMPRESA_B)}
        self._hitos = {str(HITO_PROPIO): EMPRESA_A, str(HITO_AJENO): EMPRESA_B}
        self.creados: list = []
        self.readiness_aplicado: list = []

    def get_plan_by_id(self, plan_id, empresa_id=None):
        plan = self._planes.get(str(plan_id))
        if not plan or (empresa_id and str(plan.empresa_id) != str(empresa_id)):
            return None
        return plan

    def get_hitos(self, plan_id):
        return []

    # `tipo` con default, igual que el repo real: la columna es NOT NULL sin default en la
    # base, así que el service SIEMPRE lo manda (ver `schemas/sucesion.HitoBodyCreate`).
    def create_hito(self, plan_id, titulo, descripcion, fecha_objetivo, empresa_id,
                    tipo="otro") -> HitoResponse:
        self.creados.append((str(plan_id), empresa_id))
        return HitoResponse.model_validate({
            "id": str(uuid4()), "plan_id": str(plan_id), "titulo": titulo,
            "descripcion": descripcion, "completado": False, "fecha_objetivo": fecha_objetivo,
        })

    def completar_hito(self, hito_id, empresa_id=None):
        emp = self._hitos.get(str(hito_id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return False
        return True

    def update_readiness(self, plan_id, readiness):
        self.readiness_aplicado.append(str(plan_id))
        return self._planes[str(plan_id)]


def _svc(repo=None):
    return SucesionService(planes_repo=repo or _PlanesRepo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def _get_hitos(svc, plan_id, empresa=EMPRESA_A):
    return svc.get_hitos(plan_id, empresa)


def _create_hito(svc, plan_id, empresa=EMPRESA_A):
    return svc.create_hito(plan_id, HitoBodyCreate(titulo="H"), empresa)


def _readiness(svc, plan_id, empresa=EMPRESA_A):
    return svc.update_readiness(plan_id, 50, empresa)


_POR_PLAN = [_get_hitos, _create_hito, _readiness]
_IDS = ["get_hitos", "create_hito", "update_readiness"]


@pytest.mark.parametrize("llamar", _POR_PLAN, ids=_IDS)
def test_plan_de_otra_empresa_404(llamar):
    err = _error(lambda: llamar(_svc(), PLAN_AJENO))
    assert err.code == "PLAN_NOT_FOUND" and err.status_code == 404


@pytest.mark.parametrize("llamar", _POR_PLAN, ids=_IDS)
def test_plan_ajeno_indistinguible_del_inexistente(llamar):
    ajeno = _error(lambda: llamar(_svc(), PLAN_AJENO))
    inexistente = _error(lambda: llamar(_svc(), INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("llamar", _POR_PLAN, ids=_IDS)
def test_plan_propio_camino_feliz(llamar):
    assert llamar(_svc(), PLAN_PROPIO) is not None


@pytest.mark.parametrize("llamar", _POR_PLAN, ids=_IDS)
def test_consolidado_no_restringe(llamar):
    assert llamar(_svc(), PLAN_AJENO, empresa=None) is not None


def test_create_hito_no_escribe_si_el_plan_es_ajeno():
    """Antes creaba el hito con empresa_id='' (huérfano) en vez de cortar."""
    repo = _PlanesRepo()
    _error(lambda: _create_hito(_svc(repo), PLAN_AJENO))
    assert repo.creados == []


def test_create_hito_hereda_la_empresa_del_plan():
    repo = _PlanesRepo()
    _create_hito(_svc(repo), PLAN_PROPIO)
    assert repo.creados == [(str(PLAN_PROPIO), str(EMPRESA_A))]


def test_readiness_no_escribe_si_el_plan_es_ajeno():
    repo = _PlanesRepo()
    _error(lambda: _readiness(_svc(repo), PLAN_AJENO))
    assert repo.readiness_aplicado == []


# ── completar_hito: entra por hito_id, filtro en el WHERE ─────────────────────

def test_hito_de_otra_empresa_404():
    err = _error(lambda: _svc().completar_hito(HITO_AJENO, EMPRESA_A))
    assert err.code == "HITO_NOT_FOUND" and err.status_code == 404


def test_hito_ajeno_indistinguible_del_inexistente():
    ajeno = _error(lambda: _svc().completar_hito(HITO_AJENO, EMPRESA_A))
    inexistente = _error(lambda: _svc().completar_hito(INEXISTENTE, EMPRESA_A))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_hito_propio_camino_feliz():
    assert _svc().completar_hito(HITO_PROPIO, EMPRESA_A) is True


def test_hito_consolidado_no_restringe():
    assert _svc().completar_hito(HITO_AJENO, None) is True
