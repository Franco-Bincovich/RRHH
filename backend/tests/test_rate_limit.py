"""
Rate limiting: key_func, formato del 429 y las franjas.

Se prueba en dos planos, porque cada uno cubre lo que el otro no puede:

  · **Comportamiento** (end-to-end contra el app real): que al superar el límite salga un 429
    con el formato de error del repo y con Retry-After. Se hace sobre las rutas públicas de
    assessment y sobre /api/auth/refresh, que son las únicas alcanzables sin forjar un JWT
    válido contra el JWKS.

  · **Estructural** (inspección de limiter._route_limits): que cada franja esté aplicada al
    endpoint correcto y con el valor correcto. Es lo único que puede cubrir las franjas
    autenticadas (import, export, reportes) sin montar auth de mentira — y además detecta el
    error más probable a futuro: agregar un endpoint de export y olvidarse del decorador.
    El mecanismo de "superar el límite → 429" ya queda probado por el plano de arriba; es el
    mismo para todas las franjas.

El key_func se prueba aparte, sobre Requests fabricados: es la pieza donde un error no se ve
como un test roto sino como el equipo entero compartiendo un contador.
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
from starlette.requests import Request

import main as main_mod
from config.settings import settings
from routers.assessment import _svc
from schemas.assessment import LinkResponse, ResultadoResponse
from utils.rate_limit import BASELINE, client_ip, limiter

TOKEN = "b" * 64
_RUTA_GET = f"/api/assessment/evaluacion/{TOKEN}"
_RUTA_SUBMIT = f"/api/assessment/evaluacion/{TOKEN}/submit"


# ─── key_func ─────────────────────────────────────────────────────────────────


def _req(xff: str | None, client_host: str | None = "10.0.0.1") -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return Request({
        "type": "http",
        "headers": headers,
        "client": (client_host, 12345) if client_host else None,
    })


class TestClientIp:
    """La IP es la clave del contador: si esto falla, todo el tráfico cae en un solo bucket."""

    def test_sin_xff_cae_a_la_ip_de_conexion(self) -> None:
        assert client_ip(_req(None)) == "10.0.0.1"

    def test_un_hop_toma_la_entrada_que_agrego_el_proxy(self) -> None:
        """Con Vercel (1 hop) el edge appendea la IP real: es la última entrada."""
        assert client_ip(_req("200.0.0.9")) == "200.0.0.9"

    def test_xff_falsificado_por_el_cliente_se_descarta(self) -> None:
        """El cliente manda 1.2.3.4; el proxy appendea su IP real. Gana la del proxy."""
        assert client_ip(_req("1.2.3.4, 200.0.0.9")) == "200.0.0.9"

    def test_cadena_larga_falsificada_tampoco_gana(self) -> None:
        assert client_ip(_req("1.1.1.1, 2.2.2.2, 3.3.3.3, 200.0.0.9")) == "200.0.0.9"

    def test_dos_hops_saltea_el_proxy_intermedio(self, monkeypatch) -> None:
        """CloudFront + ALB: la IP del cliente queda a dos lugares de la derecha."""
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        assert client_ip(_req("200.0.0.9, 10.1.1.1")) == "200.0.0.9"

    def test_xff_mas_corto_que_lo_declarado_no_adivina(self, monkeypatch) -> None:
        """Menos saltos de los esperados = config rota o golpe directo al origin: se cae a
        la IP de conexión en vez de tomar un valor que el cliente pudo escribir."""
        monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
        assert client_ip(_req("1.2.3.4")) == "10.0.0.1"

    def test_cero_hops_ignora_el_header(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
        assert client_ip(_req("1.2.3.4, 5.6.7.8")) == "10.0.0.1"

    def test_sin_xff_y_sin_client_no_explota(self) -> None:
        assert client_ip(_req(None, client_host=None)) == "127.0.0.1"

    def test_espacios_y_entradas_vacias_no_corren_el_indice(self) -> None:
        assert client_ip(_req("1.2.3.4 ,  , 200.0.0.9 ")) == "200.0.0.9"


# ─── Comportamiento end-to-end ────────────────────────────────────────────────


class _FakeSvc:
    """Evita la red: acá se mide el límite, no la lógica del assessment."""

    def get_evaluacion(self, token: str) -> LinkResponse:
        return LinkResponse(
            id=uuid4(), campana_id=uuid4(), token=token,
            evaluado_nombre="Ana Pérez", evaluado_email="ana@ejemplo.com",
            completado=False, created_at=datetime.now(UTC),
        )

    def submit_evaluacion(self, token: str, data) -> ResultadoResponse:
        return ResultadoResponse(
            id=uuid4(), link_id=uuid4(), evaluado_nombre="Ana Pérez", tipo="completo",
        )


@pytest.fixture
def app_publico():
    """App real con assessment ENCENDIDO (única superficie alcanzable sin JWT válido)."""
    original = settings.assessment_enabled
    settings.assessment_enabled = True
    app = importlib.reload(main_mod).app
    app.dependency_overrides[_svc] = _FakeSvc
    limiter.reset()
    yield app
    app.dependency_overrides.clear()
    limiter.reset()
    settings.assessment_enabled = original
    importlib.reload(main_mod)


def _client(app, ip: str = "200.0.0.9") -> httpx.AsyncClient:
    """Cada test elige su IP: el bucket es por IP, así no se pisan entre sí."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": ip},
    )


