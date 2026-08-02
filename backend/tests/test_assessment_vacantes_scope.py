"""
Barrera de empresa en assessment (2) y en las integraciones externas de vacantes (3) — sin red.

  · assessment  POST /campanas/{campana_id}/links y GET /resultados/{resultado_id}.
                El 404 lo lanza el propio repo, así que el filtro va ahí y el mensaje no cambia.
                ⚠️ NO es código muerto: el router está montado (condicionado por
                ASSESSMENT_ENABLED) y usa assessment_campanas_repo / assessment_resultados_repo,
                que están vivos. El legacy sin callers era repositories/assessment_repo.py, que
                se BORRÓ el 2/8/2026 — apagado por flag no es lo mismo que muerto.
  · vacantes    publicar-linkedin, emails-candidatos y candidatos-desde-email delegaban en
                Zernio/Gmail con el id de vacante crudo. Es la fuga con peor consecuencia del
                lote: el dato sale del sistema hacia un tercero.

Zernio/Gmail instancian sus repos en __init__ sin inyección, así que acá se monkeypatchea la
clase VacanteRepo en cada módulo. El fake HONRA empresa_id.
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
from uuid import UUID, uuid4

import pytest

import services.gmail_service as gmail_mod
import services.zernio_service as zernio_mod
from services.assessment_service import AssessmentService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")
AJENO = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")

_EMPRESAS = {str(PROPIO): EMPRESA_A, str(AJENO): EMPRESA_B}


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── assessment ────────────────────────────────────────────────────────────────

class _CampanasRepo:
    """El 404 lo lanza el repo (como el real), así que el fake replica esa forma."""

    def __init__(self) -> None:
        self.links: list = []

    def get_campana(self, campana_id, empresa_id=None):
        emp = _EMPRESAS.get(str(campana_id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            raise AppError("Campaña no encontrada", "CAMPANA_NOT_FOUND", 404)
        return SimpleNamespace(id=str(campana_id), empresa_id=str(emp))

    def create_link(self, data):
        self.links.append(str(data.campana_id))
        return SimpleNamespace(id=str(uuid4()), token=str(uuid4()), evaluado_email="a@b.com")


class _ResultadosRepo:
    def get_resultado(self, resultado_id, empresa_id=None):
        emp = _EMPRESAS.get(str(resultado_id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            raise AppError("Resultado no encontrado", "RESULTADO_NOT_FOUND", 404)
        return SimpleNamespace(id=str(resultado_id), empresa_id=str(emp))


def _assess_svc(campanas=None):
    return AssessmentService(campanas_repo=campanas or _CampanasRepo(),
                             resultados_repo=_ResultadosRepo())


def _link(svc, campana_id, empresa=EMPRESA_A):
    return svc.create_link(SimpleNamespace(campana_id=campana_id), empresa)


def test_assessment_campana_ajena_404_y_no_crea_link():
    repo = _CampanasRepo()
    err = _error(lambda: _link(_assess_svc(repo), AJENO))
    assert err.code == "CAMPANA_NOT_FOUND" and err.status_code == 404
    assert repo.links == []


def test_assessment_campana_ajena_indistinguible_de_inexistente():
    ajeno = _error(lambda: _link(_assess_svc(), AJENO))
    inexistente = _error(lambda: _link(_assess_svc(), INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_assessment_campana_propia_y_consolidado():
    repo = _CampanasRepo()
    _link(_assess_svc(repo), PROPIO)
    _link(_assess_svc(repo), AJENO, empresa=None)   # consolidado no restringe
    assert repo.links == [str(PROPIO), str(AJENO)]


def test_assessment_resultado_ajeno_404_e_indistinguible():
    ajeno = _error(lambda: _assess_svc().get_resultado(AJENO, EMPRESA_A))
    inexistente = _error(lambda: _assess_svc().get_resultado(INEXISTENTE, EMPRESA_A))
    assert ajeno.code == "RESULTADO_NOT_FOUND" and ajeno.status_code == 404
    assert (ajeno.code, ajeno.message) == (inexistente.code, inexistente.message)


def test_assessment_resultado_propio_y_consolidado():
    assert _assess_svc().get_resultado(PROPIO, EMPRESA_A) is not None
    assert _assess_svc().get_resultado(AJENO, None) is not None


# ── vacantes → integraciones externas ─────────────────────────────────────────

class _VacanteRepo:
    """HONRA empresa_id, como el find_by_id real de vacante_repo."""

    def find_by_id(self, id, empresa_id=None):
        emp = _EMPRESAS.get(str(id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(id), empresa_id=str(emp), titulo="V",
                               model_dump=lambda: {"titulo": "V"})


class _IntegracionRepo:
    """Sin API key: si el gate de empresa NO cortara, el flujo seguiría hasta acá y fallaría con
    otro code. Que el test espere el 404 de vacante prueba que la barrera actuó primero."""

    def get_by_user_and_tipo(self, user_id, tipo):
        return None


@pytest.fixture
def _patch_repos(monkeypatch):
    for mod in (zernio_mod, gmail_mod):
        monkeypatch.setattr(mod, "VacanteRepo", _VacanteRepo)
        monkeypatch.setattr(mod, "IntegracionRepo", _IntegracionRepo)


def _zernio(vac_id, empresa=EMPRESA_A):
    return zernio_mod.ZernioService().publicar_en_vacante(str(vac_id), "a@b.com", "u1", empresa)


def _emails(vac_id, empresa=EMPRESA_A):
    return gmail_mod.GmailService().get_emails_candidatos(str(vac_id), "u1", empresa)


@pytest.mark.parametrize("llamar,code", [(_zernio, "ZERNIO_NOT_CONFIGURED"),
                                         (_emails, "VACANTE_NOT_FOUND")],
                         ids=["publicar_linkedin", "emails_candidatos"])
def test_vacante_ajena_no_llega_a_la_integracion(_patch_repos, llamar, code):
    """Con vacante ajena ninguna de las dos alcanza a Zernio/Gmail. publicar_linkedin corta antes
    por falta de API key (su orden original); emails_candidatos corta por el gate nuevo."""
    err = _error(lambda: llamar(AJENO))
    assert err.status_code in (400, 404) and err.code == code


def test_emails_candidatos_vacante_ajena_es_404(_patch_repos):
    err = _error(lambda: _emails(AJENO))
    assert err.code == "VACANTE_NOT_FOUND" and err.status_code == 404


def test_emails_candidatos_ajena_indistinguible_de_inexistente(_patch_repos):
    ajeno = _error(lambda: _emails(AJENO))
    inexistente = _error(lambda: _emails(INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_emails_candidatos_vacante_propia_pasa_el_gate(_patch_repos):
    """Con la vacante propia el gate deja pasar y el flujo avanza hasta Gmail, que sin
    credenciales corta con GMAIL_NOT_CONFIGURED — o sea: la barrera no lo frenó."""
    err = _error(lambda: _emails(PROPIO))
    assert err.code != "VACANTE_NOT_FOUND"


def test_emails_candidatos_consolidado_no_restringe(_patch_repos):
    err = _error(lambda: _emails(AJENO, empresa=None))
    assert err.code != "VACANTE_NOT_FOUND"
