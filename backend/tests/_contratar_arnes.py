"""
El ARNÉS HTTP del puente candidato → empleado: el app mínimo y el cliente.

Helper, no test. Lo consume `tests/test_candidato_contratar.py`.

📄 **EL PADRÓN vive en `tests/_contratar_padron.py`** (qué candidatos y qué vacantes existen) y
**LOS FAKES en `tests/_contratar_fakes.py`** (qué responde cada colaborador, y por qué los cuatro
honran `empresa_id`). Tres archivos porque juntos daban 215/200, y cada uno responde una pregunta
distinta: qué datos hay · qué responde cada colaborador · cómo se le pega al endpoint.

═══════════════════════════════════════════════════════════════════════════════════════════
⚠️ EL APP DE TESTS ES MÍNIMO Y ESO ESTÁ MEDIDO, NO ASUMIDO
═══════════════════════════════════════════════════════════════════════════════════════════
Se monta el **router real** sobre un `FastAPI` desnudo, con los **handlers de error reales**
(`global_error_handler` y `validation_error_handler`). Lo que NO corre es `AuthMiddleware`: la
suite no tiene fixture de JWT y llegar por el app real exigiría falsear JWKS y `empresas_cache`
(está declarado así en `test_estado_preingreso_padron.py` y en `test_rate_limit.py`, donde
assessment es "la única superficie alcanzable sin JWT válido").

**Qué cubre igual, que es lo que importa acá:** el binding del body por Pydantic (y su 422), el
match de la ruta, el `status_code=201`, la serialización del `EmpleadoResponse` y —sobre todo—
el contrato `{error, message, code}` de cada guarda, que es lo que el front consume.
**Qué NO cubre, dicho sin maquillar:** el `AuthMiddleware` y el gate de permisos. Que la ruta
esté montada en el app REAL, con su prefijo y sin que otra la capture, se verifica aparte por
introspección de `main.app.routes` — que es como lo hacen `test_paridad_list_export` y
`test_callers_huerfanos`.

🔴 LA EMPRESA SE INYECTA EN `request.state.empresa_id`, NO COMO HEADER. `get_empresa_id` lee el
state que deja `AuthMiddleware`, no el `X-Empresa-Id` crudo: mandar el header sin el middleware
que lo resuelve dejaría `empresa_id=None` en TODOS los tests, o sea el modo consolidado siempre,
y los casos de barrera de empresa pasarían en verde por el motivo equivocado.
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

from datetime import date  # noqa: E402
from typing import Optional  # noqa: E402

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402

import routers.candidatos_escrituras as router_mod  # noqa: E402
from middleware.error_handler import global_error_handler, validation_error_handler  # noqa: E402
from tests._contratar_padron import EMPRESA_A, MANANA, USUARIO  # noqa: E402
from utils.errors import AppError  # noqa: E402


def app_con(service, empresa=EMPRESA_A) -> FastAPI:
    """App mínima con el ROUTER REAL y los HANDLERS REALES. Ver el encabezado para qué no cubre.

    `empresa=None` = modo CONSOLIDADO, que es lo que deja `AuthMiddleware` cuando el selector del
    sidebar dice "Todas las empresas". No es un caso de borde: es el que hace que la barrera del
    header NO restrinja, y por eso el service tiene que resolver la vacante y el alta con la
    empresa del CANDIDATO.
    """
    app = FastAPI()

    @app.middleware("http")
    async def _inyectar_estado(request, call_next):
        # Exactamente lo que AuthMiddleware deja en `request.state`, sin JWKS. `empresa_id` va
        # como str o None, que es la forma que `get_empresa_id` espera.
        request.state.user = {"id": USUARIO, "rol": "admin_rrhh"}
        request.state.empresa_id = empresa
        return await call_next(request)

    app.include_router(router_mod.router, prefix="/api/candidatos")
    app.add_exception_handler(AppError, global_error_handler)
    app.add_exception_handler(Exception, global_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.dependency_overrides[router_mod._contratacion_svc] = lambda: service
    return app


def cliente(app: FastAPI) -> httpx.AsyncClient:
    """Cliente HTTP sobre el app. La empresa la fija `app_con`, no el cliente: ver su docstring."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def body(*, email: str = "ana.perez@karstec.com", roles=None,
         fecha: Optional[date] = None) -> dict:
    """El body del endpoint. Defaults = camino feliz; cada test cambia UNA cosa."""
    return {"email_corporativo": email, "roles": roles or ["Analista"],
            "fecha_ingreso": (fecha or MANANA).isoformat()}
