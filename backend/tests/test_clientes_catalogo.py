"""
Catálogo de clientes (migración 102) — la BARRERA DE EMPRESA del repo.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS FALLEN?

**Que el doble dejara de acumular los filtros y aplicara solo el último**, o que no registrara
las escrituras. El repo encadena `.eq()` y el doble exige que **TODOS** los `(columna, valor)`
acumulados coincidan; `Almacen.escrituras` guarda cada UPDATE con sus filtros y su payload.

Sin esas dos piezas, `test_el_update_de_un_id_inexistente_no_escribe_nada` solo miraría el valor
de retorno — y un repo que hiciera el UPDATE sin `.eq("id")` y recién filtrara en la relectura
devolvería `None` igual, habiendo pisado otra fila. El registro de escrituras es lo único que
distingue "no devolvió nada" de "no escribió nada".

🔴 QUÉ CAMBIÓ CON LA MIGRACIÓN 108. Este archivo probaba la BARRERA DE EMPRESA del repo; esa
barrera ya no existe (el catálogo es global) y sus seis tests perdieron su caso. Lo que NO se
perdió está acá: la técnica de espiar `escrituras`, reencuadrada sobre un id inexistente. La
semántica nueva —el listado trae los de todas las empresas, cualquier id se alcanza— se afirma
en `test_clientes_global.py`, que es donde vive lo global.

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
UNO = UUID("11111111-1111-1111-1111-111111111111")
OTRO = UUID("22222222-2222-2222-2222-222222222222")
INACTIVO = UUID("33333333-3333-3333-3333-333333333333")
INEXISTENTE = UUID("99999999-9999-9999-9999-999999999999")


def _fila(id_, empresa, nombre, activo=True) -> dict:
    """La fila CONSERVA `empresa_id`: la 108 le sacó el NOT NULL, la 109 recién dropea la columna.
    Que el doble la traiga es lo que permite verificar que el repo ya no la mira."""
    return {"id": str(id_), "empresa_id": str(empresa), "nombre": nombre, "activo": activo,
            "created_at": datetime.now(UTC).isoformat(), "updated_at": None}


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({"clientes": [
        _fila(UNO, EMPRESA_A, "Acme"),
        _fila(OTRO, EMPRESA_B, "Globex"),
        _fila(INACTIVO, EMPRESA_A, "Zzz Cerrado", activo=False),
    ]})
    monkeypatch.setattr(repo_mod, "supabase_admin", a)
    return a


# ── Lo que la barrera de empresa dejó: la escritura acertada ──────────────────


class TestLaEscrituraVaDondeTieneQueIr:
    """🔴 ESTE BLOQUE HEREDA LA TÉCNICA DE `test_update_ajeno_no_escribe`, QUE PERDIÓ SU CASO.

    Aquel test era el ÚNICO de todo el módulo que miraba `Almacen.escrituras`, y por eso el único
    capaz de distinguir "no devolvió nada" de "no escribió nada": un `update` sin su `.eq()` en la
    query devuelve `None` igual —la relectura filtra— habiendo pisado otra fila. El caso "de otra
    empresa" desapareció con la 108; la técnica no, porque el modo de falla no era de la empresa
    sino del WHERE.

    ¿Qué tendría que ser distinto en el fake para que esto falle? Que `Almacen` no acumulara los
    filtros ni registrara las escrituras. Acumula TODOS los `(columna, valor)` y guarda cada
    UPDATE con su payload, así que un repo que escriba sin filtrar pisa las tres filas y se ve.
    """

    def test_el_update_de_un_id_inexistente_no_escribe_nada(self, almacen) -> None:
        antes = [dict(f) for f in almacen.catalogo["clientes"]]

        assert ClienteRepo().update(str(INEXISTENTE), {"nombre": "Hackeado"}) is None

        # 1. El id VIAJÓ EN LA QUERY. Sin esto, el UPDATE alcanzaría a cualquier fila.
        _, filtros, _ = almacen.escrituras[0]
        assert ("id", str(INEXISTENTE)) in filtros
        # 2. Y ninguna fila cambió. Las dos mitades: la primera dice qué se pidió, la segunda qué
        #    pasó. Con solo la primera, un doble que ignorara los filtros pasaría.
        assert almacen.catalogo["clientes"] == antes

    def test_el_update_de_un_id_real_escribe_solo_esa_fila(self, almacen) -> None:
        """El contraste. Sin él, "no escribió nada" pasaría con un repo que nunca escribe."""
        assert ClienteRepo().update(str(UNO), {"nombre": "Acme SA"}).nombre == "Acme SA"
        nombres = [f["nombre"] for f in almacen.catalogo["clientes"]]
        assert nombres == ["Acme SA", "Globex", "Zzz Cerrado"]


# ── Alta y baja lógica ────────────────────────────────────────────────────────


class TestAltaYBaja:
    def test_el_alta_no_manda_empresa(self, almacen) -> None:
        """Reemplaza a `test_el_alta_usa_la_empresa_del_body`. Ya no hay empresa que mandar: se
        verifica sobre la fila que QUEDÓ en el catálogo, o sea sobre el payload que el repo armó.

        La fila nueva no tiene la clave; las tres viejas sí. Es lo que distingue "no la mandó" de
        "el doble no la guarda"."""
        creado = ClienteRepo().save(ClienteCreate(nombre="  Initech  "))
        assert creado.nombre == "Initech"          # se le hace strip
        assert creado.activo is True               # default de la tabla

        nueva = [f for f in almacen.catalogo["clientes"] if f["nombre"] == "Initech"][0]
        assert "empresa_id" not in nueva, "el INSERT volvió a mandar la empresa"
        assert "empresa_id" in almacen.catalogo["clientes"][0], "el doble dejó de guardarla"

    def test_el_listado_esconde_los_inactivos_por_defecto(self, almacen) -> None:
        """El consumidor normal es el select de la carga de horas: no puede ofrecer un cliente
        dado de baja."""
        assert [c.nombre for c in ClienteRepo().find_all()] == ["Acme", "Globex"]

    def test_la_baja_es_logica(self, almacen) -> None:
        """No hay delete: `horas_proyecto.cliente_id` es una FK sin ON DELETE. Bajar un cliente
        lo saca del select y NO toca ninguna hora ya cargada."""
        assert not hasattr(ClienteRepo(), "delete")
        ClienteRepo().update(str(UNO), {"activo": False})
        assert [c.nombre for c in ClienteRepo().find_all()] == ["Globex"]
        assert len(ClienteRepo().find_all(incluir_inactivos=True)) == 3
