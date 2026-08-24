"""
Los 5 ids de entrada que eran `str` y ahora son `UUID` (sesión 0.6, preparación del porteo).

## Por qué

Con el SDK de Supabase el id viaja como string y el tipo `str` no molesta. Con **asyncpg** el
UUID vuelve como objeto y un schema que declara `str` explota. Es el error #1 de la lista del dev
de infra, presente en dos de los tres proyectos que migró.

Y ya lo pagamos de este lado: `AreaCreate.empresa_id` era `str`, Pydantic aceptaba `""`, y
Postgres lo rechazaba con `22P02` → **500 en producción** por un pedido mal armado. Tipar el
campo mueve esa validación a la frontera, donde el error es 422 y es del pedido.

Los cinco:
  1. `NominaCreate.empleado_id`                          → POST /api/costos/nomina
  2. `FilaNominaPreview.empleado_id`                     → POST /api/importacion/nomina/confirmar
  3. `ImportacionNominaConfirmarRequest.empresa_id`      → idem
  4. `FilaObjetivoPreview.responsable_id`                → POST /api/importacion/objetivos/confirmar
  5. `ImportacionObjetivosConfirmarRequest.empresa_id`   → idem

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 TENDRÍAN QUE INSTANCIAR LOS SCHEMAS A MANO.** Es el error que dejó pasar el bug de
clientes: sus 30 tests construían el schema en Python, o sea empezaban **del lado de adentro de la
validación**, y nadie miraba el body que el front manda de verdad. Acá todo entra por **HTTP crudo
contra el app real**. Si un tipo vuelve a `str`, el body inválido pasa la validación y el test de
422 rojea.

**2. 🔴 EL 422 SOLO NO ALCANZA: FALTARÍA EL CASO POSITIVO.** Un schema que rechazara TODO haría
pasar los tests negativos. Por cada campo hay un caso con id bien formado que **verifica que el
valor llegó entero al otro lado**, no solo que no hubo 422.

**3. 🔴 LA SERIALIZACIÓN NO LA VE NINGÚN TEST DE HTTP.** El doble del service corta ANTES del
repo, así que el `str()` del payload no lo ejercita nadie por ese camino — es la pregunta de
"¿el fake ES lo que estoy probando?", y acá la respuesta es no. Por eso `TestLaSerializacion*`
llama a los **repos y services REALES** con un doble de `supabase_admin` que hace `json.dumps` en
el punto exacto donde el payload sale hacia PostgREST. Molde: `test_area_empresa_tipada.py`.

**4. 🔴 EL CONFIRMAR DE OBJETIVOS SE TRAGA LOS ERRORES POR FILA.** `confirmar` envuelve cada alta
en `except Exception` y la convierte en un `FilaObjetivoError`, así que **un TypeError adentro
devolvería 200 igual**. Un test que solo mirara el status pasaría con el bug vivo. Por eso se
afirma `importados` y `errores == []`, que es lo único que distingue "cargó" de "falló en silencio".
Es exactamente lo que habría pasado con `UUID(f.responsable_id)` sin tocar, porque
`UUID(objeto_uuid)` levanta TypeError.

⚠️ Se falsea la autenticación, no la autorización (molde: `test_usuario_estado.py`): el gate de
permisos corre de verdad, por eso el rol es `admin_rrhh`.
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
from uuid import UUID, uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import middleware.auth as auth_mod  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

EMPRESA = str(uuid4())
EMPLEADO = str(uuid4())
RESPONSABLE = str(uuid4())

# Los dos valores que el bug dejaba pasar: el vacío que mandaba el front en consolidado, y un
# texto cualquiera. Los dos tienen que morir en la frontera, no en Postgres.
MALOS = ["", "no-es-un-uuid"]


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: (str(uuid4()), "smoke@x.test"))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda user_id: EstadoUsuario(rol="admin_rrhh", activo=True))


def _cliente() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                             base_url="http://test")


async def _post(ruta: str, body: dict) -> httpx.Response:
    async with _cliente() as c:
        return await c.post(ruta, json=body, headers={"Authorization": "Bearer token-valido"})


# ─── 1. NominaCreate.empleado_id ─────────────────────────────────────────────

_RUTA_NOMINA = "/api/costos/nomina"


class _CostoServiceFalso:
    """Registra lo que RECIBE: así el caso positivo prueba que el body atravesó entero."""

    recibidos: list = []

    def cargar_nomina(self, data, empresa_id, usuario_id, rol=None):
        _CostoServiceFalso.recibidos.append(data)
        from schemas.costo import NominaResponse
        return NominaResponse(
            id=str(uuid4()), empleado_id=str(data.empleado_id), empresa_id=EMPRESA,
            empleado_nombre="Ana", area_nombre="Dev", mes=data.mes, anio=data.anio,
            monto_bruto=data.monto_bruto, monto_neto=data.monto_neto, total=data.monto_bruto,
        )


@pytest.fixture
def costos(auth):
    from routers.costos_escrituras import _service
    _CostoServiceFalso.recibidos = []
    main_mod.app.dependency_overrides[_service] = _CostoServiceFalso
    yield
    main_mod.app.dependency_overrides.clear()


def _body_nomina(empleado_id: str) -> dict:
    return {"empleado_id": empleado_id, "mes": 6, "anio": 2026,
            "monto_bruto": 1000.0, "monto_neto": 800.0}


class TestNominaCreateEmpleadoId:
    async def test_un_empleado_bien_formado_atraviesa(self, costos) -> None:
        r = await _post(_RUTA_NOMINA, _body_nomina(EMPLEADO))
        assert r.status_code == 201, r.text
        recibido = _CostoServiceFalso.recibidos[0]
        assert isinstance(recibido.empleado_id, UUID), "¿volvió a ser str?"
        assert str(recibido.empleado_id) == EMPLEADO

    @pytest.mark.parametrize("malo", MALOS)
    async def test_un_empleado_invalido_da_422_y_no_500(self, costos, malo) -> None:
        r = await _post(_RUTA_NOMINA, _body_nomina(malo))
        assert r.status_code == 422, f"'{malo}' pasó la validación (¿el tipo es str otra vez?)"
        assert r.status_code != 500
        assert r.json()["code"] == "VALIDACION_INVALIDA"
        assert _CostoServiceFalso.recibidos == [], "el id inválido llegó al service"


# ─── 2 y 3. El confirmar de nómina ───────────────────────────────────────────

_RUTA_IMP_NOMINA = "/api/importacion/nomina/confirmar"


class _NominaImportFalso:
    recibidos: list = []

    def confirmar(self, body, usuario_id=None):
        _NominaImportFalso.recibidos.append(body)
        from schemas.importacion import ImportacionNominaConfirmarResponse
        return ImportacionNominaConfirmarResponse(importados=len(body.filas), actualizados=0,
                                                  errores=[])


@pytest.fixture
def imp_nomina(auth):
    from routers.importacion_nomina import _service
    _NominaImportFalso.recibidos = []
    main_mod.app.dependency_overrides[_service] = _NominaImportFalso
    yield
    main_mod.app.dependency_overrides.clear()


def _fila_nomina(empleado_id: str) -> dict:
    return {"fila": 1, "dni": "30000001", "nombre_empleado": "Ana",
            "empleado_id": empleado_id, "anio": 2026, "mes": 6,
            "salario_bruto": 1000.0, "neto": 800.0, "es_actualizacion": False}


class TestConfirmarNomina:
    async def test_body_bien_formado_atraviesa(self, imp_nomina) -> None:
        r = await _post(_RUTA_IMP_NOMINA,
                        {"empresa_id": EMPRESA, "filas": [_fila_nomina(EMPLEADO)]})
        assert r.status_code == 200, r.text
        recibido = _NominaImportFalso.recibidos[0]
        assert isinstance(recibido.empresa_id, UUID)
        assert isinstance(recibido.filas[0].empleado_id, UUID)
        assert str(recibido.empresa_id) == EMPRESA
        assert str(recibido.filas[0].empleado_id) == EMPLEADO

    @pytest.mark.parametrize("malo", MALOS)
    async def test_empresa_id_invalido_da_422(self, imp_nomina, malo) -> None:
        r = await _post(_RUTA_IMP_NOMINA,
                        {"empresa_id": malo, "filas": [_fila_nomina(EMPLEADO)]})
        assert r.status_code == 422, f"'{malo}' pasó como empresa_id"
        assert _NominaImportFalso.recibidos == []

    @pytest.mark.parametrize("malo", MALOS)
    async def test_empleado_id_de_una_fila_invalido_da_422(self, imp_nomina, malo) -> None:
        """🔴 El id de ADENTRO de la lista. Es el que viaja de vuelta desde el cliente, así que
        es el más fácil de alterar y el que antes llegaba crudo hasta el upsert."""
        r = await _post(_RUTA_IMP_NOMINA,
                        {"empresa_id": EMPRESA, "filas": [_fila_nomina(malo)]})
        assert r.status_code == 422, f"'{malo}' pasó como empleado_id de la fila"
        assert _NominaImportFalso.recibidos == []


# ─── 4 y 5. El confirmar de objetivos ────────────────────────────────────────

_RUTA_IMP_OBJ = "/api/importacion/objetivos/confirmar"


class _ObjetivoServiceFalso:
    """Doble del ObjetivoService que consume el service REAL de import.

    🔴 Se falsea ACÁ y no el `ObjetivosImportService` entero, a propósito: `_a_create` —donde
    vivía el `UUID(...)` que había que sacar— es del service real. Falsearlo entero dejaría ese
    método sin ejercitar, que es justo lo que se quiere probar.
    """

    recibidos: list = []

    def create(self, data, usuario_id):
        _ObjetivoServiceFalso.recibidos.append(data)
        return SimpleNamespace(id=str(uuid4()))


@pytest.fixture
def imp_objetivos(auth):
    from routers.importacion_objetivos import _service
    from services.objetivos_import_service import ObjetivosImportService

    class _AuditFalso:
        def registrar(self, **kwargs) -> None: pass

    _ObjetivoServiceFalso.recibidos = []
    main_mod.app.dependency_overrides[_service] = lambda: ObjetivosImportService(
        objetivos=_ObjetivoServiceFalso(), audit=_AuditFalso())
    yield
    main_mod.app.dependency_overrides.clear()


def _fila_objetivo(responsable_id: str) -> dict:
    return {"fila": 1, "titulo": "Migrar nómina", "responsable": "ana@karstec.com",
            "responsable_id": responsable_id, "responsable_nombre": "Ana Gómez",
            "prioridad": "alta", "responsables_ids": []}


class TestConfirmarObjetivos:
    async def test_body_bien_formado_crea_el_objetivo(self, imp_objetivos) -> None:
        """🔴 NO alcanza con el 200: `confirmar` atrapa toda excepción por fila y la devuelve como
        error de esa fila. Con `UUID(objeto_uuid)` sin sacar, esto daría 200 con `importados=0`."""
        r = await _post(_RUTA_IMP_OBJ,
                        {"empresa_id": EMPRESA, "filas": [_fila_objetivo(RESPONSABLE)]})
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["importados"] == 1, f"la fila no se cargó: {cuerpo['errores']}"
        assert cuerpo["errores"] == []
        creado = _ObjetivoServiceFalso.recibidos[0]
        assert str(creado.responsable_id) == RESPONSABLE
        assert str(creado.empresa_id) == EMPRESA

    @pytest.mark.parametrize("malo", MALOS)
    async def test_empresa_id_invalido_da_422(self, imp_objetivos, malo) -> None:
        r = await _post(_RUTA_IMP_OBJ,
                        {"empresa_id": malo, "filas": [_fila_objetivo(RESPONSABLE)]})
        assert r.status_code == 422, f"'{malo}' pasó como empresa_id"
        assert _ObjetivoServiceFalso.recibidos == []

    @pytest.mark.parametrize("malo", MALOS)
    async def test_responsable_id_de_una_fila_invalido_da_422(self, imp_objetivos, malo) -> None:
        r = await _post(_RUTA_IMP_OBJ,
                        {"empresa_id": EMPRESA, "filas": [_fila_objetivo(malo)]})
        assert r.status_code == 422, f"'{malo}' pasó como responsable_id de la fila"
        assert _ObjetivoServiceFalso.recibidos == []


# ─── La serialización: la capa que los tests de HTTP no tocan ────────────────


class _SupabaseEspia:
    """Doble de `supabase_admin` que SERIALIZA lo que se le manda, como haría la red.

    🔴 ES LO QUE HACE FALSABLE EL `str()`. Un doble que solo guardara el dict aceptaría un objeto
    UUID sin chistar, y el test pasaría con la conversión borrada — que es exactamente lo que
    rompe en producción. Acá el `json.dumps` corre en el mismo punto donde corre de verdad: al
    salir el payload hacia PostgREST.

    ⚠️ `eq()` también valida: el lookup de `save_nomina` filtra por el `empleado_id`, y un UUID
    crudo ahí viaja en el querystring. Es la mitad del camino que en `areas` se había arreglado
    en `save` y olvidado en `update`.
    """

    def __init__(self, fila: dict) -> None:
        self.payloads: list = []
        self.filtros: list = []
        self._fila = fila
        self._una_sola = False   # `maybe_single()`/`single()` devuelven un dict, no una lista

    def table(self, _t):
        self._una_sola = False   # cada query arranca de cero
        return self

    def select(self, *a, **k): return self
    def order(self, *a, **k): return self

    def maybe_single(self):
        self._una_sola = True
        return self

    def single(self):
        self._una_sola = True
        return self

    def eq(self, campo, valor):
        json.dumps({campo: valor})   # TypeError si le pasan un UUID crudo
        self.filtros.append((campo, valor))
        return self

    def insert(self, payload):
        json.dumps(payload)
        self.payloads.append(payload)
        return self

    def upsert(self, payload, **k):
        json.dumps(payload)
        self.payloads.append(payload)
        return self

    def execute(self):
        return SimpleNamespace(data=self._fila if self._una_sola else [self._fila])


_FILA_NOMINA_DB = {
    "id": str(uuid4()), "empleado_id": EMPLEADO, "empresa_id": EMPRESA,
    "anio": 2026, "mes": 6, "salario_bruto": 1000.0, "cargas_sociales": 200.0,
    "total": 1200.0,
    "empleados": {"nombre": "Ana", "apellido": "Gómez", "areas": {"nombre": "Dev"}},
    "empresas": {"nombre": "ACME"},
}


class TestLaSerializacionDeNominaRepo:
    """`NominaCreate.empleado_id` es UUID → `save_nomina` tiene que convertirlo en los DOS usos."""

    def test_save_nomina_manda_el_uuid_serializado(self, monkeypatch) -> None:
        import repositories._nomina_write_repo as write_mod
        import repositories.nomina_repo as repo_mod
        from repositories.nomina_repo import NominaRepo
        from schemas.costo import NominaCreate
        espia = _SupabaseEspia(_FILA_NOMINA_DB)
        monkeypatch.setattr(repo_mod, "supabase_admin", espia)
        # `save_nomina` se mudo a su satelite al partir el repo (119/100): sin este segundo
        # parche el upsert sale a la red de verdad en vez de contra el espia.
        monkeypatch.setattr(write_mod, "supabase_admin", espia)

        NominaRepo().save_nomina(NominaCreate(empleado_id=UUID(EMPLEADO), mes=6, anio=2026,
                                              monto_bruto=1000.0, monto_neto=800.0))

        assert isinstance(espia.payloads[0]["empleado_id"], str)
        assert espia.payloads[0]["empleado_id"] == EMPLEADO

    def test_el_lookup_del_empleado_tambien_va_serializado(self, monkeypatch) -> None:
        """La otra mitad: el `.eq("id", ...)` que resuelve la empresa del empleado."""
        import repositories._nomina_write_repo as write_mod
        import repositories.nomina_repo as repo_mod
        from repositories.nomina_repo import NominaRepo
        from schemas.costo import NominaCreate
        espia = _SupabaseEspia(_FILA_NOMINA_DB)
        monkeypatch.setattr(repo_mod, "supabase_admin", espia)
        # `save_nomina` se mudo a su satelite al partir el repo (119/100): sin este segundo
        # parche el upsert sale a la red de verdad en vez de contra el espia.
        monkeypatch.setattr(write_mod, "supabase_admin", espia)

        NominaRepo().save_nomina(NominaCreate(empleado_id=UUID(EMPLEADO), mes=6, anio=2026,
                                              monto_bruto=1000.0, monto_neto=800.0))

        assert ("id", EMPLEADO) in espia.filtros


class TestLaSerializacionDelImportDeNomina:
    """🔴 Acá el dict NO lo arma el repo, lo arma el SERVICE, y el repo lo entrega tal cual.

    Por eso se corre el service REAL con el repo REAL: un test contra el repo solo pasaría el
    dict ya armado a mano, que es justo lo que no puede desmentir nada.
    """

    def test_el_lote_sale_con_los_uuid_convertidos(self, monkeypatch) -> None:
        import repositories.nomina_import_repo as repo_mod
        from repositories.nomina_import_repo import NominaImportRepo
        from schemas.importacion import FilaNominaPreview, ImportacionNominaConfirmarRequest
        from services.nomina_import_service import NominaImportService

        espia = _SupabaseEspia(_FILA_NOMINA_DB)
        monkeypatch.setattr(repo_mod, "supabase_admin", espia)

        class _AuditFalso:
            def registrar(self, **kwargs) -> None: pass

        body = ImportacionNominaConfirmarRequest(
            empresa_id=UUID(EMPRESA),
            filas=[FilaNominaPreview(fila=1, dni="30000001", nombre_empleado="Ana",
                                     empleado_id=UUID(EMPLEADO), anio=2026, mes=6,
                                     salario_bruto=1000.0, neto=800.0)],
        )
        NominaImportService(repo=NominaImportRepo(), audit=_AuditFalso()).confirmar(body, "u1")

        enviado = espia.payloads[0][0]
        assert isinstance(enviado["empleado_id"], str)
        assert isinstance(enviado["empresa_id"], str)
        assert enviado["empleado_id"] == EMPLEADO and enviado["empresa_id"] == EMPRESA


class TestElRepoDeObjetivosYaConvertia:
    """⚠️ Este es el FALSO POSITIVO del barrido, y queda escrito para que nadie lo "arregle".

    `objetivo_repo.save` construye el payload con `str(...)` campo por campo desde antes de esta
    sesión, así que tipar el schema no le agregó nada que hacer. Lo que sí hubo que tocar fue
    `_a_create`, que convertía DE MÁS. El test existe para que, si alguien saca esos `str()`
    creyendo que sobran, salte acá.
    """

    def test_save_manda_los_uuid_serializados(self, monkeypatch) -> None:
        import repositories.objetivo_repo as repo_mod
        from repositories.objetivo_repo import ObjetivoRepo
        from schemas.objetivo import ObjetivoCreate

        fila = {"id": str(uuid4()), "empresa_id": EMPRESA, "responsable_id": RESPONSABLE,
                "titulo": "X", "prioridad": "alta"}
        espia = _SupabaseEspia(fila)
        monkeypatch.setattr(repo_mod, "supabase_admin", espia)
        monkeypatch.setattr(repo_mod, "set_responsables", lambda *a, **k: None)
        monkeypatch.setattr(ObjetivoRepo, "find_by_id", lambda self, _id: None)

        ObjetivoRepo().save(ObjetivoCreate(empresa_id=UUID(EMPRESA),
                                           responsable_id=UUID(RESPONSABLE),
                                           titulo="X", prioridad="alta"))

        enviado = espia.payloads[0]
        assert isinstance(enviado["empresa_id"], str)
        assert isinstance(enviado["responsable_id"], str)
