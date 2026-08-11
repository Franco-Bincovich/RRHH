"""
ABM de clientes — el SERVICE: rechazo único, duplicados y CONTENIDO de la auditoría.

Corre contra el `ClienteRepo` REAL sobre el doble de tabla (`tests/_almacen_tabla.Almacen`), no
contra un repo falso. Es deliberado: lo que se quiere probar es la cadena entera —el service
llama, el repo arma la query, el doble la ejecuta—, y un repo falso convertiría el resultado en
una constante del test. Lo único falseado es `AuditService`, porque un evento hay que capturarlo
para poder mirarlo.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. El catálogo tendría que tener UN SOLO cliente.** Con uno solo, "rechaza lo que no existe" y
"rechaza todo" son indistinguibles. Hay dos, y cada bloque afirma las DOS direcciones: el
inexistente da 404 **y** el que existe se edita.

**2. 🔴 Las filas del catálogo tendrían que nacer SIN `empresa_id`.** Nacen con una empresa real
(A y B), aunque el repo ya no la mire: la 108 le sacó el NOT NULL y la 109 recién dropea la
columna. Eso es lo que permite afirmar que el repo dejó de acotar —`test_el_mismo_nombre_de_otra_
empresa_YA_NO_se_puede` compara contra la fila de EMPRESA_B— y que el evento elige NULL teniendo
un valor a mano (eso último se afirma en `test_clientes_global.py`).

⚠️ Este archivo probaba la BARRERA DE EMPRESA y la empresa del evento de auditoría. Las dos
desaparecieron con la 108. Lo que las sobrevivió está repartido así: el RECHAZO ÚNICO en
`TestRechazoUnico` (acá), el CONTENIDO del evento en `TestAuditoria` (acá), y lo global en
`test_clientes_global.py`.

**3. `_AuditoriaFalsa` tendría que descartar los kwargs.** Guarda cada llamada entera, así que
un payload al que le falte `empresa_id`, o que mande la accion equivocada, se ve.

**4. El doble tendría que devolver una fila prefabricada en el `insert`.** La arma con el
payload recibido, así que un `save` que deje de mandar `nombre` no valida contra el schema.
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
UNO = UUID("11111111-1111-1111-1111-111111111111")
OTRO = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
OTRO_INEXISTENTE = UUID("44444444-4444-4444-4444-444444444444")
USUARIO = str(uuid4())


class _AuditoriaFalsa:
    """Guarda cada llamada ENTERA. Un payload al que le falte un campo se ve."""

    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _fila(id_, empresa, nombre, activo=True) -> dict:
    return {"id": str(id_), "empresa_id": str(empresa), "nombre": nombre, "activo": activo,
            "created_at": datetime.now(UTC).isoformat(), "updated_at": None}


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({"clientes": [
        _fila(UNO, EMPRESA_A, "Acme"),
        _fila(OTRO, EMPRESA_B, "Globex"),
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


# ── El rechazo es UNO SOLO ────────────────────────────────────────────────────


class TestRechazoUnico:
    """🔴 HEREDA LA INVARIANTE DE `TestBarreraDeEmpresa`, QUE PERDIÓ SU CASO.

    Aquel bloque probaba que "no existe" y "es de otra empresa" fueran INDISTINGUIBLES desde
    afuera. La segunda mitad desapareció con la 108 —no hay clientes ajenos—, pero la invariante
    que la sostenía sigue viva y es más general: **el rechazo de este service es uno solo**. Si
    algún día alguien agrega un motivo con su propio `code` o su propio mensaje, vuelve a existir
    un oráculo, y estos tests lo atrapan sin que importe cuál sea el motivo nuevo.

    ¿Qué tendría que ser distinto para que fallen? Que se comparara contra un literal escrito acá.
    Se comparan DOS rechazos REALES entre sí, así que el día que el mensaje canónico cambie el
    test sigue valiendo — lo que no puede es que DOS caminos den mensajes distintos.
    """

    def test_leer_un_inexistente_da_404(self, svc) -> None:
        err = _error(lambda: svc.get_cliente(INEXISTENTE))
        assert (err.code, err.status_code) == ("CLIENTE_NOT_FOUND", 404)

    def test_dos_inexistentes_distintos_dan_exactamente_el_mismo_error(self, svc) -> None:
        a = _error(lambda: svc.get_cliente(INEXISTENTE))
        b = _error(lambda: svc.get_cliente(OTRO_INEXISTENTE))
        assert (a.code, a.message, a.status_code) == (b.code, b.message, b.status_code)

    def test_los_tres_caminos_rechazan_igual(self, svc) -> None:
        """Leer, editar y dar de baja un id que no existe: mismo code, mismo mensaje, mismo
        status. Un 403 en cualquiera de los tres —o un mensaje más específico— confirmaría algo."""
        leer = _error(lambda: svc.get_cliente(INEXISTENTE))
        editar = _error(lambda: svc.update_cliente(INEXISTENTE, ClienteUpdate(nombre="X"), USUARIO))
        bajar = _error(lambda: svc.delete_cliente(INEXISTENTE, USUARIO))
        for otro in (editar, bajar):
            assert (otro.code, otro.message, otro.status_code) == \
                   (leer.code, leer.message, leer.status_code)

    def test_editar_un_inexistente_no_escribe_ni_audita(self, svc, almacen, auditoria) -> None:
        err = _error(lambda: svc.update_cliente(
            INEXISTENTE, ClienteUpdate(nombre="Hackeado"), USUARIO))
        assert err.code == "CLIENTE_NOT_FOUND"
        assert [f["nombre"] for f in almacen.catalogo["clientes"]] == ["Acme", "Globex"]
        assert almacen.escrituras == []          # cortó ANTES de tocar la base
        assert auditoria.eventos == []           # y no dejó un evento de algo que no pasó

    def test_dar_de_baja_un_inexistente_no_escribe_ni_audita(self, svc, almacen, auditoria) -> None:
        err = _error(lambda: svc.delete_cliente(INEXISTENTE, USUARIO))
        assert err.code == "CLIENTE_NOT_FOUND"
        assert all(f["activo"] is True for f in almacen.catalogo["clientes"])
        assert almacen.escrituras == []
        assert auditoria.eventos == []

    def test_el_que_existe_si_se_edita(self, svc) -> None:
        """El contraste: sin esto, todo lo de arriba pasaría con un service que rechaza todo."""
        assert svc.update_cliente(UNO, ClienteUpdate(nombre="Acme SA"), USUARIO).nombre == "Acme SA"


# ── Nombre duplicado ──────────────────────────────────────────────────────────


class TestNombreDuplicado:
    """El índice `ux_clientes_nombre_global` es sobre `lower(nombre)` (migración 108), así que la
    comparación tiene que ser CASE-INSENSITIVE. Todos los casos usan una capitalización distinta
    de la guardada: con el mismo texto exacto, un chequeo sensible a mayúsculas pasaría igual y el
    test no probaría la parte que importa."""

    @pytest.mark.parametrize("nombre", ["ACME", "acme", "AcMe", "  Acme  "])
    def test_el_alta_rechaza_el_duplicado(self, svc, nombre: str) -> None:
        err = _error(lambda: svc.create_cliente(ClienteCreate(nombre=nombre), USUARIO))
        assert (err.code, err.status_code) == ("CLIENTE_DUPLICADO", 409)

    def test_la_edicion_rechaza_el_duplicado(self, almacen, svc) -> None:
        almacen.catalogo["clientes"].append(_fila(INEXISTENTE, EMPRESA_A, "Otro"))
        err = _error(lambda: svc.update_cliente(
            INEXISTENTE, ClienteUpdate(nombre="aCmE"), USUARIO))
        assert err.code == "CLIENTE_DUPLICADO"

    def test_renombrarse_a_si_mismo_no_es_duplicado(self, svc) -> None:
        """Sin `excepto_id`, guardar el mismo cliente sin cambiarle el nombre daría 409: se
        chocaría consigo mismo y la pantalla sería imposible de usar."""
        assert svc.update_cliente(UNO, ClienteUpdate(nombre="ACME"), USUARIO).nombre == "ACME"

    def test_el_mismo_nombre_de_otra_empresa_ya_no_se_puede(self, svc, almacen) -> None:
        """🔴 TEST INVERTIDO, no borrado. Hasta la 107 esto era LEGAL y este mismo test lo
        afirmaba: el índice era `(empresa_id, lower(nombre))` y dos sociedades podían facturarle
        al mismo cliente. Con el índice global, "Globex" es uno solo para todo el sistema.

        Lo que lo hace falsable: la fila "Globex" del catálogo sigue teniendo `empresa_id`
        = EMPRESA_B, distinta de la de "Acme". Si el repo volviera a acotar por empresa, no la
        vería y el alta pasaría."""
        assert almacen.catalogo["clientes"][1]["empresa_id"] == str(EMPRESA_B)
        err = _error(lambda: svc.create_cliente(ClienteCreate(nombre="globex"), USUARIO))
        assert (err.code, err.status_code) == ("CLIENTE_DUPLICADO", 409)

    def test_el_nombre_vacio_se_rechaza_antes_que_el_duplicado(self, svc) -> None:
        err = _error(lambda: svc.create_cliente(ClienteCreate(nombre="   "), USUARIO))
        assert (err.code, err.status_code) == ("NOMBRE_REQUERIDO", 422)


# ── Auditoría: las tres, con la empresa de la ENTIDAD ─────────────────────────


class TestAuditoria:
    """EL CONTENIDO del evento. Que `empresa_id` vaya NULL se afirma en `test_clientes_global.py`
    (`TestAuditoriaSinEmpresa`); acá se afirma todo lo DEMÁS, que aquel no mira.

    🔴 El reparto no es arbitrario: los cinco tests viejos de este bloque mezclaban las dos cosas,
    y al perder la empresa se llevaban puestas afirmaciones que nada tenía que ver con ella —el
    `registro_id`, el `usuario_id`, la `entidad`, y sobre todo el DIFF. Si este bloque se hubiera
    borrado entero, el diff de clientes se quedaba sin un solo test."""

    def test_el_alta_registra_quien_que_y_sobre_que_fila(self, svc, auditoria) -> None:
        creado = svc.create_cliente(ClienteCreate(nombre="Initech"), USUARIO)
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"], ev["entidad"]) == ("INSERT", "alta_cliente", "cliente")
        assert str(ev["registro_id"]) == str(creado.id)
        assert ev["usuario_id"] == USUARIO
        assert ev["datos_nuevos"]["nombre"] == "Initech"
        assert ev["datos_anteriores"] is None

    def test_la_edicion_registra_accion_y_evento(self, svc, auditoria) -> None:
        svc.update_cliente(UNO, ClienteUpdate(nombre="Acme SA"), USUARIO)
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"]) == ("UPDATE", "update_cliente")
        assert str(ev["registro_id"]) == str(UNO)

    def test_el_diff_registra_el_antes_y_el_despues(self, svc, auditoria) -> None:
        """🔴 EL QUE MÁS IMPORTA DE ESTE BLOQUE, y el único que lo cubre en todo el repo. Un diff
        que volcara la fila entera en vez de comparar registraría un cambio en `activo` que nadie
        hizo — que es exactamente el diff fantasma que costó 93 eventos falsos en producción."""
        svc.update_cliente(UNO, ClienteUpdate(nombre="Acme SA"), USUARIO)
        ev = auditoria.eventos[0]
        assert ev["datos_anteriores"]["nombre"] == "Acme"
        assert ev["datos_nuevos"]["nombre"] == "Acme SA"
        # No inventa cambios en lo que no se tocó: el diff sale de comparar, no de volcar la fila.
        assert "activo" not in ev["datos_nuevos"]

    def test_la_baja_fotografia_el_estado_anterior(self, svc, auditoria) -> None:
        svc.delete_cliente(UNO, USUARIO)
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"]) == ("DELETE", "baja_cliente")
        assert ev["datos_anteriores"]["activo"] is True   # el estado ANTES de la baja
        assert ev["datos_nuevos"] is None


# ── La baja es lógica ─────────────────────────────────────────────────────────


class TestBajaLogica:
    def test_la_fila_sobrevive_y_solo_cambia_activo(self, svc, almacen) -> None:
        """🔴 `horas_proyecto.cliente_id` es una FK SIN ON DELETE: un borrado físico de un
        cliente con horas no daría 409, reventaría contra la constraint como 500 — que es el bug
        que `proyectos_service.delete` tiene hoy. Acá la fila no se borra nunca."""
        svc.delete_cliente(UNO, USUARIO)
        fila = almacen.catalogo["clientes"][0]
        assert fila["id"] == str(UNO) and fila["activo"] is False
        assert fila["nombre"] == "Acme"                      # no se pisó nada más
        assert len(almacen.catalogo["clientes"]) == 2        # ninguna fila desapareció

    def test_el_dado_de_baja_desaparece_del_listado_pero_es_recuperable(self, svc) -> None:
        svc.delete_cliente(UNO, USUARIO)
        assert [c.nombre for c in svc.get_clientes().items] == ["Globex"]
        assert [c.nombre for c in svc.get_clientes(incluir_inactivos=True).items] \
            == ["Acme", "Globex"]
        svc.update_cliente(UNO, ClienteUpdate(activo=True), USUARIO)
        assert [c.nombre for c in svc.get_clientes().items] == ["Acme", "Globex"]
