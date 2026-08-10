"""
Catálogo de clientes (migración 102) — la BARRERA DE EMPRESA del repo.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS FALLEN?

**Que el doble dejara de acumular los filtros y aplicara solo el último.** El repo encadena
`.eq("id", ...)` y después `.eq("empresa_id", ...)`; un fake que se quedara con el último filtro
—o peor, que ACEPTARA `empresa_id` y lo IGNORARA— devolvería el cliente ajeno igual y estos
tests pasarían con la barrera borrada. Es el caso #1 de la doctrina del repo ("el fake acepta
empresa_id y lo ignora → la barrera entera sin probar"), y por eso el doble exige que
**TODOS** los `(columna, valor)` acumulados coincidan, y el catálogo modela DOS empresas con un
cliente en cada una.

La segunda pieza que hace que puedan fallar: `Almacen.escrituras`. Sin ella,
`test_update_ajeno_no_escribe` solo miraría el valor de retorno — y un repo que hiciera el
UPDATE sin `.eq("empresa_id")` y recién filtrara en la relectura devolvería `None` igual,
habiendo pisado la fila ajena. El registro de escrituras es lo único que distingue "no devolvió
nada" de "no escribió nada".

⚠️ El fake de escritura construye la fila A PARTIR del payload recibido, nunca de un objeto
prefabricado: si `save` dejara de mandar `nombre`, el `ClienteResponse` no validaría.
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
from schemas.cliente import ClienteCreate  # noqa: E402
from tests._almacen_tabla import Almacen  # noqa: E402

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")
AJENO = UUID("22222222-2222-2222-2222-222222222222")
INACTIVO = UUID("33333333-3333-3333-3333-333333333333")


def _fila(id_, empresa, nombre, activo=True) -> dict:
    return {"id": str(id_), "empresa_id": str(empresa), "nombre": nombre, "activo": activo,
            "created_at": datetime.now(UTC).isoformat(), "updated_at": None}


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({"clientes": [
        _fila(PROPIO, EMPRESA_A, "Acme"),
        _fila(AJENO, EMPRESA_B, "Globex"),
        _fila(INACTIVO, EMPRESA_A, "Zzz Cerrado", activo=False),
    ]})
    monkeypatch.setattr(repo_mod, "supabase_admin", a)
    return a


# ── La barrera ────────────────────────────────────────────────────────────────


class TestBarreraDeEmpresa:
    def test_cliente_de_otra_empresa_no_se_ve(self, almacen) -> None:
        assert ClienteRepo().find_by_id(str(AJENO), EMPRESA_A) is None

    def test_el_propio_si_se_ve(self, almacen) -> None:
        """El contraste que hace que el test de arriba signifique algo: si el fake devolviera
        None para todo, "no se ve el ajeno" pasaría con la barrera borrada."""
        propio = ClienteRepo().find_by_id(str(PROPIO), EMPRESA_A)
        assert propio is not None and propio.nombre == "Acme"

    def test_consolidado_no_restringe(self, almacen) -> None:
        """empresa_id=None es la vista consolidada, no un fallo de validación."""
        assert ClienteRepo().find_by_id(str(AJENO), None).nombre == "Globex"

    def test_el_listado_no_trae_los_ajenos(self, almacen) -> None:
        nombres = [c.nombre for c in ClienteRepo().find_all(EMPRESA_A, incluir_inactivos=True)]
        assert nombres == ["Acme", "Zzz Cerrado"]

    def test_update_ajeno_no_escribe(self, almacen) -> None:
        """🔴 La barrera va EN EL UPDATE, no solo en la relectura.

        Sin el `.eq("empresa_id")` del update, el repo devolvería None igual (la relectura sí
        filtra) habiendo pisado la fila ajena. Por eso se afirma sobre `escrituras`, que es lo
        que VIAJA EN LA QUERY, y además sobre el nombre que quedó en el catálogo.
        """
        assert ClienteRepo().update(str(AJENO), {"nombre": "Hackeado"}, EMPRESA_A) is None
        _, filtros, _ = almacen.escrituras[0]
        assert ("empresa_id", str(EMPRESA_A)) in filtros
        assert almacen.catalogo["clientes"][1]["nombre"] == "Globex"

    def test_update_propio_si_escribe(self, almacen) -> None:
        assert ClienteRepo().update(str(PROPIO), {"nombre": "Acme SA"}, EMPRESA_A).nombre == "Acme SA"


# ── Alta y baja lógica ────────────────────────────────────────────────────────


class TestAltaYBaja:
    def test_el_alta_usa_la_empresa_del_body(self, almacen) -> None:
        """Crear es una ACCIÓN: la empresa sale del form, nunca del header. Si el repo tomara
        otra cosa, el cliente nuevo no aparecería en el listado de EMPRESA_B."""
        creado = ClienteRepo().save(ClienteCreate(empresa_id=EMPRESA_B, nombre="  Initech  "))
        assert str(creado.empresa_id) == str(EMPRESA_B)
        assert creado.nombre == "Initech"          # se le hace strip
        assert creado.activo is True               # default de la tabla
        assert [c.nombre for c in ClienteRepo().find_all(EMPRESA_B)] == ["Globex", "Initech"]

    def test_el_listado_esconde_los_inactivos_por_defecto(self, almacen) -> None:
        """El consumidor normal es el select de la carga de horas: no puede ofrecer un cliente
        dado de baja."""
        assert [c.nombre for c in ClienteRepo().find_all(EMPRESA_A)] == ["Acme"]

    def test_la_baja_es_logica(self, almacen) -> None:
        """No hay delete: `horas_proyecto.cliente_id` es una FK sin ON DELETE. Bajar un cliente
        lo saca del select y NO toca ninguna hora ya cargada."""
        assert not hasattr(ClienteRepo(), "delete")
        ClienteRepo().update(str(PROPIO), {"activo": False}, EMPRESA_A)
        assert ClienteRepo().find_all(EMPRESA_A) == []
        assert len(ClienteRepo().find_all(EMPRESA_A, incluir_inactivos=True)) == 2
