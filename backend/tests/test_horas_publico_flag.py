"""
El flag `HORAS_PUBLICO_ENABLED` y los DOS ejes del rate limit de la quinta ruta pública.

Cubre las tres piezas del apagado:
  · `main.py`            — el router se monta solo con el flag encendido.
  · `_rutas_publicas.py` — la ruta solo cuenta como pública con el flag encendido.
  · el efecto combinado  — apagado, es INDISTINGUIBLE de una ruta que nunca existió.

Lo que se verifica no es "da error", sino que da **EL MISMO error que un path que nunca existió**.
Si apagar el módulo devolviera un status o un body distinto al de cualquier ruta desconocida, eso
mismo confirmaría que el módulo está ahí, apagado. Molde: `test_assessment_modulo_flag.py`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 La ruta de control tendría que ser una constante escrita a mano.** Se compara contra
`/api/modulo-que-nunca-existio/algo`, un path REAL que se manda por la misma app y del que se lee
la respuesta REAL. Si en vez de eso se afirmara `resp.status_code == 401`, el test pasaría el día
que el 401 de las rutas desconocidas cambie a otra cosa y la ruta apagada se quede en 401 — que
es exactamente la divergencia que se quiere detectar.

**2. El app tendría que ser un `FastAPI()` de mentira.** Se reconstruye el app REAL de `main.py`
con `importlib.reload`, porque el punto es que el cableado de producción respete el flag.

**3. El servicio real tendría que quedar cableado.** Con el flag ENCENDIDO se sobreescribe por
un doble: sin eso el test pegaría contra Supabase y el 200 dependería de la red.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

import importlib  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import middleware._rutas_publicas as rutas_mod  # noqa: E402
from config.settings import settings  # noqa: E402
from middleware.auth import _is_public  # noqa: E402
from routers.horas_publico import _service  # noqa: E402
from schemas.horas_publico import IdentificacionResponse  # noqa: E402

_RUTA = "/api/horas-publico/identificar"
# Path de control: no existe ni existió nunca. El módulo apagado tiene que ser indistinguible.
_RUTA_INEXISTENTE = "/api/modulo-que-nunca-existio/algo"
_CUERPO = {"dni": "30111222"}


class _SvcFalso:
    """Evita la red: estos tests miden el CABLEADO del flag, no la lógica de identificación."""

    async def identificar(self, dni: str, ip=None, user_agent=None) -> IdentificacionResponse:
        return IdentificacionResponse(nombre="Juan", token="t" * 43,
                                      expira_en=datetime.now(UTC))


@pytest.fixture
def app_con_flag(request):
    """Reconstruye el app REAL con el flag en el estado pedido y lo restaura al salir."""
    activo: bool = request.param
    original = settings.horas_publico_enabled
    settings.horas_publico_enabled = activo
    app = importlib.reload(main_mod).app
    app.dependency_overrides[_service] = _SvcFalso
    yield app
    app.dependency_overrides.clear()
    settings.horas_publico_enabled = original
    importlib.reload(main_mod)


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _paths(app) -> set:
    return {getattr(r, "path", "") for r in app.routes}


# ─── Módulo APAGADO ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("app_con_flag", [False], indirect=True)
class TestApagado:
    def test_el_router_no_se_monta(self, app_con_flag) -> None:
        assert not any(p.startswith("/api/horas-publico") for p in _paths(app_con_flag))

    def test_la_ruta_no_es_publica(self, app_con_flag) -> None:
        assert not _is_public(_RUTA)

    def test_no_aparece_en_las_rutas_publicas_activas(self, app_con_flag) -> None:
        """Es lo que lee el smoke test: apagada no tiene que figurar como superficie sin auth."""
        assert _RUTA not in rutas_mod.rutas_publicas_activas()

    async def test_es_indistinguible_de_una_ruta_inexistente(self, app_con_flag) -> None:
        """🔴 EL TEST QUE IMPORTA. Mismo status y mismo body que un path que nunca existió."""
        async with _client(app_con_flag) as c:
            apagada = await c.post(_RUTA, json=_CUERPO)
            control = await c.post(_RUTA_INEXISTENTE, json=_CUERPO)
        assert (apagada.status_code, apagada.json()) == (control.status_code, control.json())

    async def test_nunca_responde_403(self, app_con_flag) -> None:
        """Un 403 confirmaría que el recurso existe y que no te dejan entrar."""
        async with _client(app_con_flag) as c:
            assert (await c.post(_RUTA, json=_CUERPO)).status_code != 403

    async def test_no_responde_200(self, app_con_flag) -> None:
        async with _client(app_con_flag) as c:
            assert (await c.post(_RUTA, json=_CUERPO)).status_code != 200


# ─── Módulo ENCENDIDO ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("app_con_flag", [True], indirect=True)
class TestEncendido:
    def test_el_router_se_monta(self, app_con_flag) -> None:
        assert _RUTA in _paths(app_con_flag)

    def test_la_ruta_es_publica(self, app_con_flag) -> None:
        assert _is_public(_RUTA) and _RUTA in rutas_mod.rutas_publicas_activas()

    async def test_responde_sin_token(self, app_con_flag) -> None:
        """El contraste que hace que los tests de apagado signifiquen algo."""
        async with _client(app_con_flag) as c:
            resp = await c.post(_RUTA, json=_CUERPO)
        assert resp.status_code == 200 and resp.json()["nombre"] == "Juan"

    async def test_encenderlo_no_abre_lo_que_nunca_fue_publico(self, app_con_flag) -> None:
        async with _client(app_con_flag) as c:
            assert (await c.get("/api/empleados")).status_code == 401


# ─── El matcheo, con las dos direcciones ──────────────────────────────────────


class TestElMatcheoEsExacto:
    """El matcheo es igualdad de string. Estas variantes NO son públicas con ningún flag."""

    @pytest.fixture(autouse=True)
    def encendido(self):
        original = settings.horas_publico_enabled
        settings.horas_publico_enabled = True
        yield
        settings.horas_publico_enabled = original

    @pytest.mark.parametrize("variante", [
        _RUTA + "/",              # barra final: el redirect de Starlette ocurre DETRÁS del auth
        _RUTA + "/extra",
        _RUTA.upper(),
        "/api/horas-publico",
        "/api/horas-publico/otra-cosa",
    ])
    def test_las_variantes_no_son_publicas(self, variante: str) -> None:
        assert not _is_public(variante)

    def test_la_exacta_si_lo_es(self) -> None:
        """Sin este contraste, "ninguna variante es pública" pasaría con la ruta borrada."""
        assert _is_public(_RUTA)


class TestElFlagNoContagia:
    """Encender horas-publico no puede volver pública ninguna otra ruta, ni al revés."""

    def test_las_cuatro_de_siempre_siguen_publicas_con_el_flag_apagado(self) -> None:
        original = settings.horas_publico_enabled
        settings.horas_publico_enabled = False
        try:
            for r in ("/health", "/api/auth/login", "/api/auth/refresh",
                      "/api/integraciones/google/callback"):
                assert _is_public(r)
        finally:
            settings.horas_publico_enabled = original

    def test_el_flag_agrega_exactamente_cinco(self) -> None:
        original = settings.horas_publico_enabled
        try:
            settings.horas_publico_enabled = False
            apagado = rutas_mod.rutas_publicas_activas()
            settings.horas_publico_enabled = True
            encendido = rutas_mod.rutas_publicas_activas()
        finally:
            settings.horas_publico_enabled = original
        # 🔴 CINCO, no una: identificar, las dos escrituras, el GET de la semana y el catálogo
        # de clientes del select. Si alguien suma una sexta al flag, este test lo obliga a pasar
        # por acá y a decidirlo en vez de que aparezca sola — cada una es superficie sin auth.
        assert encendido - apagado == {_RUTA, "/api/horas-publico/horas",
                                       "/api/horas-publico/licencia",
                                       "/api/horas-publico/semana",
                                       "/api/horas-publico/clientes"}
        assert len(apagado) == 4, "las incondicionales son cuatro; una quinta necesita decisión"
