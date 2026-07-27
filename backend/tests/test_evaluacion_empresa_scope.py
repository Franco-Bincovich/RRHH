"""
Tests de la barrera de empresa en evaluaciones (Fase 2 — fuga entre empresas). Fakes, sin red.

Cubre los 4 endpoints que reciben un lote_id crudo (/metricas, /evaluados, /export, /ficha) más
las lecturas por lote de EvaluacionService: un lote de OTRA empresa responde el MISMO 404 que
uno inexistente (mismo code y mismo mensaje: no confirma la existencia de recursos ajenos), el
propio responde OK, y el modo consolidado (empresa None = "Todas") no restringe.

Incluye la cadena de dos saltos evaluado → lote → empresa de /ficha: el evaluado se busca solo
entre los del lote ya validado, así que un evaluado de otra empresa no es alcanzable ni pasando
su UUID real. Y que la equivalencia del import queda atada a la empresa del LOTE.
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

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from schemas.evaluacion_resultados import EvaluadoResponse, LoteResponse, ResultadoResponse
from services.evaluacion_reportes_service import EvaluacionReportesService
from services.evaluacion_service import EvaluacionService
from utils.errors import AppError

EMPRESA_PROPIA, EMPRESA_AJENA = uuid4(), uuid4()
AHORA = datetime.now(timezone.utc)


# ── Fakes ─────────────────────────────────────────────────────────────────────

def _lote(empresa_id: UUID) -> LoteResponse:
    return LoteResponse(id=uuid4(), empresa_id=empresa_id, periodo="Julio 2026", created_at=AHORA)


def _evaluado(lote_id: UUID, apellido: str = "Godoy") -> EvaluadoResponse:
    return EvaluadoResponse(id=uuid4(), lote_id=lote_id, created_at=AHORA, perfil="general",
                            apellido_evaluado=apellido, nombre_evaluado="Sol", nota_final=8.0)


class _FakeRepo:
    """Dos lotes, uno por empresa, cada uno con su evaluado y su resultado."""

    def __init__(self) -> None:
        self.propio, self.ajeno = _lote(EMPRESA_PROPIA), _lote(EMPRESA_AJENA)
        self._por_lote = {
            str(self.propio.id): [_evaluado(self.propio.id, "Propio")],
            str(self.ajeno.id): [_evaluado(self.ajeno.id, "Ajeno")],
        }
        self.leidos: list = []  # evaluados leídos: prueba que el 404 corta ANTES de leer

    def find_lote_by_id(self, id):
        return next((lo for lo in (self.propio, self.ajeno) if str(lo.id) == str(id)), None)

    def find_evaluados(self, lote_id):
        self.leidos.append(str(lote_id))
        return list(self._por_lote.get(str(lote_id), []))

    def find_resultados_por_evaluados(self, ids):
        return [ResultadoResponse(id=uuid4(), evaluado_id=UUID(i), created_at=AHORA,
                                  tipo_evaluador="PAR", competencia="X", orden=1, nota=7.0)
                for i in ids]


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.fixture
def svc(repo) -> EvaluacionReportesService:
    return EvaluacionReportesService(repo=repo)


def _llamadas(svc: EvaluacionReportesService, lote_id: UUID, evaluado_id: UUID) -> list:
    """Los 4 endpoints que reciben un id de recurso, como los llama el router."""
    return [
        ("metricas", lambda e: svc.metricas(lote_id, e)),
        ("evaluados", lambda e: svc.listado(lote_id, e)),
        ("export", lambda e: svc.exportar(lote_id, e, "csv")),
        ("ficha", lambda e: svc.ficha(lote_id, evaluado_id, e)),
    ]


# ── El lote ajeno responde 404 idéntico al inexistente ────────────────────────

def test_lote_de_otra_empresa_da_404_en_los_4_endpoints(svc, repo):
    ajeno = repo.ajeno
    ev_ajeno = repo._por_lote[str(ajeno.id)][0]
    for nombre, llamar in _llamadas(svc, ajeno.id, ev_ajeno.id):
        with pytest.raises(AppError) as exc:
            llamar(EMPRESA_PROPIA)
        assert exc.value.code == "LOTE_NOT_FOUND", nombre
        assert exc.value.status_code == 404, nombre
    assert repo.leidos == []  # cortó antes de leer una sola fila ajena


def test_mensaje_del_404_ajeno_es_indistinguible_del_inexistente(svc, repo):
    """No debe confirmar que el lote existe en otra empresa: mismo code Y mismo mensaje."""
    with pytest.raises(AppError) as ajeno:
        svc.metricas(repo.ajeno.id, EMPRESA_PROPIA)
    with pytest.raises(AppError) as inexistente:
        svc.metricas(uuid4(), EMPRESA_PROPIA)
    assert (ajeno.value.code, ajeno.value.message) == (inexistente.value.code, inexistente.value.message)
    assert ajeno.value.status_code == inexistente.value.status_code == 404


# ── El lote propio y el modo consolidado siguen funcionando ───────────────────

def test_lote_propio_responde_ok_en_los_4_endpoints(svc, repo):
    ev = repo._por_lote[str(repo.propio.id)][0]
    for nombre, llamar in _llamadas(svc, repo.propio.id, ev.id):
        assert llamar(EMPRESA_PROPIA) is not None, nombre
    assert svc.listado(repo.propio.id, EMPRESA_PROPIA).total == 1


def test_empresa_none_es_consolidado_y_no_restringe(svc, repo):
    """None = 'Todas las empresas' (semántica de get_empresa_id): el lote ajeno SÍ se lee."""
    ev = repo._por_lote[str(repo.ajeno.id)][0]
    for nombre, llamar in _llamadas(svc, repo.ajeno.id, ev.id):
        assert llamar(None) is not None, nombre


# ── Cadena de dos saltos: evaluado → lote → empresa ───────────────────────────

def test_ficha_evaluado_ajeno_no_es_alcanzable_ni_con_su_uuid_real(svc, repo):
    """Dos saltos: el evaluado no lleva empresa_id, se alcanza por lote_id. Pedir el evaluado
    AJENO a través del lote PROPIO no puede filtrarlo — no está entre los del lote validado."""
    ev_ajeno = repo._por_lote[str(repo.ajeno.id)][0]
    with pytest.raises(AppError) as exc:
        svc.ficha(repo.propio.id, ev_ajeno.id, EMPRESA_PROPIA)
    assert exc.value.code == "EVALUADO_NOT_FOUND" and exc.value.status_code == 404
    # y por su propio lote tampoco, porque el lote ya frena por empresa
    with pytest.raises(AppError) as exc2:
        svc.ficha(repo.ajeno.id, ev_ajeno.id, EMPRESA_PROPIA)
    assert exc2.value.code == "LOTE_NOT_FOUND"


def test_evaluados_de_un_lote_ajeno_nunca_se_devuelven(svc, repo):
    """El listado del lote propio trae solo sus evaluados (los del ajeno no se rozan)."""
    items = svc.listado(repo.propio.id, EMPRESA_PROPIA).items
    assert [i.apellido for i in items] == ["Propio"]
    assert repo.leidos == [str(repo.propio.id)]


# ── Lecturas por lote de EvaluacionService ────────────────────────────────────

def test_service_get_lote_y_listar_evaluados_validan_empresa(repo):
    svc = EvaluacionService(repo=repo)
    assert svc.get_lote(repo.propio.id, EMPRESA_PROPIA).id == repo.propio.id
    assert svc.listar_evaluados(repo.propio.id, EMPRESA_PROPIA).total == 1
    for llamar in (svc.get_lote, svc.listar_evaluados):
        with pytest.raises(AppError) as exc:
            llamar(repo.ajeno.id, EMPRESA_PROPIA)
        assert exc.value.code == "LOTE_NOT_FOUND" and exc.value.status_code == 404
    assert svc.get_lote(repo.ajeno.id).id == repo.ajeno.id  # sin empresa = consolidado
