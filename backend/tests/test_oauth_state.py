"""
Nonce del flujo de autorización OAuth: emisión, consumo y rechazo.

Qué garantiza el mecanismo, y qué se prueba de cada cosa:

  · **Un solo uso** — el borrado ES la verificación, así que el mismo valor no puede completar
    dos flujos (TestUnSoloUso).
  · **Vigencia acotada** — TTL de 10 minutos (TestVencimiento).
  · **Identidad tomada de la fila persistida, nunca del query param** — es lo que hace que la
    cuenta de Google termine conectada al usuario que inició el flujo y a ningún otro
    (TestIdentidadSaleDelRegistro). El test más importante del archivo.
  · **Rechazo indistinguible** — los cuatro motivos (ausente, desconocido, vencido, ya usado)
    salen con el mismo code, el mismo mensaje y el mismo status. Se comparan las tuplas
    completas, no solo el código (TestRechazoUnico).
  · **Autolimpieza** — la purga corre en el camino que crea filas, y no toca las vigentes
    (TestPurgaOportunista).

El fake de repo modela la tabla de verdad: `consumir` BORRA y devuelve lo borrado, que es la
semántica de la que depende el uso único. Un fake que solo leyera daría verde sin probar nada.
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

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

import services._google_oauth as goauth
from config.settings import settings
from services._oauth_state import _TTL_MINUTOS, consumir, generar
from utils.errors import AppError

USUARIO_A = str(uuid4())
USUARIO_B = str(uuid4())


class _FakeStateRepo:
    """Modela oauth_states. `consumir` borra y devuelve, como el DELETE real."""

    def __init__(self) -> None:
        self.filas: list[dict] = []
        self.purgas = 0

    def crear(self, state_hash: str, user_id: str, proveedor: str, expires_at: str) -> dict:
        fila = {"state_hash": state_hash, "user_id": user_id,
                "proveedor": proveedor, "expires_at": expires_at}
        self.filas.append(fila)
        return fila

    def consumir(self, state_hash: str, proveedor: str):
        for i, f in enumerate(self.filas):
            if f["state_hash"] == state_hash and f["proveedor"] == proveedor:
                return self.filas.pop(i)
        return None

    def purgar_vencidos(self, ahora: str) -> int:
        antes = len(self.filas)
        self.filas = [f for f in self.filas if f["expires_at"] >= ahora]
        self.purgas += 1
        return antes - len(self.filas)


def _vencer(repo: _FakeStateRepo) -> None:
    """Empuja todas las filas al pasado."""
    pasado = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    for f in repo.filas:
        f["expires_at"] = pasado


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def _firma(e: AppError) -> tuple:
    return (e.status_code, e.code, e.message)


# ─── Emisión ──────────────────────────────────────────────────────────────────


class TestGenerar:
    def test_dos_llamadas_dan_states_distintos(self) -> None:
        repo = _FakeStateRepo()
        assert generar(repo, USUARIO_A) != generar(repo, USUARIO_A)

    def test_persiste_una_fila_por_emision(self) -> None:
        repo = _FakeStateRepo()
        generar(repo, USUARIO_A)
        generar(repo, USUARIO_A)
        assert len(repo.filas) == 2

    def test_no_guarda_el_valor_crudo(self) -> None:
        repo = _FakeStateRepo()
        state = generar(repo, USUARIO_A)
        assert state not in [f["state_hash"] for f in repo.filas]
        assert len(repo.filas[0]["state_hash"]) == 64  # sha256 hex

    def test_el_ttl_es_el_declarado(self) -> None:
        repo = _FakeStateRepo()
        generar(repo, USUARIO_A)
        expira = datetime.fromisoformat(repo.filas[0]["expires_at"])
        restante = (expira - datetime.now(UTC)).total_seconds()
        assert _TTL_MINUTOS * 60 - 5 < restante <= _TTL_MINUTOS * 60


# ─── Un solo uso ──────────────────────────────────────────────────────────────


class TestUnSoloUso:
    def test_state_valido_resuelve_el_usuario(self) -> None:
        repo = _FakeStateRepo()
        assert consumir(repo, generar(repo, USUARIO_A)) == USUARIO_A

    def test_queda_consumido(self) -> None:
        repo = _FakeStateRepo()
        consumir(repo, generar(repo, USUARIO_A))
        assert repo.filas == []

    def test_el_segundo_uso_falla(self) -> None:
        repo = _FakeStateRepo()
        state = generar(repo, USUARIO_A)
        consumir(repo, state)
        assert _error(lambda: consumir(repo, state)).code == "OAUTH_STATE_INVALIDO"

    def test_consumir_uno_no_invalida_los_otros(self) -> None:
        repo = _FakeStateRepo()
        primero, segundo = generar(repo, USUARIO_A), generar(repo, USUARIO_A)
        consumir(repo, primero)
        assert consumir(repo, segundo) == USUARIO_A


class TestVencimiento:
    def test_state_vencido_falla(self) -> None:
        repo = _FakeStateRepo()
        state = generar(repo, USUARIO_A)
        _vencer(repo)
        assert _error(lambda: consumir(repo, state)).code == "OAUTH_STATE_INVALIDO"

    def test_otro_proveedor_no_sirve(self) -> None:
        repo = _FakeStateRepo()
        state = generar(repo, USUARIO_A, proveedor="google")
        assert _error(lambda: consumir(repo, state, proveedor="otro")).code == "OAUTH_STATE_INVALIDO"


# ─── Rechazo único ────────────────────────────────────────────────────────────


class TestRechazoUnico:
    """Los cuatro motivos tienen que ser indistinguibles desde afuera."""

    def _casos(self) -> dict[str, AppError]:
        repo = _FakeStateRepo()
        usado = generar(repo, USUARIO_A)
        consumir(repo, usado)
        vencido = generar(repo, USUARIO_A)
        _vencer(repo)
        return {
            "ausente": _error(lambda: consumir(repo, None)),
            "desconocido": _error(lambda: consumir(repo, "no-existe-este-state")),
            "ya_usado": _error(lambda: consumir(repo, usado)),
            "vencido": _error(lambda: consumir(repo, vencido)),
        }

    def test_los_cuatro_dan_la_misma_firma(self) -> None:
        firmas = {motivo: _firma(e) for motivo, e in self._casos().items()}
        assert len(set(firmas.values())) == 1, firmas

    def test_vacio_tambien_cae_en_el_rechazo(self) -> None:
        repo = _FakeStateRepo()
        assert _error(lambda: consumir(repo, "")).code == "OAUTH_STATE_INVALIDO"

    def test_el_warning_no_vuelca_el_valor(self, caplog) -> None:
        repo = _FakeStateRepo()
        secreto = "state-secreto-que-no-debe-loguearse"
        with caplog.at_level("WARNING"):
            _error(lambda: consumir(repo, secreto))
        assert caplog.records
        assert all(secreto not in r.getMessage() for r in caplog.records)


# ─── Purga oportunista ────────────────────────────────────────────────────────


class TestPurgaOportunista:
    def test_generar_purga(self) -> None:
        repo = _FakeStateRepo()
        generar(repo, USUARIO_A)
        assert repo.purgas == 1

    def test_borra_vencidos_y_conserva_vigentes(self) -> None:
        repo = _FakeStateRepo()
        generar(repo, USUARIO_A)
        _vencer(repo)                    # la de arriba queda vencida
        vigente = generar(repo, USUARIO_B)  # esta purga y luego inserta
        assert len(repo.filas) == 1
        assert consumir(repo, vigente) == USUARIO_B

    def test_no_purga_el_state_recien_emitido(self) -> None:
        """Se purga ANTES de insertar; si fuera al revés, el nuevo podría barrerse solo."""
        repo = _FakeStateRepo()
        state = generar(repo, USUARIO_A)
        assert consumir(repo, state) == USUARIO_A


# ─── Identidad: sale del registro, no del query param ─────────────────────────


class _FakeCreds:
    token = "access-token"
    refresh_token = "refresh-token"
    expiry = None


class _FakeFlow:
    credentials = _FakeCreds()

    def __init__(self) -> None:
        self.redirect_uri = None

    @classmethod
    def from_client_config(cls, config, scopes, state=None):
        return cls()

    def fetch_token(self, code=None) -> None:
        pass

    def authorization_url(self, **kw):
        return (f"https://accounts.google.com/o/oauth2/auth?state={kw['state']}", None)


class _FakeHttpResp:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"email": "ana@ejemplo.com"}


class _FakeHttpClient:
    def __enter__(self):
        return self

    def __exit__(self, *a) -> bool:
        return False

    def get(self, url, headers=None):
        return _FakeHttpResp()


class _IntegracionRepoSpy:
    def __init__(self) -> None:
        self.guardado_para: list[str] = []

    def save_google_tokens(self, user_id: str, tokens: dict) -> dict:
        self.guardado_para.append(user_id)
        return {}


@pytest.fixture
def sin_red(monkeypatch):
    """Corta Google: acá se mide de quién queda la cuenta, no el intercambio de tokens."""
    monkeypatch.setattr(goauth, "Flow", _FakeFlow)
    monkeypatch.setattr(goauth, "httpx", SimpleNamespace(Client=lambda *a, **k: _FakeHttpClient()))
    monkeypatch.setattr(settings, "google_client_id", "id-de-prueba")
    monkeypatch.setattr(settings, "google_client_secret", "secreto-de-prueba")


class TestIdentidadSaleDelRegistro:
    def test_la_cuenta_queda_en_el_usuario_que_inicio_el_flujo(self, sin_red) -> None:
        states, integraciones = _FakeStateRepo(), _IntegracionRepoSpy()
        state = goauth.construir_url_autorizacion(USUARIO_A, state_repo=states)
        state = state.split("state=")[1]
        goauth.procesar_callback(integraciones, state, "code-de-google", state_repo=states)
        assert integraciones.guardado_para == [USUARIO_A]

    def test_un_state_de_a_nunca_conecta_la_cuenta_a_b(self, sin_red) -> None:
        """El corazón del mecanismo: la identidad NO viaja en el parámetro del callback."""
        states, integraciones = _FakeStateRepo(), _IntegracionRepoSpy()
        de_a = goauth.construir_url_autorizacion(USUARIO_A, state_repo=states).split("state=")[1]
        goauth.procesar_callback(integraciones, de_a, "code", state_repo=states)
        assert USUARIO_B not in integraciones.guardado_para

    def test_el_callback_consume_el_state(self, sin_red) -> None:
        states, integraciones = _FakeStateRepo(), _IntegracionRepoSpy()
        state = goauth.construir_url_autorizacion(USUARIO_A, state_repo=states).split("state=")[1]
        goauth.procesar_callback(integraciones, state, "code", state_repo=states)
        assert states.filas == []

    def test_reusar_el_state_del_callback_falla(self, sin_red) -> None:
        states, integraciones = _FakeStateRepo(), _IntegracionRepoSpy()
        state = goauth.construir_url_autorizacion(USUARIO_A, state_repo=states).split("state=")[1]
        goauth.procesar_callback(integraciones, state, "code", state_repo=states)
        with pytest.raises(AppError) as exc:
            goauth.procesar_callback(integraciones, state, "code", state_repo=states)
        assert exc.value.code == "OAUTH_STATE_INVALIDO"
        assert integraciones.guardado_para == [USUARIO_A]  # no hubo segunda conexión

    def test_state_invalido_no_llega_a_intercambiar_tokens(self, sin_red) -> None:
        """La verificación va PRIMERO: con un state que no sirve no se habla con Google."""
        states, integraciones = _FakeStateRepo(), _IntegracionRepoSpy()
        with pytest.raises(AppError):
            goauth.procesar_callback(integraciones, "state-inventado", "code", state_repo=states)
        assert integraciones.guardado_para == []

    def test_la_url_lleva_un_state_que_no_es_el_user_id(self, sin_red) -> None:
        states = _FakeStateRepo()
        url = goauth.construir_url_autorizacion(USUARIO_A, state_repo=states)
        assert USUARIO_A not in url
