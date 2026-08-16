"""
`AreaCreate.empresa_id` es UUID, no str — y el 500 pasa a ser 422.

## Qué se rompía

`schemas/area.py:12` declaraba `empresa_id: str`. El front mandaba `""` con el sidebar en
"Todas las empresas" (`AreaModal` sembraba `empresaId ?? getEmpresaActivaId() ?? ""` y no
validaba nada), Pydantic lo ACEPTABA por ser un str válido, y el `""` llegaba hasta Postgres, que
lo rechazaba con `22P02 invalid input syntax for type uuid` → **500**.

Es el mismo bug del `empresa_id: ""` de clientes con un agravante: allá el schema tipaba UUID y
salía un 422 (feo pero honesto); acá el tipo `str` movía la validación de la frontera al motor de
base de datos, donde el error ya no es del pedido sino del servidor.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 TENDRÍAN QUE INSTANCIAR `AreaCreate` A MANO.** Es exactamente el error que dejó pasar el
bug de clientes: los 30 tests de aquel módulo construían el schema en Python, o sea empezaban
**del lado de adentro de la validación**, y el body que el front manda de verdad no lo miraba
nadie. Acá se manda un **body HTTP crudo** con `empresa_id: ""` contra el app REAL. Si el tipo
vuelve a `str`, el request pasa la validación y esto rojea.

**2. El test tendría que afirmar solo el status.** Un `""` mal tipado también podría dar 422 por
otro motivo, así que se afirma el CONTRATO completo (`code`, y que el mensaje nombre el campo) —
que es lo que el usuario termina leyendo.

**3. Faltaría el caso POSITIVO.** Con solo "el vacío se rechaza", un schema que rechazara TODO
pasaría. Se manda también un UUID bien formado y se verifica que **pasa la validación** (llega al
service, que es hasta donde este test mira).

⚠️ NO se falsea la autorización, solo la autenticación (molde: `test_usuario_estado.py`). El gate
de permisos corre de verdad: por eso el rol es `admin_rrhh`.
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
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import middleware.auth as auth_mod  # noqa: E402
from routers.areas_escrituras import _service  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

_RUTA = "/api/areas"
EMPRESA = str(uuid4())


class _ServicioFalso:
    """Doble del service. Registra lo que RECIBE: así el caso positivo prueba que el body
    ATRAVESÓ la validación y llegó entero, no solo que no dio 422."""

    recibidos: list = []

    def create_area(self, data, created_by):
        _ServicioFalso.recibidos.append(data)
        from datetime import UTC, datetime
        from schemas.area import AreaResponse
        return AreaResponse(id=str(uuid4()), empresa_id=str(data.empresa_id), nombre=data.nombre,
                            descripcion=None, responsable_id=None, responsable_nombre=None,
                            activo=True, cantidad_empleados=0,
                            created_at=datetime.now(UTC), updated_at=None)


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: str(uuid4()))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda user_id: EstadoUsuario(rol="admin_rrhh", activo=True))
    _ServicioFalso.recibidos = []
    main_mod.app.dependency_overrides[_service] = _ServicioFalso
    yield httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                            base_url="http://test")
    main_mod.app.dependency_overrides.clear()


async def _post(cliente, body: dict) -> httpx.Response:
    async with cliente as c:
        return await c.post(_RUTA, json=body,
                            headers={"Authorization": "Bearer token-valido"})


class TestResponsableIdTambienEsUUID:
    """`responsable_id` es `UUID | None` — opcional, pero tipado.

    🔴 EL QUE CAZA EL `mode="json"`. La serialización vive en `area_repo`, no en el schema: un
    test que armara el dict a mano NO puede ver que `model_dump()` pelado devuelve el objeto UUID
    y revienta al insertar. Por eso el alta con responsable va por HTTP y llega hasta el service,
    que es donde el payload ya pasó por el repo real en el camino de producción.
    """

    async def test_un_responsable_bien_formado_atraviesa(self, cliente) -> None:
        resp = str(uuid4())
        r = await _post(cliente, {"empresa_id": EMPRESA, "nombre": "Sistemas",
                                  "responsable_id": resp})
        assert r.status_code == 201, r.text
        assert str(_ServicioFalso.recibidos[0].responsable_id) == resp

    async def test_un_responsable_vacio_da_422_y_no_500(self, cliente) -> None:
        r = await _post(cliente, {"empresa_id": EMPRESA, "nombre": "Sistemas",
                                  "responsable_id": ""})
        assert r.status_code == 422, "¿volvió a ser str?"
        assert r.json()["code"] == "VALIDACION_INVALIDA"
        assert _ServicioFalso.recibidos == []

    async def test_sin_responsable_sigue_andando(self, cliente) -> None:
        """Es OPCIONAL: sin él, un `UUID` a secas (no `UUID | None`) rompería el alta normal."""
        r = await _post(cliente, {"empresa_id": EMPRESA, "nombre": "Sistemas"})
        assert r.status_code == 201, r.text
        assert _ServicioFalso.recibidos[0].responsable_id is None


class _SupabaseEspia:
    """Doble de `supabase_admin` que SERIALIZA lo que se le manda, como haría la red.

    🔴 ES LO QUE HACE FALSABLE EL `mode="json"`. Un doble que solo guardara el dict aceptaría un
    objeto UUID sin chistar, y el test pasaría con el `mode="json"` borrado — que es exactamente
    lo que rompe en producción. Acá el `json.dumps` corre en el mismo punto donde corre de verdad:
    al salir el payload hacia PostgREST.
    """

    def __init__(self) -> None:
        self.payloads: list = []

    def table(self, _t): return self
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def neq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def maybe_single(self): return self

    def insert(self, payload):
        json.dumps(payload)          # levanta TypeError si quedó un UUID sin convertir
        self.payloads.append(payload)
        return self

    def update(self, payload):
        json.dumps(payload)
        self.payloads.append(payload)
        return self

    def execute(self):
        return SimpleNamespace(data=[{
            "id": str(uuid4()), "empresa_id": str(uuid4()), "nombre": "X",
            "descripcion": None, "responsable_id": None, "activo": True,
            "created_at": "2026-08-10T00:00:00+00:00",
        }])


class TestLaSerializacionDelRepo:
    """🔴 LA CAPA QUE EL TEST DE HTTP NO TOCA.

    El doble del service corta ANTES del repo, así que el `mode="json"` no lo ejercita nadie por
    ese camino. Es la pregunta de L9 —¿el fake ES lo que estoy probando?— y acá la respuesta es
    no: la serialización vive en `area_repo`, así que hay que llamar al repo REAL.
    """

    def test_save_manda_los_uuid_serializados(self, monkeypatch) -> None:
        import repositories._area_row as row_mod
        import repositories.area_repo as repo_mod
        from repositories.area_repo import AreaRepo
        from schemas.area import AreaCreate
        espia = _SupabaseEspia()
        monkeypatch.setattr(repo_mod, "supabase_admin", espia)
        # El conteo por área y el mapper se mudaron a `_area_row` al partir el repo
        # (100/100): sin este segundo parche, `_counts_by_area` sale a la red de verdad.
        monkeypatch.setattr(row_mod, "supabase_admin", espia)

        AreaRepo().save(AreaCreate(empresa_id=uuid4(), nombre="X", responsable_id=uuid4()))

        enviado = espia.payloads[0]
        assert isinstance(enviado["empresa_id"], str)
        assert isinstance(enviado["responsable_id"], str)

    def test_update_manda_los_uuid_serializados(self, monkeypatch) -> None:
        import repositories._area_row as row_mod
        import repositories.area_repo as repo_mod
        from repositories.area_repo import AreaRepo
        from schemas.area import AreaUpdate
        espia = _SupabaseEspia()
        monkeypatch.setattr(repo_mod, "supabase_admin", espia)
        # El conteo por área y el mapper se mudaron a `_area_row` al partir el repo
        # (100/100): sin este segundo parche, `_counts_by_area` sale a la red de verdad.
        monkeypatch.setattr(row_mod, "supabase_admin", espia)

        AreaRepo().update(str(uuid4()), AreaUpdate(responsable_id=uuid4()))

        assert isinstance(espia.payloads[0]["responsable_id"], str)


class TestElVacioEsUn422YNoUn500:
    async def test_empresa_id_vacio_da_422_con_el_contrato(self, cliente) -> None:
        """🔴 EL BODY EXACTO que mandaba `AreaModal` con el sidebar en consolidado."""
        r = await _post(cliente, {"empresa_id": "", "nombre": "Sistemas"})

        assert r.status_code == 422, "volvió a aceptar el vacío (¿el tipo es str otra vez?)"
        body = r.json()
        assert set(body) == {"error", "message", "code"}
        assert body["code"] == "VALIDACION_INVALIDA"
        assert "empresa" in body["message"]
        assert _ServicioFalso.recibidos == [], "el vacío llegó al service"

    async def test_nunca_es_500(self, cliente) -> None:
        """La distinción que motiva la sesión: un pedido mal armado NO es un error del servidor.
        Con `empresa_id: str`, este mismo body salía como 500 desde Postgres."""
        r = await _post(cliente, {"empresa_id": "", "nombre": "Sistemas"})
        assert r.status_code != 500

    async def test_un_uuid_mal_formado_tambien_rebota_antes_de_la_base(self, cliente) -> None:
        r = await _post(cliente, {"empresa_id": "no-es-un-uuid", "nombre": "Sistemas"})
        assert r.status_code == 422
        assert _ServicioFalso.recibidos == []

    async def test_un_uuid_valido_si_atraviesa(self, cliente) -> None:
        """🔴 EL CASO POSITIVO. Sin él, un schema que rechazara TODO pasaría los tres de arriba.
        Se afirma que el body llegó al service ENTERO, no solo que no dio 422."""
        r = await _post(cliente, {"empresa_id": EMPRESA, "nombre": "Sistemas"})

        assert r.status_code == 201, r.text
        assert len(_ServicioFalso.recibidos) == 1
        recibido = _ServicioFalso.recibidos[0]
        assert str(recibido.empresa_id) == EMPRESA
        assert recibido.nombre == "Sistemas"
