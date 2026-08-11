"""
Clientes como catálogo GLOBAL (migración 108). Reemplaza lo que la barrera de empresa cubría.

Corre contra el `ClienteRepo` REAL sobre el doble de tabla (`tests/_almacen_tabla.Almacen`), igual
que `test_clientes_abm.py`: lo que se quiere probar es la cadena entera —el service llama, el repo
arma la query, el doble la ejecuta— y un repo falso convertiría la ausencia de filtro en una
constante del test. Lo único falseado es `AuditService`, porque un evento hay que capturarlo.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 EL ALMACÉN TENDRÍA QUE MODELAR UNA SOLA EMPRESA.** Modela DOS, con un cliente en cada
una, y las filas CONSERVAN su `empresa_id` (la 108 no borra la columna). Eso es lo que hace
falsable "el catálogo es global": si el repo volviera a filtrar, el listado traería 1 en vez de 2
y `find_by_id` del ajeno daría `None`. Con una sola empresa, "no filtra" y "filtra bien" serían
indistinguibles — que es el caso #1 de la doctrina del repo, al revés.

**2. 🔴 LAS FILAS TENDRÍAN QUE NACER CON `empresa_id` NULL.** Nacen con una empresa REAL cargada,
y por eso `TestAuditoriaSinEmpresa` puede desmentir: hay un valor concreto disponible en la fila,
así que un payload que lo leyera daría A o B. Que el evento diga `None` teniendo un valor a mano
es la única forma de probar que el NULL es una decisión y no el reflejo de un dato vacío.

**3. El doble tendría que devolver una fila prefabricada en el `insert`.** La arma con el payload
recibido, así que un `save` que dejara de mandar `nombre` no validaría contra el schema.

**4. `_AuditoriaFalsa` tendría que descartar los kwargs.** Guarda cada llamada ENTERA, así que un
payload al que le falte `empresa_id` —que no es lo mismo que mandarlo en None— se ve.

**5. Faltaría el caso POSITIVO de `existe_nombre`.** Se afirman las dos direcciones: el nombre
repetido rebota con 409 aunque esté "en otra empresa", y un nombre libre entra. Sin la segunda,
un `existe_nombre` que devolviera siempre True pasaría el test del duplicado.
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

from datetime import UTC, datetime  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories.cliente_repo as repo_mod  # noqa: E402
from repositories.cliente_repo import ClienteRepo  # noqa: E402
from schemas.cliente import ClienteCreate, ClienteUpdate  # noqa: E402
from services.cliente_service import ClienteService  # noqa: E402
from tests._almacen_tabla import Almacen  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
DE_A = UUID("11111111-1111-1111-1111-111111111111")
DE_B = UUID("22222222-2222-2222-2222-222222222222")
USUARIO = str(uuid4())


class _AuditoriaFalsa:
    """Guarda cada llamada ENTERA. Un payload al que le falte una clave se ve."""

    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _fila(id_, empresa, nombre, activo=True) -> dict:
    """Fila como la que hay HOY en la base: con `empresa_id` cargado.

    🔴 La 108 NO borra la columna, solo le saca el NOT NULL. Que el doble conserve el valor es
    deliberado: es lo que permite que el test de auditoría distinga "eligió NULL" de "no había
    nada que poner"."""
    return {"id": str(id_), "empresa_id": str(empresa), "nombre": nombre, "activo": activo,
            "created_at": datetime.now(UTC).isoformat(), "updated_at": None}


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({"clientes": [
        _fila(DE_A, EMPRESA_A, "Acme"),
        _fila(DE_B, EMPRESA_B, "Globex"),
    ]})
    monkeypatch.setattr(repo_mod, "supabase_admin", a)
    return a


@pytest.fixture
def auditoria() -> _AuditoriaFalsa:
    return _AuditoriaFalsa()


@pytest.fixture
def svc(almacen, auditoria) -> ClienteService:
    return ClienteService(repo=ClienteRepo(), audit=auditoria)


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── El catálogo no se acota por empresa ───────────────────────────────────────


class TestCatalogoGlobal:
    def test_el_listado_trae_los_de_todas_las_empresas(self, svc) -> None:
        nombres = {c.nombre for c in svc.get_clientes().items}
        assert nombres == {"Acme", "Globex"}

    def test_se_alcanza_por_id_un_cliente_de_cualquier_empresa(self, svc) -> None:
        # Los DOS, no uno: si el repo filtrara por algo, uno de los dos daría 404.
        assert svc.get_cliente(DE_A).nombre == "Acme"
        assert svc.get_cliente(DE_B).nombre == "Globex"

    def test_un_id_inexistente_sigue_dando_404(self, svc) -> None:
        err = _error(lambda: svc.get_cliente(uuid4()))
        assert (err.code, err.status_code) == ("CLIENTE_NOT_FOUND", 404)

    def test_se_edita_y_se_da_de_baja_cualquiera(self, svc) -> None:
        assert svc.update_cliente(DE_B, ClienteUpdate(nombre="Globex SA"), USUARIO).nombre == "Globex SA"
        svc.delete_cliente(DE_A, USUARIO)
        assert {c.nombre for c in svc.get_clientes().items} == {"Globex SA"}

    def test_la_respuesta_ya_no_expone_empresa_id(self, svc, almacen) -> None:
        """La fila CRUDA del almacén sí la trae; el schema la descarta.

        Las dos mitades importan: sin la primera, "el schema no la expone" se cumpliría también
        si la fila viniera sin el campo, que es otra cosa —y es justo lo que va a pasar recién
        con la 109—. Acá el dato ESTÁ y aun así no sale."""
        cruda = almacen.catalogo["clientes"][0]
        assert cruda["empresa_id"] == str(EMPRESA_A)
        assert not hasattr(svc.get_cliente(DE_A), "empresa_id")