class TestFormatoDel429:
    async def test_supera_el_limite_y_devuelve_429(self, app_publico) -> None:
        async with _client(app_publico, "10.10.0.1") as c:
            for _ in range(10):
                assert (await c.get(_RUTA_GET)).status_code == 200
            resp = await c.get(_RUTA_GET)
        assert resp.status_code == 429

    async def test_body_con_el_formato_de_error_del_repo(self, app_publico) -> None:
        """{error: true, message, code} — NO el {"error": "Rate limit exceeded: ..."} de slowapi."""
        async with _client(app_publico, "10.10.0.2") as c:
            for _ in range(11):
                resp = await c.get(_RUTA_GET)
        body = resp.json()
        assert body["error"] is True
        assert body["code"] == "RATE_LIMIT_EXCEEDED"
        assert isinstance(body["message"], str) and body["message"]
        assert set(body) == {"error", "message", "code"}

    async def test_conserva_retry_after(self, app_publico) -> None:
        async with _client(app_publico, "10.10.0.3") as c:
            for _ in range(11):
                resp = await c.get(_RUTA_GET)
        assert "Retry-After" in resp.headers
        assert int(resp.headers["Retry-After"]) >= 0

    async def test_ips_distintas_no_comparten_bucket(self, app_publico) -> None:
        """Si esto falla, un solo cliente ruidoso deja afuera a todos los demás."""
        async with _client(app_publico, "10.10.0.4") as c:
            for _ in range(11):
                await c.get(_RUTA_GET)
        async with _client(app_publico, "10.10.0.5") as otro:
            assert (await otro.get(_RUTA_GET)).status_code == 200

    async def test_submit_tiene_su_propio_limite_mas_bajo(self, app_publico) -> None:
        """5/min: la escritura sin auth es más restrictiva que la lectura."""
        async with _client(app_publico, "10.10.0.6") as c:
            for _ in range(5):
                assert (await c.post(_RUTA_SUBMIT, json={"respuestas": []})).status_code == 201
            resp = await c.post(_RUTA_SUBMIT, json={"respuestas": []})
        assert resp.status_code == 429

    async def test_health_exento(self, app_publico) -> None:
        """Muy por encima del baseline: el health check no se puede rate-limitar."""
        async with _client(app_publico, "10.10.0.7") as c:
            for _ in range(60):
                resp = await c.get("/health")
        assert resp.status_code == 200


# ─── Franjas: qué límite quedó en qué endpoint ────────────────────────────────


def _limites(modulo: str, funcion: str) -> list:
    return limiter._route_limits.get(f"routers.{modulo}.{funcion}", [])


def _valores(modulo: str, funcion: str) -> set[str]:
    return {str(lim.limit) for lim in _limites(modulo, funcion)}


