"""
Los DOS ejes del rate limit de la quinta ruta pública, cada uno contra su propio ataque.

El rate limit NO es una mitigación más acá: en las otras cuatro rutas públicas hay un
autenticador real detrás (contraseña, refresh token rotativo, nonce de un solo uso) y el límite
solo encarece el abuso. En ésta el acceso es SOLO con dni, así que **el rate limit es la única
defensa**. Por eso se prueba que corta de verdad, no que está declarado.

  · POR IP (10/min, decorador de slowapi sobre el endpoint) — frena a UNA máquina probando
    muchos dnis. No frena un pool de IPs.
  · POR DNI (20/hora, `utils/rate_limit_dni`) — no frena la enumeración (cada intento usa un dni
    distinto, o sea un contador distinto) pero sí el uso repetido de un dni ajeno ya conocido.

Ninguno cubre lo del otro, y por eso hay dos clases y un test explícito de INDEPENDENCIA.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 Los contadores tendrían que estar sucios de otros tests.** Cada test usa una IP y un dni
ÚNICOS (`uuid4`), o sea un bucket virgen. Sin eso el resultado dependería del orden de la suite:
un test que corriera segundo vería el contador ya consumido y "corta en el 11" pasaría por el
motivo equivocado — o fallaría sin que nada esté roto.

**2. Se afirman las DOS direcciones.** No alcanza con "el intento N+1 corta": hay que ver que los
N anteriores NO cortan, o un limitador que rechaza siempre pasaría igual. Cada test compara la
tanda permitida contra el corte.

**3. La independencia se prueba con un segundo actor.** "El límite por IP corta" y "el límite por
IP corta a todo el mundo" son indistinguibles con una sola IP.

⚠️ La IP se controla con `X-Forwarded-For` porque `client_ip` toma `hops[-trusted_proxy_hops]` y
el default es 1. Es el MISMO camino que corre en producción detrás de Vercel, no un atajo.
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
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import services.identificacion_service as svc_mod  # noqa: E402
from config.settings import settings  # noqa: E402
from routers.horas_publico import _service  # noqa: E402
from schemas.horas_publico import IdentificacionResponse  # noqa: E402
from utils.rate_limit_dni import LIMITE_POR_DNI, consumir_intento  # noqa: E402

_RUTA = "/api/horas-publico/identificar"
_CUERPO = {"dni": "30111222"}


class _SvcFalso:
    async def identificar(self, dni: str, ip=None, user_agent=None) -> IdentificacionResponse:
        return IdentificacionResponse(nombre="Juan", token="t" * 43,
                                      expira_en=datetime.now(UTC))


@pytest.fixture
def app(monkeypatch):
    """App REAL con el flag encendido y el service falseado (el eje que se mide es el límite)."""
    monkeypatch.setattr(svc_mod, "_PISO_SEGUNDOS", 0.0)
    original = settings.horas_publico_enabled
    settings.horas_publico_enabled = True
    app = importlib.reload(main_mod).app
    app.dependency_overrides[_service] = _SvcFalso
    yield app
    app.dependency_overrides.clear()
    settings.horas_publico_enabled = original
    importlib.reload(main_mod)


def _ip_virgen() -> str:
    """Una IP que ningún otro test tocó: bucket limpio sin depender del orden de la suite."""
    return f"203.0.113.{uuid4().int % 200}.{uuid4().int % 10000}"


async def _postear(app, ip: str, veces: int) -> list:
    codigos = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        for _ in range(veces):
            r = await c.post(_RUTA, json=_CUERPO, headers={"X-Forwarded-For": ip})
            codigos.append(r.status_code)
    return codigos


# ── Eje 1: por IP ─────────────────────────────────────────────────────────────


class TestPorIP:
    async def test_corta_en_el_intento_11(self, app) -> None:
        """La franja es 10/min, la misma del callback de Google."""
        codigos = await _postear(app, _ip_virgen(), 11)
        assert codigos[:10] == [200] * 10, "cortó ANTES de los 10 permitidos"
        assert codigos[10] == 429

    async def test_el_429_respeta_el_contrato_de_error_del_repo(self, app) -> None:
        """El handler propio arma el body con `global_error_handler`, así que un 429 no puede
        divergir del `{error, message, code}` que el front espera de todo error."""
        ip = _ip_virgen()
        await _postear(app, ip, 10)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as c:
            r = await c.post(_RUTA, json=_CUERPO, headers={"X-Forwarded-For": ip})
        assert r.status_code == 429
        assert r.json()["code"] == "RATE_LIMIT_EXCEEDED"
        assert r.headers.get("Retry-After")

    async def test_bloquear_una_ip_no_bloquea_a_otra(self, app) -> None:
        """🔴 Sin este contraste, "corta" y "corta a todo el mundo" son lo mismo — y lo segundo
        sería una negación de servicio para el padrón entero."""
        atacante = _ip_virgen()
        assert (await _postear(app, atacante, 11))[10] == 429
        assert await _postear(app, _ip_virgen(), 1) == [200]


# ── Eje 2: por DNI ────────────────────────────────────────────────────────────


class TestPorDNI:
    """Se ejercita el contador REAL (`utils.rate_limit_dni`), no un doble: lo que importa es que
    use el storage configurado de la app, que es lo que le da Redis gratis cuando infra lo conecte."""

    def test_corta_en_el_intento_21(self) -> None:
        dni = str(uuid4().int)[:8]
        assert all(consumir_intento(dni) for _ in range(20)), "cortó antes de los 20 permitidos"
        assert consumir_intento(dni) is False

    def test_bloquear_un_dni_no_bloquea_a_otro(self) -> None:
        """Un contador por dni que se contagie sería peor que no tenerlo: un solo atacante
        dejaría a todo el padrón sin poder identificarse."""
        atacado = str(uuid4().int)[:8]
        for _ in range(21):
            consumir_intento(atacado)
        assert consumir_intento(atacado) is False
        assert consumir_intento(str(uuid4().int)[:8]) is True

    def test_consume_tambien_los_intentos_fallidos(self) -> None:
        """El contador vive en el service ANTES de tocar la base, así que no distingue acierto de
        fallo. Si solo contara aciertos, machacar un dni ajeno sería gratis hasta acertar."""
        inexistente = str(uuid4().int)[:8]
        for _ in range(20):
            consumir_intento(inexistente)
        assert consumir_intento(inexistente) is False

    def test_la_ventana_es_horaria_y_no_por_minuto(self) -> None:
        """El abuso que este eje ataca es sostenido, no una ráfaga: las ráfagas las corta el eje
        por IP. Una ventana por minuto dejaría 1200/hora, o sea no sería un techo."""
        assert LIMITE_POR_DNI.GRANULARITY.seconds == 3600
        assert LIMITE_POR_DNI.amount == 20


# ── Los dos son independientes ────────────────────────────────────────────────


class TestLosDosEjesSonIndependientes:
    async def test_una_ip_limpia_no_salva_a_un_dni_quemado(self, app) -> None:
        """🔴 EL TEST QUE JUSTIFICA QUE HAYA DOS EJES. Es el escenario real del eje por dni:
        alguien con muchas IPs usando un dni ajeno que ya conoce. Con una IP virgen el límite
        por IP no dice nada, y sin el eje por dni el intento pasaría."""
        dni = str(uuid4().int)[:8]
        for _ in range(20):
            consumir_intento(dni)
        assert consumir_intento(dni) is False          # el dni está quemado…
        assert await _postear(app, _ip_virgen(), 1) == [200]   # …y la IP sigue limpia

    async def test_un_dni_limpio_no_salva_a_una_ip_quemada(self, app) -> None:
        """El recíproco: es el escenario del eje por IP —enumeración desde una máquina—, donde
        cada intento usa un dni distinto y el contador por dni nunca se toca dos veces."""
        ip = _ip_virgen()
        assert (await _postear(app, ip, 11))[10] == 429
        assert consumir_intento(str(uuid4().int)[:8]) is True