# ── Unicidad de nombre: ahora es GLOBAL ───────────────────────────────────────


class TestNombreUnicoGlobal:
    def test_el_nombre_de_otra_empresa_ahora_rebota(self, svc) -> None:
        """🔴 SE INVIRTIÓ. Hasta la 107 esto era legal y había un test que lo afirmaba
        (`test_el_mismo_nombre_en_otra_empresa_si_se_puede`). Con el catálogo global, "Globex"
        es uno solo para todo el sistema."""
        err = _error(lambda: svc.create_cliente(ClienteCreate(nombre="Globex"), USUARIO))
        assert (err.code, err.status_code) == ("CLIENTE_DUPLICADO", 409)

    @pytest.mark.parametrize("nombre", ["acme", "ACME", "  Acme  "])
    def test_la_comparacion_es_case_insensitive_y_trimmea(self, svc, nombre: str) -> None:
        err = _error(lambda: svc.create_cliente(ClienteCreate(nombre=nombre), USUARIO))
        assert err.code == "CLIENTE_DUPLICADO"

    def test_un_nombre_libre_si_entra(self, svc) -> None:
        """El caso positivo: sin él, un `existe_nombre` que devolviera siempre True pasaría."""
        creado = svc.create_cliente(ClienteCreate(nombre="Initech"), USUARIO)
        assert creado.nombre == "Initech"
        assert {c.nombre for c in svc.get_clientes().items} == {"Acme", "Globex", "Initech"}

    def test_renombrarse_a_si_mismo_no_es_duplicado(self, svc) -> None:
        assert svc.update_cliente(DE_A, ClienteUpdate(nombre="Acme"), USUARIO).nombre == "Acme"


# ── Auditoría: el evento NO lleva empresa ─────────────────────────────────────


class TestAuditoriaSinEmpresa:
    """🔴 EL BLOQUE QUE REEMPLAZA AL QUE SE PIERDE.

    Los tres tests que se van en L7 (`test_el_alta_audita_con_la_empresa_del_cliente` y sus dos
    hermanos) afirmaban que la empresa del evento salía de la ENTIDAD y no del header. La
    invariante que cubrían —el evento no se etiqueta con lo que el usuario tenía seleccionado en
    el sidebar— sigue viva acá, con el desenlace nuevo: un cliente no tiene empresa, así que el
    evento va NULL.

    Lo que hace falsable el test: las filas del almacén TIENEN `empresa_id` cargado (A y B). Hay
    un valor concreto disponible; que el evento diga None es una elección, no un vacío heredado.
    """

    def test_el_alta_audita_con_empresa_id_null(self, svc, auditoria) -> None:
        svc.create_cliente(ClienteCreate(nombre="Initech"), USUARIO)
        ev = auditoria.eventos[-1]
        assert ev["evento"] == "alta_cliente"
        assert "empresa_id" in ev, "la clave tiene que viajar, aunque valga None"
        assert ev["empresa_id"] is None

    def test_la_edicion_audita_con_empresa_id_null(self, svc, auditoria) -> None:
        # Sobre un cliente de EMPRESA_A: si el payload leyera la entidad, diría A.
        svc.update_cliente(DE_A, ClienteUpdate(nombre="Acme SA"), USUARIO)
        ev = auditoria.eventos[-1]
        assert ev["evento"] == "update_cliente"
        assert ev["empresa_id"] is None

    def test_la_baja_audita_con_empresa_id_null(self, svc, auditoria) -> None:
        svc.delete_cliente(DE_B, USUARIO)
        ev = auditoria.eventos[-1]
        assert ev["evento"] == "baja_cliente"
        assert ev["empresa_id"] is None

    def test_ninguna_empresa_real_se_filtra_en_el_payload(self, svc, auditoria) -> None:
        """Barre el evento ENTERO: ni A ni B pueden aparecer en ninguna clave, ni siquiera dentro
        de `datos_nuevos`/`datos_anteriores` (donde entrarían si `_CAMPOS_CLIENTE` la conservara)."""
        svc.create_cliente(ClienteCreate(nombre="Initech"), USUARIO)
        svc.update_cliente(DE_A, ClienteUpdate(nombre="Acme SA"), USUARIO)
        svc.delete_cliente(DE_B, USUARIO)
        assert len(auditoria.eventos) == 3
        for ev in auditoria.eventos:
            texto = str(ev)
            assert str(EMPRESA_A) not in texto and str(EMPRESA_B) not in texto

    def test_las_tres_escrituras_siguen_auditando(self, svc, auditoria) -> None:
        """`test_auditoria_coherente` exige que un módulo que audita algo las audite todas."""
        svc.create_cliente(ClienteCreate(nombre="Initech"), USUARIO)
        svc.update_cliente(DE_A, ClienteUpdate(nombre="Acme SA"), USUARIO)
        svc.delete_cliente(DE_B, USUARIO)
        assert [e["accion"] for e in auditoria.eventos] == ["INSERT", "UPDATE", "DELETE"]