class TestFranjaPublica:
    @pytest.mark.parametrize("funcion,esperado", [
        ("get_evaluacion", "10 per 1 minute"),
        ("submit_evaluacion", "5 per 1 minute"),
    ])
    def test_assessment(self, funcion: str, esperado: str) -> None:
        assert _valores("assessment", funcion) == {esperado}

    def test_limites_puestos_aunque_el_modulo_este_apagado(self) -> None:
        """Encender ASSESSMENT_ENABLED no debe reabrir el agujero: el límite ya está."""
        assert settings.assessment_enabled is False
        assert _limites("assessment", "get_evaluacion")

    def test_google_callback(self) -> None:
        assert _valores("integraciones", "google_callback") == {"10 per 1 minute"}


class TestFranjaCredenciales:
    @pytest.mark.parametrize("modulo,funcion,esperado", [
        ("auth", "login", "5 per 1 minute"),
        ("auth", "refresh", "20 per 1 minute"),
        ("usuarios", "cambiar_password", "10 per 1 hour"),
    ])
    def test_limite(self, modulo: str, funcion: str, esperado: str) -> None:
        assert _valores(modulo, funcion) == {esperado}


class TestFranjaImport:
    ENDPOINTS = [
        ("importacion_nomina", "preview_nomina"),
        ("importacion_nomina", "confirmar_nomina"),
        ("importacion_nomina_empleados", "importar_nomina_empleados"),
        ("evaluaciones_import", "preview"),
        ("evaluaciones_import", "confirmar"),
    ]

    @pytest.mark.parametrize("modulo,funcion", ENDPOINTS)
    def test_valor(self, modulo: str, funcion: str) -> None:
        assert _valores(modulo, funcion) == {"10 per 1 hour"}

    @pytest.mark.parametrize("modulo,funcion", ENDPOINTS)
    def test_comparten_bucket(self, modulo: str, funcion: str) -> None:
        """shared_limit: los 5 consumen el mismo contador, no 10/hora cada uno."""
        assert {lim.scope for lim in _limites(modulo, funcion)} == {"import"}


class TestFranjaExport:
    ENDPOINTS = [
        ("empleados", "exportar_empleados"),
        ("vacaciones", "exportar_vacaciones"),
        ("ausencias", "exportar_ausencias"),
        ("ev_instancias", "exportar_instancias"),
        ("asignaciones_capacitacion", "exportar_asignaciones"),
        ("inventario_asignaciones", "exportar_asignaciones"),
        ("reportes", "exportar_reporte"),
    ]

    @pytest.mark.parametrize("modulo,funcion", ENDPOINTS)
    def test_valor(self, modulo: str, funcion: str) -> None:
        assert _valores(modulo, funcion) == {"30 per 1 hour"}

    @pytest.mark.parametrize("modulo,funcion", ENDPOINTS)
    def test_comparten_bucket(self, modulo: str, funcion: str) -> None:
        assert {lim.scope for lim in _limites(modulo, funcion)} == {"export"}

    @pytest.mark.parametrize("modulo,funcion", [
        ("objetivos", "exportar_objetivos"),
        ("inventario_items", "exportar_items"),
        ("evaluaciones_resultados", "exportar"),
    ])
    def test_los_tres_pendientes_siguen_sin_decorador(self, modulo: str, funcion: str) -> None:
        """Quedaron bajo el baseline porque el decorador los pasaba del límite de 80 líneas.
        Cuando esos routers se dividan, este test falla y recuerda agregarles la franja."""
        assert not _limites(modulo, funcion)


class TestFranjaCostoExterno:
    def test_generar_reporte(self) -> None:
        assert _valores("reportes", "generar_reporte") == {"20 per 1 hour"}


class TestBaseline:
    def test_valor(self) -> None:
        assert BASELINE == "300/minute"

    def test_aplica_a_los_no_decorados(self) -> None:
        assert [str(lim.limit) for grupo in limiter._default_limits for lim in grupo] == \
            ["300 per 1 minute"]

    def test_un_endpoint_cualquiera_no_tiene_decorador_propio(self) -> None:
        """Guarda del diseño: el baseline cubre por defecto, no hay que decorar todo."""
        assert not _limites("empleados", "list_empleados")
