"""
Flag de módulo de assessment (settings.assessment_enabled / env ASSESSMENT_ENABLED).

Cubre las tres piezas del apagado:
  · main.py            — el router se monta solo si el flag está on.
  · middleware/auth.py — las 2 rutas públicas solo son públicas si el flag está on.
  · el borrado de _ASSESSMENT_FE_RE, el bypass de auth sobre /assessment/* que no matcheaba
    ninguna ruta del backend pero dejaba la puerta abierta para cualquiera que se montara ahí.

Lo que se verifica no es solo "da error", sino que **da el MISMO error que una ruta que nunca
existió**: si apagar el módulo devolviera un status o un body distinto al de cualquier path
desconocido, eso mismo confirmaría que el módulo está ahí, apagado. Ese es el test que importa.

El flag se prueba reconstruyendo el app real de main.py con importlib.reload, no un app de
mentira: el punto es justamente que el cableado de producción respete el flag.
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

import importlib
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

import main as main_mod
from config.settings import settings
from middleware.auth import _is_public
from routers.assessment import _svc
from schemas.assessment import LinkResponse, ResultadoResponse

TOKEN = "a" * 64
_RUTA_GET = f"/api/assessment/evaluacion/{TOKEN}"
_RUTA_SUBMIT = f"/api/assessment/evaluacion/{TOKEN}/submit"
# Path de control: no existe ni existió nunca. El módulo apagado tiene que ser indistinguible.
_RUTA_INEXISTENTE = "/api/modulo-que-nunca-existio/algo"


class _FakeSvc:
    """Evita la red: el test mide el cableado del flag, no la lógica del assessment."""

    def get_evaluacion(self, token: str) -> LinkResponse:
        return LinkResponse(
            id=uuid4(), campana_id=uuid4(), token=token,
            evaluado_nombre="Ana Pérez", evaluado_email="ana@ejemplo.com",
            completado=False, created_at=datetime.now(UTC),
        )

    def submit_evaluacion(self, token: str, data) -> ResultadoResponse:
        return ResultadoResponse(
            id=uuid4(), link_id=uuid4(), evaluado_nombre="Ana Pérez",
            tipo="completo", score_general=80,
        )


@pytest.fixture
def app_con_flag(request):
    """Reconstruye el app real con el flag en el estado pedido y lo restaura al salir."""
    activo: bool = request.param
    original = settings.assessment_enabled
    settings.assessment_enabled = activo
    app = importlib.reload(main_mod).app
    app.dependency_overrides[_svc] = _FakeSvc
    yield app
    app.dependency_overrides.clear()
    settings.assessment_enabled = original
    importlib.reload(main_mod)


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _paths(app) -> set[str]:
    return {getattr(r, "path", "") for r in app.routes}


# ─── Módulo APAGADO ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("app_con_flag", [False], indirect=True)
class TestApagado:
    def test_router_no_montado(self, app_con_flag) -> None:
        assert not any(p.startswith("/api/assessment") for p in _paths(app_con_flag))

    async def test_get_no_responde_como_antes(self, app_con_flag) -> None:
        async with _client(app_con_flag) as c:
            resp = await c.get(_RUTA_GET)
        assert resp.status_code != 200

    async def test_submit_no_responde_como_antes(self, app_con_flag) -> None:
        async with _client(app_con_flag) as c:
            resp = await c.post(_RUTA_SUBMIT, json={"respuestas": []})
        assert resp.status_code != 201

    async def test_get_indistinguible_de_ruta_inexistente(self, app_con_flag) -> None:
        """Mismo status y mismo body que un path que nunca existió — sin oráculo."""
        async with _client(app_con_flag) as c:
            apagada = await c.get(_RUTA_GET)
            control = await c.get(_RUTA_INEXISTENTE)
        assert (apagada.status_code, apagada.json()) == (control.status_code, control.json())

    async def test_submit_indistinguible_de_ruta_inexistente(self, app_con_flag) -> None:
        async with _client(app_con_flag) as c:
            apagada = await c.post(_RUTA_SUBMIT, json={"respuestas": []})
            control = await c.post(_RUTA_INEXISTENTE, json={"respuestas": []})
        assert (apagada.status_code, apagada.json()) == (control.status_code, control.json())

    async def test_nunca_responde_403(self, app_con_flag) -> None:
        """Un 403 confirmaría que el recurso existe y que no te dejan entrar."""
        async with _client(app_con_flag) as c:
            for resp in (await c.get(_RUTA_GET), await c.post(_RUTA_SUBMIT, json={"respuestas": []})):
                assert resp.status_code != 403


# ─── Módulo ENCENDIDO ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("app_con_flag", [True], indirect=True)
class TestEncendido:
    def test_router_montado(self, app_con_flag) -> None:
        assert _RUTA_GET.replace(TOKEN, "{token}") in _paths(app_con_flag)

    async def test_get_responde_sin_token(self, app_con_flag) -> None:
        """Sigue siendo pública: sin Authorization devuelve el link igual que antes."""
        async with _client(app_con_flag) as c:
            resp = await c.get(_RUTA_GET)
        assert resp.status_code == 200
        assert resp.json()["evaluado_email"] == "ana@ejemplo.com"

    async def test_submit_responde_sin_token(self, app_con_flag) -> None:
        async with _client(app_con_flag) as c:
            resp = await c.post(_RUTA_SUBMIT, json={"respuestas": []})
        assert resp.status_code == 201
        assert resp.json()["score_general"] == 80

    async def test_endpoints_autenticados_siguen_pidiendo_token(self, app_con_flag) -> None:
        """Encender el módulo no abre lo que nunca fue público."""
        async with _client(app_con_flag) as c:
            resp = await c.get("/api/assessment/campanas")
        assert resp.status_code == 401


# ─── _is_public: qué es público según el flag ─────────────────────────────────


class TestIsPublic:
    """Sin app: mide directo la decisión del middleware, que es donde vive el gateo."""

    def _con_flag(self, activo: bool, ruta: str) -> bool:
        original = settings.assessment_enabled
        settings.assessment_enabled = activo
        try:
            return _is_public(ruta)
        finally:
            settings.assessment_enabled = original

    @pytest.mark.parametrize("ruta", [_RUTA_GET, _RUTA_SUBMIT])
    def test_apagado_no_son_publicas(self, ruta: str) -> None:
        assert not self._con_flag(False, ruta)

    @pytest.mark.parametrize("ruta", [_RUTA_GET, _RUTA_SUBMIT])
    def test_encendido_son_publicas(self, ruta: str) -> None:
        assert self._con_flag(True, ruta)


# ─── _ASSESSMENT_FE_RE borrado ────────────────────────────────────────────────


class TestBypassFrontendBorrado:
    """/assessment/* ya no saltea auth, ni siquiera con el módulo encendido."""

    @pytest.mark.parametrize("activo", [False, True])
    def test_ruta_front_nunca_es_publica(self, activo: bool) -> None:
        original = settings.assessment_enabled
        settings.assessment_enabled = activo
        try:
            assert not _is_public("/assessment/cualquier-token")
            assert not _is_public("/assessment/x")
        finally:
            settings.assessment_enabled = original

    def test_publicas_siguen_siendo_publicas(self) -> None:
        """Guarda de regresión: el gateo no se comió las rutas públicas de siempre."""
        for ruta in ("/health", "/api/auth/login", "/api/auth/refresh",
                     "/api/integraciones/google/callback"):
            assert _is_public(ruta)
