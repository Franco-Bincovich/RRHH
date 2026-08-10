"""
ABM de clientes — el SERVICE: barrera de empresa, duplicados y auditoría.

Corre contra el `ClienteRepo` REAL sobre el doble de tabla (`tests/_almacen_tabla.Almacen`), no
contra un repo falso. Es deliberado: lo que se quiere probar es la cadena entera —el service
propaga la empresa, el repo la mete en el WHERE, el doble la honra—, y un repo falso convertiría
la barrera en una constante del test. Lo único falseado es `AuditService`, porque un evento hay
que capturarlo para poder mirarlo.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. El catálogo tendría que modelar UNA empresa.** Con una sola, "el ajeno no se ve" y "no se
ve nada" son indistinguibles y la barrera pasa borrada. Hay dos empresas con un cliente en cada
una, y cada bloque afirma las DOS direcciones: el ajeno da 404 **y** el propio se encuentra.

**2. 🔴 El evento de auditoría tendría que llamarse con la MISMA empresa que trae la entidad.**
Si el test pasara `empresa_id=EMPRESA_A` y la entidad fuera de EMPRESA_A, un payload que leyera
el header daría idéntico al que lee la entidad: el test no podría desmentir de dónde salió. Por
eso `update` y `delete` se invocan en modo CONSOLIDADO (`empresa_id=None`) sobre un cliente de
EMPRESA_A: el header vale None y la entidad vale A, así que sólo un payload que lea la ENTIDAD
puede dar A. Es el bug que `_costos_write.py:80` tiene abierto hoy.

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
PROPIO = UUID("11111111-1111-1111-1111-111111111111")
AJENO = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
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
        _fila(PROPIO, EMPRESA_A, "Acme"),
        _fila(AJENO, EMPRESA_B, "Globex"),
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


# ── Barrera de empresa en las tres escrituras ─────────────────────────────────


class TestBarreraDeEmpresa:
    def test_leer_uno_ajeno_da_404(self, svc) -> None:
        err = _error(lambda: svc.get_cliente(AJENO, EMPRESA_A))
        assert (err.code, err.status_code) == ("CLIENTE_NOT_FOUND", 404)

    def test_el_ajeno_es_indistinguible_del_inexistente(self, svc) -> None:
        """Un code o un mensaje distinto confirmaría que el recurso existe y es de otro."""
        ajeno = _error(lambda: svc.get_cliente(AJENO, EMPRESA_A))
        inexistente = _error(lambda: svc.get_cliente(INEXISTENTE, EMPRESA_A))
        assert (ajeno.code, ajeno.message, ajeno.status_code) == \
               (inexistente.code, inexistente.message, inexistente.status_code)

    def test_editar_uno_ajeno_da_404_y_no_escribe(self, svc, almacen, auditoria) -> None:
        err = _error(lambda: svc.update_cliente(
            AJENO, ClienteUpdate(nombre="Hackeado"), EMPRESA_A, USUARIO))
        assert err.code == "CLIENTE_NOT_FOUND"
        assert almacen.catalogo["clientes"][1]["nombre"] == "Globex"
        assert almacen.escrituras == []          # cortó ANTES de tocar la base
        assert auditoria.eventos == []           # y no dejó un evento de algo que no pasó

    def test_dar_de_baja_uno_ajeno_da_404_y_no_escribe(self, svc, almacen, auditoria) -> None:
        err = _error(lambda: svc.delete_cliente(AJENO, EMPRESA_A, USUARIO))
        assert err.code == "CLIENTE_NOT_FOUND"
        assert almacen.catalogo["clientes"][1]["activo"] is True
        assert almacen.escrituras == []
        assert auditoria.eventos == []

    def test_el_propio_si_se_edita(self, svc) -> None:
        """El contraste: sin esto, los tests de arriba pasarían con un service que rechaza todo."""
        assert svc.update_cliente(PROPIO, ClienteUpdate(nombre="Acme SA"),
                                  EMPRESA_A, USUARIO).nombre == "Acme SA"

    def test_el_listado_no_trae_los_ajenos(self, svc) -> None:
        assert [c.nombre for c in svc.get_clientes(EMPRESA_A).items] == ["Acme"]


# ── Nombre duplicado ──────────────────────────────────────────────────────────


class TestNombreDuplicado:
    """El índice `ux_clientes_nombre_por_empresa` es sobre `(empresa_id, lower(nombre))`, así que
    la comparación tiene que ser CASE-INSENSITIVE. Todos los casos usan una capitalización
    distinta de la guardada: con el mismo texto exacto, un chequeo sensible a mayúsculas pasaría
    igual y el test no probaría la parte que importa."""

    @pytest.mark.parametrize("nombre", ["ACME", "acme", "AcMe", "  Acme  "])
    def test_el_alta_rechaza_el_duplicado(self, svc, nombre: str) -> None:
        err = _error(lambda: svc.create_cliente(
            ClienteCreate(empresa_id=EMPRESA_A, nombre=nombre), USUARIO))
        assert (err.code, err.status_code) == ("CLIENTE_DUPLICADO", 409)

    def test_la_edicion_rechaza_el_duplicado(self, almacen, svc) -> None:
        almacen.catalogo["clientes"].append(_fila(INEXISTENTE, EMPRESA_A, "Otro"))
        err = _error(lambda: svc.update_cliente(
            INEXISTENTE, ClienteUpdate(nombre="aCmE"), EMPRESA_A, USUARIO))
        assert err.code == "CLIENTE_DUPLICADO"

    def test_renombrarse_a_si_mismo_no_es_duplicado(self, svc) -> None:
        """Sin `excepto_id`, guardar el mismo cliente sin cambiarle el nombre daría 409: se
        chocaría consigo mismo y la pantalla sería imposible de usar."""
        assert svc.update_cliente(PROPIO, ClienteUpdate(nombre="ACME"),
                                  EMPRESA_A, USUARIO).nombre == "ACME"

    def test_el_mismo_nombre_en_otra_empresa_si_se_puede(self, svc) -> None:
        """El índice único es POR empresa: dos sociedades del grupo pueden facturarle al mismo
        cliente. Si la unicidad fuera global, esto daría 409 y sería un bug."""
        assert svc.create_cliente(
            ClienteCreate(empresa_id=EMPRESA_B, nombre="Acme"), USUARIO).nombre == "Acme"

    def test_el_nombre_vacio_se_rechaza_antes_que_el_duplicado(self, svc) -> None:
        err = _error(lambda: svc.create_cliente(
            ClienteCreate(empresa_id=EMPRESA_A, nombre="   "), USUARIO))
        assert (err.code, err.status_code) == ("NOMBRE_REQUERIDO", 422)


# ── Auditoría: las tres, con la empresa de la ENTIDAD ─────────────────────────


class TestAuditoria:
    """🔴 `update` y `delete` se llaman en modo CONSOLIDADO (empresa_id=None) sobre un cliente de
    EMPRESA_A. Ver el punto 2 del encabezado: es lo único que hace que "salió de la entidad" y
    "salió del header" den resultados distintos."""

    def test_el_alta_audita_con_la_empresa_del_cliente(self, svc, auditoria) -> None:
        creado = svc.create_cliente(
            ClienteCreate(empresa_id=EMPRESA_B, nombre="Initech"), USUARIO)
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"], ev["entidad"]) == ("INSERT", "alta_cliente", "cliente")
        assert str(ev["empresa_id"]) == str(EMPRESA_B)
        assert str(ev["registro_id"]) == str(creado.id)
        assert ev["usuario_id"] == USUARIO
        assert ev["datos_nuevos"]["nombre"] == "Initech"
        assert ev["datos_anteriores"] is None

    def test_la_edicion_audita_con_la_empresa_de_la_entidad_no_del_header(
            self, svc, auditoria) -> None:
        svc.update_cliente(PROPIO, ClienteUpdate(nombre="Acme SA"), None, USUARIO)
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"]) == ("UPDATE", "update_cliente")
        assert ev["empresa_id"] is not None, "se etiquetó con el header (None), no con la entidad"
        assert str(ev["empresa_id"]) == str(EMPRESA_A)

    def test_el_diff_registra_el_antes_y_el_despues(self, svc, auditoria) -> None:
        svc.update_cliente(PROPIO, ClienteUpdate(nombre="Acme SA"), EMPRESA_A, USUARIO)
        ev = auditoria.eventos[0]
        assert ev["datos_anteriores"]["nombre"] == "Acme"
        assert ev["datos_nuevos"]["nombre"] == "Acme SA"
        # No inventa cambios en lo que no se tocó: el diff sale de comparar, no de volcar la fila.
        assert "activo" not in ev["datos_nuevos"]

    def test_la_baja_audita_con_la_empresa_de_la_entidad_no_del_header(
            self, svc, auditoria) -> None:
        svc.delete_cliente(PROPIO, None, USUARIO)
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"]) == ("DELETE", "baja_cliente")
        assert ev["empresa_id"] is not None, "se etiquetó con el header (None), no con la entidad"
        assert str(ev["empresa_id"]) == str(EMPRESA_A)
        assert ev["datos_anteriores"]["activo"] is True   # el estado ANTES de la baja
        assert ev["datos_nuevos"] is None

    def test_las_tres_escrituras_auditan(self, svc, auditoria) -> None:
        """`test_auditoria_coherente` exige que un módulo que audita algo lo audite TODO. Esto lo
        verifica desde adentro: los tres caminos, una corrida, tres eventos."""
        svc.create_cliente(ClienteCreate(empresa_id=EMPRESA_A, nombre="Initech"), USUARIO)
        svc.update_cliente(PROPIO, ClienteUpdate(nombre="Acme SA"), EMPRESA_A, USUARIO)
        svc.delete_cliente(PROPIO, EMPRESA_A, USUARIO)
        assert [e["evento"] for e in auditoria.eventos] == \
               ["alta_cliente", "update_cliente", "baja_cliente"]


# ── La baja es lógica ─────────────────────────────────────────────────────────


class TestBajaLogica:
    def test_la_fila_sobrevive_y_solo_cambia_activo(self, svc, almacen) -> None:
        """🔴 `horas_proyecto.cliente_id` es una FK SIN ON DELETE: un borrado físico de un
        cliente con horas no daría 409, reventaría contra la constraint como 500 — que es el bug
        que `proyectos_service.delete` tiene hoy. Acá la fila no se borra nunca."""
        svc.delete_cliente(PROPIO, EMPRESA_A, USUARIO)
        fila = almacen.catalogo["clientes"][0]
        assert fila["id"] == str(PROPIO) and fila["activo"] is False
        assert fila["nombre"] == "Acme"                      # no se pisó nada más
        assert len(almacen.catalogo["clientes"]) == 2        # ninguna fila desapareció

    def test_el_dado_de_baja_desaparece_del_listado_pero_es_recuperable(self, svc) -> None:
        svc.delete_cliente(PROPIO, EMPRESA_A, USUARIO)
        assert svc.get_clientes(EMPRESA_A).items == []
        assert [c.nombre for c in svc.get_clientes(EMPRESA_A, incluir_inactivos=True).items] \
            == ["Acme"]
        svc.update_cliente(PROPIO, ClienteUpdate(activo=True), EMPRESA_A, USUARIO)
        assert [c.nombre for c in svc.get_clientes(EMPRESA_A).items] == ["Acme"]
