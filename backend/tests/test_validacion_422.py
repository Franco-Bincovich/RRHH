"""
El 422 de validación sale con el contrato `{error, message, code}`, no con el `detail` de Pydantic.

## Qué se rompía

`main.py` registraba handlers para `AppError` y para `Exception`, y NINGUNO de los dos cubre
`RequestValidationError`: Starlette manda el de `Exception` al `ServerErrorMiddleware` y FastAPI
conserva el suyo propio para validación. Así que todo 422 salía como `{"detail": [...]}`, sin
`message` ni `code` — y `toApiError` (`frontend/services/api.ts`, embudo ÚNICO de `apiFetch`,
`postMultipart` y `descargarArchivo`) busca exactamente esas dos claves, no las encontraba y caía
a `"Error del servidor"` / `"UNKNOWN"`. **Cualquier 422 de cualquier endpoint se mostraba como un
error del servidor en las 27 pantallas**, que además es falso: un 422 es un problema del pedido.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 El app tendría que ser un `FastAPI()` armado por el test.** Es el punto que decide todo:
un app propio con `add_exception_handler` adentro del test PASA aunque `main.py` nunca registre
nada — y la omisión en `main.py` era el bug entero. Por eso `TestElAppRealLoRegistra` pega contra
`main.app` y usa `/api/auth/login`, que es pública (no hace falta token) y rechaza el body ANTES
de tocar Supabase, así que no hay red de por medio. El app de sonda de `TestElMensaje` existe solo
para las formas que ningún endpoint real produce (anidamiento, query params), y no sustituye al
anterior.

**2. La aserción tendría que mirar solo el status.** Un 422 seguiría siendo 422 con el `detail`
crudo: lo que hay que afirmar es el BODY, clave por clave, y que `detail` NO esté.

**3. `TestNoSeFiltra` tendría que buscar el valor recibido y ya.** Busca además el `loc`, el
`type`, el `msg` y la `url` de Pydantic, que son las cuatro cosas que el criterio de
`middleware/error_handler.py` decidió no exponer. Con una sola de las cuatro, un handler que
filtrara las otras tres pasaría.

**4. El caso del body vacío tendría que no estar.** Con solo el caso "un campo mal", un handler
que devolviera siempre el mensaje genérico pasaría — y el genérico es justamente lo que NO sirve.
Se afirman las dos ramas: con campos identificables se nombran, sin ellos se cae al genérico.

**5. 🔴 Las dos RAMAS DE ORIGEN tendrían que probarse con el mismo request.** `TestRamaBody` y
`TestRamaPedido` afirman cosas OPUESTAS —una exige que el campo se nombre, la otra exige que NO
aparezca— sobre requests distintos. Colapsar las dos ramas en el código rompe las dos clases: la
que espera el nombre deja de encontrarlo, y la que lo prohíbe lo encuentra. Con una sola clase,
una rama viviría sin que nada la mire.

**6. El test del `page_size` tendría que pegarle a la sonda.** Le pega a `/api/auditoria` en el
app REAL, que es donde vive el `le=100` que quemó dos veces. Un `Query(le=100)` inventado en la
sonda probaría el handler pero no que un endpoint de verdad caiga en la rama correcta.

⚠️ NO se falsea la autorización, solo la AUTENTICACIÓN (el JWT y el estado del usuario, molde:
`test_usuario_estado.py`). El gate de permisos corre de verdad: por eso el rol es `admin_rrhh`.
Y la validación del query corta ANTES del handler del endpoint, así que no se toca la base.
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

import json  # noqa: E402
from pathlib import Path  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI, Query  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import main as main_mod  # noqa: E402
import middleware.auth as auth_mod  # noqa: E402
from middleware.error_handler import validation_error_handler  # noqa: E402
from utils.rate_limit import limiter  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

CLAVES = {"error", "message", "code"}
CODE = "VALIDACION_INVALIDA"
CODE_PEDIDO = "PEDIDO_INVALIDO"

CONTRATO_422_BODY = {
    "error": True,
    "message": "Revisá los datos del formulario: empresa (falta).",
    "code": "VALIDACION_INVALIDA",
}
CONTRATO_422_QUERY = {
    "error": True,
    "message": "No se pudo completar el pedido. Actualizá la pantalla y volvé a intentar.",
    "code": "PEDIDO_INVALIDO",
}

# 🔗 EL PUENTE CON EL FRONT. `TestContratoPublicado` captura las respuestas REALES del app y las
# deja acá; `frontend/services/api.test.ts` lee ESTE archivo y se las da de comer a `toApiError`.
#
# 🔴 POR QUÉ UN ARCHIVO Y NO LA MISMA CONSTANTE ESCRITA DE LOS DOS LADOS. Con el body copiado a
# mano en el test del front, renombrar `message` a `mensaje` en el handler rojea SOLO el backend:
# el front sigue comiendo su propia copia y pasa feliz. O sea que el test del front no tocaría el
# contrato, que es justo lo que tiene que tocar. Alimentándolo con lo que el backend EMITE de
# verdad, un cambio de un solo lado rompe el otro. Es la misma doctrina de siempre: un test que
# se alimenta de su propia constante afirma algo sobre sí mismo.
CONTRATO_PUBLICADO = Path(__file__).parent / "_contrato_errores.json"


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def sesion_valida(monkeypatch):
    """Da por buena la AUTENTICACIÓN para poder llegar a la validación de un endpoint real.

    Falsea solo el JWT y el estado del usuario (molde: `test_usuario_estado.py`). El gate de
    permisos NO se toca: corre de verdad, y por eso el rol tiene que alcanzar. La validación del
    query/path corta antes del handler, así que la base nunca se consulta.
    """
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: str(uuid4()))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)

    def _con(estado: EstadoUsuario):
        monkeypatch.setattr(auth_mod, "estado_usuario", lambda user_id: estado)
    return _con


@pytest.fixture(autouse=True)
def _sin_rate_limit():
    """Login está limitado a 5/min y estos tests lo golpean varias veces. El contador se limpia
    antes de cada uno: lo que se mide acá es la validación, no la franja (esa es de test_rate_limit)."""
    limiter.reset()
    yield
    limiter.reset()


# ─── El cableado real ─────────────────────────────────────────────────────────


class TestElAppRealLoRegistra:
    """🔴 EL BLOQUE QUE IMPORTA: contra `main.app`, no contra un app de mentira."""

    def test_el_handler_registrado_es_el_nuestro(self) -> None:
        assert main_mod.app.exception_handlers.get(RequestValidationError) is validation_error_handler

    async def test_un_body_invalido_devuelve_el_contrato(self) -> None:
        """`/api/auth/login` es pública y el 422 corta antes de Supabase: sin token y sin red."""
        async with _client(main_mod.app) as c:
            r = await c.post("/api/auth/login", json={})
        assert r.status_code == 422
        body = r.json()
        assert set(body) == CLAVES, f"el body no cumple el contrato: {body}"
        assert body["error"] is True
        assert body["code"] == CODE
        assert "username" in body["message"] and "password" in body["message"]

    async def test_ya_no_sale_el_detail_de_pydantic(self) -> None:
        async with _client(main_mod.app) as c:
            r = await c.post("/api/auth/login", json={"username": 123})
        assert "detail" not in r.json()

    async def test_el_front_lo_lee_sin_caer_al_generico(self) -> None:
        """Simula `toApiError` tal cual: `body.message ?? "Error del servidor"`, idem `code`."""
        async with _client(main_mod.app) as c:
            r = await c.post("/api/auth/login", json={"username": "x"})
        body = r.json()
        assert body.get("message", None) not in (None, "Error del servidor")
        assert body.get("code", None) not in (None, "UNKNOWN")


# ─── Las formas del mensaje ───────────────────────────────────────────────────


class _Anidado(BaseModel):
    fecha_desde: str


class _Cuerpo(BaseModel):
    empresa_id: UUID
    nombre: str = Field(..., max_length=120)
    items: list[_Anidado] | None = None


@pytest.fixture
def sonda() -> FastAPI:
    """App mínima para las formas que ningún endpoint público produce (anidamiento, query).

    NO reemplaza a `TestElAppRealLoRegistra`: acá el handler se registra a mano, así que este app
    pasaría aunque `main.py` no lo registrara. Lo que se mide es el TEXTO, no el cableado.
    """
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # Body Y query en el MISMO endpoint: es la única forma de producir un `loc` mixto.
    @app.post("/sonda")
    async def _post(body: _Cuerpo, orden: int = Query(1, le=5)):  # pragma: no cover
        return {"ok": True}

    @app.get("/sonda")
    async def _get(page_size: int = Query(20, ge=1, le=100)):  # pragma: no cover
        return {"ok": True}

    return app


class TestRamaBody:
    """Lo llenó una PERSONA: se nombra el campo y se le pide corregirlo."""

    async def test_el_caso_de_produccion_de_clientes(self, sonda) -> None:
        """El body exacto que mandaba ClienteModal con el sidebar en 'Todas las empresas'."""
        async with _client(sonda) as c:
            r = await c.post("/sonda", json={"empresa_id": "", "nombre": "Acme S.A."})
        assert r.json() == CONTRATO_422_BODY

    async def test_traduce_el_problema_y_no_vuelca_pydantic(self, sonda) -> None:
        async with _client(sonda) as c:
            r = await c.post("/sonda", json={"empresa_id": "no-uuid", "nombre": "x" * 200})
        assert r.json()["message"] == (
            "Revisá los datos del formulario: empresa (tiene un formato inválido), "
            "nombre (es demasiado largo)."
        )
        assert r.json()["code"] == CODE

    async def test_un_body_sin_campos_identificables_cae_al_generico(self, sonda) -> None:
        """`loc` es solo `("body",)`: no hay campo que nombrar, y no se inventa uno. Sigue siendo
        de la rama BODY —el body lo mandó el formulario—, así que conserva su code."""
        async with _client(sonda) as c:
            r = await c.post("/sonda", content=b"{roto", headers={"Content-Type": "application/json"})
        assert r.json()["message"] == (
            "El pedido tiene datos inválidos. Revisá el formulario e intentá de nuevo.")
        assert r.json()["code"] == CODE

    async def test_del_anidado_sale_la_hoja_y_no_el_camino(self, sonda) -> None:
        """`body.items.0.fecha_desde` → "fecha desde". El índice y el submodelo describen el
        schema por dentro; la hoja es lo único que le sirve a quien completa el formulario."""
        async with _client(sonda) as c:
            r = await c.post("/sonda", json={
                "empresa_id": "8f3b1e2a-0000-4a1b-9c2d-111122223333",
                "nombre": "Acme", "items": [{}]})
        mensaje = r.json()["message"]
        assert mensaje == "Revisá los datos del formulario: fecha desde (falta)."
        assert "items" not in mensaje and "0" not in mensaje

    async def test_loc_mixto_gana_body(self, sonda) -> None:
        """🔴 body + query en el MISMO request. Gana body porque es la rama accionable: si hay
        algo que la persona puede arreglar, esa información vale más que el aviso genérico.
        El `orden` inválido queda solo en el log."""
        async with _client(sonda) as c:
            r = await c.post("/sonda", params={"orden": 99},
                             json={"empresa_id": "", "nombre": "Acme S.A."})
        assert r.json() == CONTRATO_422_BODY
        assert "orden" not in r.json()["message"]


class TestRamaPedido:
    """Lo armó la APLICACIÓN: NO se nombra el campo y no se le pide corregir nada."""

    async def test_query_invalido_no_nombra_el_campo(self, sonda) -> None:
        async with _client(sonda) as c:
            r = await c.get("/sonda", params={"page_size": 200})
        assert r.json() == CONTRATO_422_QUERY

    async def test_el_page_size_200_contra_un_endpoint_real(self, sesion_valida) -> None:
        """🔴 LA QUEMADA, EN EL APP DE VERDAD. `useDestinatarios` y `useCandidatosProyecto`
        pedían `page_size=200` contra el `le=100` de los routers paginados y la pantalla decía
        'no hay datos' con la base llena. `/api/auditoria` es uno de esos seis.

        El usuario NO tipeó ese 200 en ningún lado: lo puso el front. Por eso el mensaje no
        nombra el campo — pedirle que corrija "page size" lo manda a buscar un input que no
        existe."""
        sesion_valida(EstadoUsuario(rol="admin_rrhh", activo=True))
        async with _client(main_mod.app) as c:
            r = await c.get("/api/auditoria", params={"page_size": 200},
                            headers={"Authorization": "Bearer token-valido"})
        assert r.status_code == 422
        assert r.json() == CONTRATO_422_QUERY
        assert "page" not in r.json()["message"]

    async def test_path_invalido_tampoco_nombra_el_campo(self, sesion_valida) -> None:
        """Un UUID mal formado en la URL lo compuso el front con un id que ya tenía."""
        sesion_valida(EstadoUsuario(rol="admin_rrhh", activo=True))
        async with _client(main_mod.app) as c:
            r = await c.get("/api/empleados/no-es-un-uuid",
                            headers={"Authorization": "Bearer token-valido"})
        assert r.status_code == 422
        assert r.json() == CONTRATO_422_QUERY


# ─── El puente con el front ───────────────────────────────────────────────────


class TestContratoPublicado:
    """Captura lo que el app EMITE de verdad y lo publica para `frontend/services/api.test.ts`.

    🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO FALLE? Que los cuerpos se escribieran a mano
    en vez de capturarse. Salen de tres requests REALES contra el app real (dos 422 y un 401 de
    control), así que el archivo no puede quedar diciendo algo que el backend ya no manda. El
    mismo test afirma además que coinciden con lo esperado: si solo publicara, un handler roto
    publicaría su propio error y el front lo tomaría como la verdad nueva.
    """

    async def test_captura_y_publica(self, sonda, sesion_valida) -> None:
        sesion_valida(EstadoUsuario(rol="admin_rrhh", activo=True))
        async with _client(sonda) as c:
            body_422 = (await c.post("/sonda", json={"empresa_id": "", "nombre": "Acme S.A."})).json()
        async with _client(main_mod.app) as c:
            query_422 = (await c.get("/api/auditoria", params={"page_size": 200},
                                     headers={"Authorization": "Bearer token-valido"})).json()
            # Control: un AppError que NO es 422 y que ya funcionaba antes de este arreglo.
            no_autorizado = (await c.get("/api/auditoria")).json()

        publicado = {
            "_leeme": "GENERADO por backend/tests/test_validacion_422.py. No editar a mano.",
            "422_body": body_422,
            "422_query": query_422,
            "401_control": no_autorizado,
        }
        CONTRATO_PUBLICADO.write_text(
            json.dumps(publicado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        assert body_422 == CONTRATO_422_BODY
        assert query_422 == CONTRATO_422_QUERY
        assert set(no_autorizado) == CLAVES and no_autorizado["code"] == "MISSING_TOKEN"


# ─── Lo que no puede salir ────────────────────────────────────────────────────


class TestNoSeFiltra:
    """El criterio completo está en `middleware/error_handler.py`; acá se verifica."""

    async def test_ni_estructura_ni_jerga_ni_el_valor_recibido(self, sonda) -> None:
        secreto = "hunter2-el-valor-que-mando-el-cliente"
        async with _client(sonda) as c:
            r = await c.post("/sonda", json={"empresa_id": secreto, "nombre": "Acme"})
        cuerpo = r.text
        # El VALOR: puede ser una contraseña, un DNI o un sueldo — el campo que falla puede ser
        # justamente el sensible.
        assert secreto not in cuerpo
        # La ESTRUCTURA y la JERGA de Pydantic.
        for prohibido in ("detail", "loc", "uuid_parsing", "url", "pydantic", "body."):
            assert prohibido not in cuerpo, f"se filtró {prohibido!r}: {cuerpo}"

    async def test_el_log_lleva_el_diagnostico_pero_nunca_el_valor(self, sonda, caplog) -> None:
        """🔴 El `input` tampoco va al LOG: un `password` mal formado escribiría la contraseña en
        claro en los logs de la plataforma. Van el `loc` completo y el `type`, que es lo que un
        dev necesita. Mismo criterio que el WARNING de `_oauth_state.consumir`."""
        secreto = "hunter2-el-valor-que-mando-el-cliente"
        with caplog.at_level("WARNING", logger="hrkarstec"):
            async with _client(sonda) as c:
                await c.post("/sonda", json={"empresa_id": secreto, "nombre": "Acme"})
        registros = [r for r in caplog.records if r.getMessage() == "Validación de request rechazada"]
        assert len(registros) == 1, "el 422 tiene que dejar UNA entrada de diagnóstico"
        errores = registros[0].errores
        assert errores == [{"loc": "body.empresa_id", "type": "uuid_parsing"}]
        assert secreto not in str(errores)

    async def test_la_rama_de_pedido_loguea_igual_de_completo(self, sonda, caplog) -> None:
        """🔴 Al usuario no se le nombra el campo, PERO el log lo lleva entero — si no, la rama
        que el usuario no puede diagnosticar sería también la que el dev no puede diagnosticar,
        y un `page_size` mal serializado quedaría invisible en los dos lados."""
        with caplog.at_level("WARNING", logger="hrkarstec"):
            async with _client(sonda) as c:
                await c.get("/sonda", params={"page_size": 200})
        registros = [r for r in caplog.records if r.getMessage() == "Validación de request rechazada"]
        assert len(registros) == 1
        assert registros[0].levelname == "WARNING"
        assert registros[0].errores == [
            {"loc": "query.page_size", "type": "less_than_equal"}]
        # El `input` tampoco va acá: es la MISMA regla en las dos ramas.
        assert "200" not in str(registros[0].errores)
