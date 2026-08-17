"""
Los tres filtros de la migración 119 (tipo, periodicidad, área), el objeto que los transporta y
la traducción del 23505.

Vive aparte de `test_objetivos.py` (1.180 líneas) porque cubre una superficie nueva y porque tres
de sus bloques necesitan fakes propios: el cliente de Supabase que FILTRA arrays de verdad, y un
repo que sabe rebotar con un 23505.

## ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 **`FakeSupabase.contains()` COMPARA POR ELEMENTO.** Es el punto entero del bloque del
     área: si el doble hiciera contención de SUBCADENA, "Sistemas" encontraría
     "Sistemas Corporativos" y el test que separa las dos áreas pasaría igual con un
     `ILIKE '%...%'` en el repo — o sea, con el bug que la migración 119 vino a cerrar. Por eso
     el bloque 0 lo prueba ANTES de usarlo: **un fake nuevo se verifica primero, y sobre todo se
     verifica que sepa decir QUE NO.**
  2. 🔴 **El catálogo tiene un área que es PREFIJO de otra** ("Sistemas" vs "Sistemas
     Corporativos"). Sin ese par, el `.contains()` y un ILIKE devuelven el mismo conjunto y no
     hay test posible que los distinga.
  3. 🔴 **El catálogo tiene un OPERATIVO colgado de un ANUAL.** Sin esa fila, la promoción a raíz
     no ocurre y "el hijo se promueve" es indistinguible de "el hijo desaparece".
  4. 🔴 **El repo que rebota expone `.code`** como la `APIError` real de postgrest, y hay un
     contrapeso con OTRO error: si el traductor fuera un `except Exception` a secas, el
     contrapeso lo caza.
  5. 🔴 **El parser del fake y el encoder del repo son EL MISMO MÓDULO** (`utils.postgrest_array`),
     y hay un test de ida y vuelta que lo ata. Con dos interpretaciones del formato, el día que
     el encoder cambie el fake seguiría entendiendo el viejo y todo el bloque del área pasaría
     sin ejercitar nada.
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

from datetime import datetime  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

from repositories._objetivo_area import por_area  # noqa: E402
from schemas.objetivo import (  # noqa: E402
    TIPO_POR_DEFECTO, TIPOS, TIPOS_OPCIONES, ObjetivoCreate, ObjetivoUpdate,
)
from schemas.objetivo_filtros import ObjetivosFiltros  # noqa: E402
from services._objetivos_duplicado import duplicado_a_409, es_choque_de_unicidad  # noqa: E402
from services._objetivos_export import construir_filas_export  # noqa: E402
from services.objetivo_service import ObjetivoService  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from utils.errors import AppError  # noqa: E402
from utils.postgrest_array import (  # noqa: E402
    como_lo_manda_la_libreria, elementos_de, literal_array,
)

EMPRESA = uuid4()
USER = uuid4()
_TS = "2026-01-05T09:00:00+00:00"

# 🔴 Punto 2 y 3 del encabezado, en el catálogo de filas crudas que ve el repo REAL.
#   · "Sistemas" (raíz anual) vs "Sistemas Corporativos" (hijo operativo) → el par prefijo.
#   · el hijo operativo cuelga de un padre ANUAL → la promoción a raíz.
#   · "Legales, Compliance" con una coma adentro → el caso que parte `",".join` sin comillar.
_ID_PADRE, _ID_HIJO, _ID_SUELTO = str(uuid4()), str(uuid4()), str(uuid4())


def _fila(id_: str, titulo: str, tipo: str, areas, parent=None, periodicidad="") -> dict:
    return {
        "id": id_, "empresa_id": str(EMPRESA), "responsable_id": str(USER),
        "titulo": titulo, "descripcion": None, "prioridad": "media", "estado": "por_hacer",
        "fecha_entrega": None, "created_at": _TS, "updated_at": _TS, "parent_id": parent,
        "tipo": tipo, "periodicidad": periodicidad, "areas_involucradas": list(areas),
    }


_FILAS = [
    _fila(_ID_PADRE, "Plan anual de dotación", "anual", ["Sistemas", "Legales"]),
    _fila(_ID_HIJO, "Relevar proveedores", "operativo", ["Sistemas Corporativos"],
          parent=_ID_PADRE, periodicidad="primer trimestre"),
    _fila(_ID_SUELTO, "Cerrar el mes", "operativo", ["Legales, Compliance"],
          periodicidad="mensual"),
]


@pytest.fixture
def repo_real(monkeypatch):
    """El repo DE VERDAD contra un cliente falso que filtra arrays por elemento.

    🔴 PARCHEA LOS CUATRO MÓDULOS QUE IMPORTAN `supabase_admin` POR SU CUENTA. Es la misma trampa
    que documenta `_objetivo_filtros`: uno sin parchear no falla por una aserción, falla con
    ConnectError contra la red — un rojo que no dice nada. `_objetivo_area` no está en la lista
    porque NO importa el cliente: recibe la query ya construida.
    """
    import repositories._objetivo_responsables as resp_mod
    import repositories._objetivo_row as row_mod
    import repositories._objetivos_arbol as arbol_mod
    import repositories.objetivo_repo as mod

    fake = FakeSupabase({
        "objetivos": _FILAS,
        "empresas": [{"id": str(EMPRESA), "nombre": "Karstec"}],
        "users": [{"id": str(USER), "nombre": "Ana", "apellido": "Gómez"}],
        "objetivo_responsables": [],
    })
    for m in (mod, row_mod, resp_mod, arbol_mod):
        monkeypatch.setattr(m, "supabase_admin", fake)
    return mod.ObjetivoRepo(), fake


# ── 0. 🔴 LOS GUARDIANES DEL FAKE NUEVO — antes de usarlo para probar nada ────

class TestElFakeDeContainsSabeDecirQueNo:
    """Sin este bloque, todo el bloque del área es decorativo.

    Un `.contains()` de mentira que devolviera siempre todo, o que comparara subcadenas, haría
    que "el filtro es por elemento" y "el filtro es por subcadena" dieran el mismo resultado — y
    ése es exactamente el bug que la migración 119 vino a cerrar.
    """

    def _fake(self) -> FakeSupabase:
        return FakeSupabase({"t": [
            {"id": "a", "areas_involucradas": ["Sistemas", "Legales"]},
            {"id": "b", "areas_involucradas": ["Sistemas Corporativos"]},
            {"id": "c", "areas_involucradas": []},
        ]})

    def test_dice_que_SI_cuando_el_elemento_esta(self) -> None:
        fake = self._fake()
        filas = fake.table("t").select("*").contains("areas_involucradas", ["Sistemas"]).execute()
        assert [f["id"] for f in filas.data] == ["a"]

    def test_dice_que_NO_ante_un_PREFIJO(self) -> None:
        """🔴 LA ASERCIÓN QUE SOSTIENE EL ARCHIVO. "Sistemas" NO puede encontrar la fila cuyo
        único área es "Sistemas Corporativos": son dos áreas distintas. Si el fake dijera que sí,
        no habría forma de distinguir un `@>` de un `ILIKE '%Sistemas%'`."""
        fake = self._fake()
        filas = fake.table("t").select("*").contains("areas_involucradas", ["Sistemas"]).execute()
        assert "b" not in [f["id"] for f in filas.data]

    def test_dice_que_NO_ante_un_area_inexistente(self) -> None:
        fake = self._fake()
        filas = fake.table("t").select("*").contains("areas_involucradas", ["Compras"]).execute()
        assert filas.data == []

    def test_un_array_vacio_no_contiene_nada(self) -> None:
        fake = self._fake()
        filas = fake.table("t").select("*").contains("areas_involucradas", ["Legales"]).execute()
        assert "c" not in [f["id"] for f in filas.data]

    def test_con_dos_elementos_pide_LOS_DOS(self) -> None:
        """`@>` es AND, no OR. Si el fake hiciera OR, un multiselect futuro se escribiría contra
        una semántica que la base no tiene."""
        fake = self._fake()
        q = fake.table("t").select("*").contains("areas_involucradas", ["Sistemas", "Legales"])
        assert [f["id"] for f in q.execute().data] == ["a"]
        q2 = fake.table("t").select("*").contains("areas_involucradas", ["Sistemas", "Compras"])
        assert q2.execute().data == []

    def test_compone_por_AND_con_un_eq_y_no_lo_pisa(self) -> None:
        """El `.contains()` guarda su predicado aparte de `_columna`/`_ids`. Si los compartiera,
        `.eq(...).contains(...)` mediría UN filtro creyendo que mide dos."""
        fake = FakeSupabase({"t": [
            {"id": "a", "emp": "1", "areas_involucradas": ["Sistemas"]},
            {"id": "b", "emp": "2", "areas_involucradas": ["Sistemas"]},
        ]})
        q = fake.table("t").select("*").eq("emp", "1").contains("areas_involucradas", ["Sistemas"])
        assert [f["id"] for f in q.execute().data] == ["a"]

    def test_registra_lo_que_se_le_pidio(self) -> None:
        fake = self._fake()
        fake.table("t").select("*").contains("areas_involucradas", '{"Sistemas"}').execute()
        assert fake.contenciones == [("t", "areas_involucradas", ["Sistemas"])]


class TestElEncoderYElParserHablanElMismoFormato:
    """🔴 El fake parsea con `elementos_de` lo que el repo escribe con `literal_array`. Si fueran
    dos interpretaciones distintas del formato, el día que el encoder cambie el fake seguiría
    entendiendo el viejo y TODO el bloque del área pasaría sin haber filtrado nada."""

    @pytest.mark.parametrize("valores", [
        [],
        ["Sistemas"],
        ["Sistemas", "Legales"],
        ["Legales, Compliance"],          # 🔴 el que rompe `",".join` sin comillar
        ['Ventas "Norte"'],
        ["Sistemas Corporativos"],
    ])
    def test_ida_y_vuelta(self, valores) -> None:
        assert elementos_de(literal_array(valores)) == valores

    def test_un_area_con_coma_es_UN_solo_elemento(self) -> None:
        """La razón de ser de `literal_array`. Sin las comillas, PostgREST vería DOS elementos y
        la consulta pediría que el objetivo tenga las dos áreas — devolvería cero, sin error."""
        assert literal_array(["Legales, Compliance"]) == '{"Legales, Compliance"}'
        assert len(elementos_de('{"Legales, Compliance"}')) == 1
        assert len(elementos_de("{Legales, Compliance}")) == 2   # el contrapeso: sin comillas, 2

    def test_la_libreria_parte_el_valor_y_el_fake_lo_reproduce(self) -> None:
        """🔴 La pérdida que el fake TIENE que modelar para no ser más indulgente que PostgREST.
        `.contains(col, ["Legales, Compliance"])` no es equivalente a mandar el literal: la
        librería concatena sin comillar y el valor llega partido en dos."""
        assert como_lo_manda_la_libreria(["Legales, Compliance"]) == "{Legales, Compliance}"
        assert elementos_de(como_lo_manda_la_libreria(["Legales, Compliance"])) == [
            "Legales", "Compliance"]
        # Y el contraste: con el literal comillado del repo, el valor sobrevive entero.
        assert elementos_de(literal_array(["Legales, Compliance"])) == ["Legales, Compliance"]


def test_el_catalogo_tiene_un_area_que_es_prefijo_de_otra() -> None:
    """Punto 2 del encabezado. Sin este par, `@>` e `ILIKE` dan lo mismo y no hay test posible."""
    todas = [a for f in _FILAS for a in f["areas_involucradas"]]
    assert "Sistemas" in todas and "Sistemas Corporativos" in todas


def test_el_catalogo_tiene_un_operativo_colgado_de_un_anual() -> None:
    """Punto 3 del encabezado. Sin esta fila, la promoción a raíz no puede ocurrir."""
    padre = next(f for f in _FILAS if f["id"] == _ID_PADRE)
    hijo = next(f for f in _FILAS if f["id"] == _ID_HIJO)
    assert padre["tipo"] == "anual" and hijo["tipo"] == "operativo"
    assert hijo["parent_id"] == padre["id"]


# ── 1. 🔴 El filtro por área, contra el repo REAL ─────────────────────────────

def _titulos(raices) -> list:
    """Todos los títulos del árbol, RAÍCES E HIJOS, ordenados.

    🔴 POR QUÉ LOS TESTS DEL ÁREA NO AFIRMAN SOBRE `[r.titulo for r in raices]`, QUE ERA LO
    NATURAL. Porque así estaban escritos, y una mutación lo desmintió: al aflojar el
    `.contains()` del fake a comparación de SUBCADENA —o sea, al simular el `ILIKE '%Sistemas%'`
    que la migración 119 vino a sacar— el test `test_NO_matchea_un_PREFIJO` **siguió en verde**.

    El motivo es la forma del resultado, no el filtro: con la mutación, "Relevar proveedores"
    (área "Sistemas Corporativos") SÍ entraba al conjunto, pero como su padre también entraba,
    `armar_arbol` lo anidaba adentro y desaparecía de la lista de raíces. El `not in` se cumplía
    por la razón equivocada.

    Aplanar es lo único que hace que la aserción mire el CONJUNTO FILTRADO y no la forma del
    árbol. Es el caso #2 de la regla del repo con otra cara: el fake no mentía, mentía la
    proyección sobre la que se afirmaba.
    """
    return sorted([r.titulo for r in raices] + [h.titulo for r in raices for h in r.hijos])


class TestElFiltroDeAreaEsPorElemento:
    """El motivo entero por el que `areas_involucradas` pasó de `text` a `text[]`.

    ⚠️ Todas las aserciones de esta clase van sobre `_titulos()` (el árbol APLANADO) y no sobre
    las raíces. El porqué está en ese helper, y no es cosmético: con raíces, la mutación que
    convierte el filtro en un ILIKE parcial pasa en verde.
    """

    def test_encuentra_el_area_EXACTA(self, repo_real) -> None:
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA, ObjetivosFiltros(area="Sistemas"))

        assert _titulos(raices) == ["Plan anual de dotación"]

    def test_NO_matchea_un_PREFIJO(self, repo_real) -> None:
        """🔴 EL TEST DE LA SESIÓN. Con la columna en `text` y un `ILIKE '%Sistemas%'` esto NO
        podía pasar: "Relevar proveedores" (área "Sistemas Corporativos") habría entrado también.
        Es la aserción que separa un filtro honesto de uno que devuelve de más en silencio."""
        repo, _ = repo_real

        titulos = _titulos(repo.find_all(EMPRESA, ObjetivosFiltros(area="Sistemas")))

        assert "Relevar proveedores" not in titulos

    def test_el_area_larga_SI_encuentra_su_fila(self, repo_real) -> None:
        """Contrapeso del anterior: un filtro que no encontrara nada nunca también lo pasaría."""
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA, ObjetivosFiltros(area="Sistemas Corporativos"))

        assert _titulos(raices) == ["Relevar proveedores"]

    def test_encuentra_un_area_que_NO_es_la_primera_del_array(self, repo_real) -> None:
        """`@>` es contención, no comparación posicional: "Legales" está segunda en el padre."""
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA, ObjetivosFiltros(area="Legales"))

        assert _titulos(raices) == ["Plan anual de dotación"]

    def test_NO_matchea_un_area_que_CONTIENE_a_la_buscada(self, repo_real) -> None:
        """La otra dirección del prefijo, y la que el test de arriba deja pasar: "Legales" NO
        puede encontrar "Legales, Compliance". Con subcadena las dos filas entrarían, y como acá
        NINGUNA es hija de la otra, esta aserción no se puede cumplir por la forma del árbol."""
        repo, _ = repo_real

        titulos = _titulos(repo.find_all(EMPRESA, ObjetivosFiltros(area="Legales")))

        assert "Cerrar el mes" not in titulos

    def test_un_area_con_COMA_adentro_se_encuentra_entera(self, repo_real) -> None:
        """🔴 Si el valor viajara como lista, `",".join` lo partiría en dos y esto daría cero."""
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA, ObjetivosFiltros(area="Legales, Compliance"))

        assert _titulos(raices) == ["Cerrar el mes"]

    def test_sin_filtro_de_area_no_viaja_ningun_contains(self, repo_real) -> None:
        """Contrapeso: con un `.contains()` incondicional, todo lo de arriba pasaría igual."""
        repo, fake = repo_real

        repo.find_all(EMPRESA)

        assert fake.contenciones == []

    def test_el_valor_viaja_COMILLADO_en_la_query(self) -> None:
        """Un escalón más abajo: qué literal exacto recibe PostgREST. Se afirma sobre el valor
        CRUDO —no sobre el ya parseado— porque el comillado es justamente lo que se quiere fijar."""
        registrado = []

        class _Q:
            def contains(self, col, val):
                registrado.append((col, val))
                return self

        por_area(_Q(), "Legales, Compliance")

        assert registrado == [("areas_involucradas", '{"Legales, Compliance"}')]


# ── 2. 🔴 Las dos vistas ──────────────────────────────────────────────────────

class TestLasDosVistas:

    def test_un_ANUAL_no_aparece_filtrando_por_operativo(self, repo_real) -> None:
        repo, _ = repo_real

        titulos = [r.titulo for r in repo.find_all(EMPRESA, ObjetivosFiltros(tipo="operativo"))]

        assert "Plan anual de dotación" not in titulos

    def test_un_OPERATIVO_no_aparece_filtrando_por_anual(self, repo_real) -> None:
        repo, _ = repo_real

        titulos = [r.titulo for r in repo.find_all(EMPRESA, ObjetivosFiltros(tipo="anual"))]

        assert "Cerrar el mes" not in titulos and "Relevar proveedores" not in titulos

    def test_cada_vista_trae_lo_suyo(self, repo_real) -> None:
        """Contrapeso de los dos de arriba: un filtro que devolviera SIEMPRE vacío los pasaría."""
        repo, _ = repo_real

        anuales = repo.find_all(EMPRESA, ObjetivosFiltros(tipo="anual"))
        operativos = repo.find_all(EMPRESA, ObjetivosFiltros(tipo="operativo"))

        assert [r.titulo for r in anuales] == ["Plan anual de dotación"]
        assert sorted(r.titulo for r in operativos) == ["Cerrar el mes", "Relevar proveedores"]

    def test_un_operativo_colgado_de_un_anual_sale_como_RAIZ(self, repo_real) -> None:
        """🔴 EL TEST DE LA SESIÓN. Filtrando por operativo, el padre anual no pasa — y el hijo
        NO desaparece: se promueve al nivel superior. Es la invariante de `_objetivos_arbol`
        ("un hijo nunca desaparece") aplicada al eje nuevo."""
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA, ObjetivosFiltros(tipo="operativo"))

        promovido = [r for r in raices if r.titulo == "Relevar proveedores"]
        assert len(promovido) == 1, "el hijo operativo desapareció al filtrar por su propia vista"
        assert promovido[0].parent_id == _ID_PADRE, "el vínculo con el padre no se pierde"

    def test_en_la_vista_anual_ese_mismo_objetivo_es_HIJO(self, repo_real) -> None:
        """La otra mitad, y la que hace visible la consecuencia: el MISMO objetivo cuenta como
        raíz en una vista y como hijo en la otra. Sin filtro, es hijo."""
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA)

        padre = next(r for r in raices if r.titulo == "Plan anual de dotación")
        assert [h.titulo for h in padre.hijos] == ["Relevar proveedores"]
        assert "Relevar proveedores" not in [r.titulo for r in raices]

    def test_la_suma_de_las_dos_vistas_supera_el_total_de_raices(self, repo_real) -> None:
        """La consecuencia numérica de la promoción, medida y no argumentada: 1 + 2 > 2. No son
        filas duplicadas — es el hijo contando como raíz en la vista operativa."""
        repo, _ = repo_real

        sin_filtro = len(repo.find_all(EMPRESA))
        anuales = len(repo.find_all(EMPRESA, ObjetivosFiltros(tipo="anual")))
        operativos = len(repo.find_all(EMPRESA, ObjetivosFiltros(tipo="operativo")))

        assert (anuales, operativos, sin_filtro) == (1, 2, 2)
        assert anuales + operativos > sin_filtro

    def test_el_tipo_viaja_como_eq_y_no_como_contains(self, repo_real) -> None:
        """Que `tipo` sea `.eq()` y `area` `.contains()` no es intercambiable: con el tipo en un
        `contains` la query fallaría contra una columna que no es array."""
        repo, fake = repo_real

        repo.find_all(EMPRESA, ObjetivosFiltros(tipo="anual"))

        assert fake.contenciones == []


class TestElFiltroDePeriodicidad:

    def test_encuentra_por_valor_exacto(self, repo_real) -> None:
        repo, _ = repo_real

        raices = repo.find_all(EMPRESA, ObjetivosFiltros(periodicidad="mensual"))

        assert [r.titulo for r in raices] == ["Cerrar el mes"]

    def test_una_periodicidad_que_no_existe_da_vacio(self, repo_real) -> None:
        repo, _ = repo_real

        assert repo.find_all(EMPRESA, ObjetivosFiltros(periodicidad="trimestral")) == []

    def test_la_cadena_vacia_NO_filtra(self, repo_real) -> None:
        """`periodicidad=""` es "sin filtro", no "los que tienen la periodicidad vacía": el
        predicado se agrega con un `if` sobre el valor. Si filtrara, la vista anual —donde todos
        la tienen vacía— se volvería inalcanzable desde un formulario que manda el campo en
        blanco."""
        repo, _ = repo_real

        assert len(repo.find_all(EMPRESA, ObjetivosFiltros(periodicidad=""))) == 2


# ── 3. 🔴 El 23505 traducido a 409 ────────────────────────────────────────────

class _APIErrorFalsa(Exception):
    """Como la `APIError` de postgrest: lleva `.code` con el SQLSTATE. Molde real, no inventado
    — `postgrest/exceptions.py` expone `message`, `code`, `hint` y `details`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _RepoQueRebota:
    """Repo mínimo que choca el índice único en `save` y en `update`.

    🔴 `find_by_id` devuelve algo, para que `update` llegue al choque en vez de morir en el 404
    de "no existe": si devolviera None, el test del 409 en la edición estaría midiendo el 404.
    """

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.fila = object()

    def find_by_id(self, id, empresa_id=None):
        return self.fila

    def save(self, data):
        raise self._exc

    def update(self, id, data, empresa_id=None):
        raise self._exc

    def tiene_hijos(self, id, empresa_id=None) -> bool:
        return False


def _create() -> ObjetivoCreate:
    return ObjetivoCreate(empresa_id=EMPRESA, responsable_id=USER, titulo="Cerrar el trimestre")


@pytest.fixture
def users_ok(monkeypatch):
    """El responsable siempre valida: acá lo que se prueba es el choque, no el gate."""
    import services._objetivos_validaciones as val_mod
    monkeypatch.setattr(val_mod, "ensure_responsable_valido", lambda _id: None)
    import services.objetivo_service as svc_mod
    monkeypatch.setattr(svc_mod, "ensure_responsable_valido", lambda _id: None)


class TestElDuplicadoDa409:

    def test_el_ALTA_duplicada_da_409_y_no_500(self, users_ok) -> None:
        """🔴 EL TEST DE LA SESIÓN. Antes de esto la `APIError` subía hasta
        `global_error_handler` y salía como **500 INTERNAL_ERROR**: un error de servidor por un
        dato que el usuario puede corregir. Las migraciones 111 y 114 daban por hecho que estaba
        traducido desde hacía semanas."""
        exc = _APIErrorFalsa("23505", 'duplicate key value violates unique constraint '
                                      '"ux_objetivo_responsable_titulo"')
        svc = ObjetivoService(repo=_RepoQueRebota(exc))

        with pytest.raises(AppError) as e:
            svc.create(_create(), "tester")

        assert e.value.status_code == 409
        assert e.value.code == "OBJETIVO_DUPLICADO"

    def test_la_EDICION_duplicada_tambien_da_409(self, users_ok) -> None:
        """Cambiarle el título, la periodicidad o el TIPO a un objetivo puede dejarlo idéntico a
        otro. Es la razón por la que la traducción vive en el service y no envolviendo el insert."""
        exc = _APIErrorFalsa("23505", "duplicate key value violates unique constraint")
        svc = ObjetivoService(repo=_RepoQueRebota(exc))

        with pytest.raises(AppError) as e:
            svc.update(uuid4(), ObjetivoUpdate(tipo="operativo"))

        assert e.value.status_code == 409

    def test_el_mensaje_nombra_las_TRES_salidas(self, users_ok) -> None:
        """Un "ya existe" a secas deja a RRHH cambiando el título, que casi nunca es lo que
        quiere. La clave del índice tiene tres columnas que el usuario puede tocar."""
        exc = _APIErrorFalsa("23505", "duplicate key")
        svc = ObjetivoService(repo=_RepoQueRebota(exc))

        with pytest.raises(AppError) as e:
            svc.create(_create(), "tester")

        for palabra in ("título", "periodicidad", "vista"):
            assert palabra in e.value.message

    def test_un_error_que_NO_es_23505_sube_SIN_traducir(self, users_ok) -> None:
        """🔴 EL CONTRAPESO, y el que separa esto de un `except Exception` a secas. Un timeout o
        un 42703 (columna inexistente) no son un duplicado: convertirlos en 409 le diría al
        usuario que cambie el título de algo que no está duplicado, y escondería un bug real."""
        exc = _APIErrorFalsa("42703", 'column "tipoo" does not exist')
        svc = ObjetivoService(repo=_RepoQueRebota(exc))

        with pytest.raises(_APIErrorFalsa):
            svc.create(_create(), "tester")

    def test_un_AppError_del_repo_pasa_INTACTO(self) -> None:
        """Un 404 del repo no tiene que pasar por el detector de duplicados."""
        original = AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)

        with pytest.raises(AppError) as e:
            with duplicado_a_409():
                raise original

        assert e.value.code == "OBJETIVO_NOT_FOUND"

    @pytest.mark.parametrize("exc,esperado", [
        (_APIErrorFalsa("23505", "x"), True),
        (_APIErrorFalsa("42703", "x"), False),
        # `code` con el status HTTP: es lo que arma `generate_default_error_message` cuando el
        # body no es JSON. El 23505 sólo sobrevive en el texto, y por eso hay fallback.
        (_APIErrorFalsa("409", "duplicate key ... (SQLSTATE 23505)"), True),
        (RuntimeError("timeout"), False),
    ])
    def test_el_detector_distingue(self, exc, esperado) -> None:
        assert es_choque_de_unicidad(exc) is esperado


# ── 4. 🔴 El objeto de filtros: qué hace imposible el argumento corrido ───────

class TestElObjetoDeFiltros:
    """Las tres defensas, y la que NO existe. Ver `schemas/objetivo_filtros.py`."""

    def test_NO_se_puede_construir_POSICIONALMENTE(self) -> None:
        """🔴 La defensa principal: con siete `Optional[str]` en fila, un argumento corrido no
        daba error, daba el conjunto equivocado. Un BaseModel sólo acepta keywords, así que el
        corrimiento deja de ser expresable."""
        with pytest.raises(TypeError):
            ObjetivosFiltros("anual")           # type: ignore[misc]

    def test_un_nombre_de_filtro_MAL_ESCRITO_revienta(self) -> None:
        """`extra="forbid"`. Sin esto, `tipoo=` se perdería en silencio y el listado devolvería
        de más — que es exactamente cómo se ve el bug que este objeto viene a impedir."""
        with pytest.raises(Exception):
            ObjetivosFiltros(tipoo="anual")     # type: ignore[call-arg]

    def test_un_valor_de_OTRO_vocabulario_en_el_slot_de_tipo_revienta(self) -> None:
        """`tipo` es el único con vocabulario cerrado, así que es el único cuyo VALOR puede
        desmentir un cruce: un estado o una prioridad ahí no construyen."""
        for ajeno in ("por_hacer", "alta", "mensual"):
            with pytest.raises(Exception):
                ObjetivosFiltros(tipo=ajeno)    # type: ignore[arg-type]

    def test_los_valores_legitimos_SI_construyen(self) -> None:
        """Contrapeso: un modelo que rechazara todo pasaría los tres tests de arriba."""
        f = ObjetivosFiltros(estado="por_hacer", responsable_id=str(USER), prioridad="alta",
                             tipo="anual", periodicidad="mensual", area="Sistemas")
        assert (f.tipo, f.area) == ("anual", "Sistemas")

    def test_es_INMUTABLE(self) -> None:
        """`frozen=True`: el service no puede reescribir un filtro que le llegó del router, así
        que lo que se ve en la URL es lo que llega a la query."""
        f = ObjetivosFiltros(tipo="anual")
        with pytest.raises(Exception):
            f.tipo = "operativo"                # type: ignore[misc]

    def test_intercambiar_los_DOS_TEXTOS_LIBRES_sigue_siendo_construible(self) -> None:
        """🔴 LO QUE EL OBJETO **NO** RESUELVE, fijado a propósito para que nadie lo venda de más.

        `periodicidad` y `area` son los dos texto libre: ningún tipo puede distinguirlos, y
        `ObjetivosFiltros(area="mensual")` es un filtro perfectamente válido por un área que se
        llama "mensual". Lo que desapareció es el corrimiento SILENCIOSO por posición; para
        equivocarse ahora hay que escribir mal el NOMBRE del filtro, que se ve en el diff.

        Si algún día este test empieza a fallar, es porque alguien cerró el vocabulario de uno de
        los dos — y ahí hay que actualizar el docstring del schema, no borrar el test.
        """
        f = ObjetivosFiltros(area="mensual", periodicidad="Sistemas")
        assert (f.area, f.periodicidad) == ("mensual", "Sistemas")


# ── 5. Los dos defaults, que no son el mismo ─────────────────────────────────

class TestLosDosDefaults:

    def test_el_ALTA_nace_OPERATIVO(self) -> None:
        """El default de PRODUCTO: la vista permisiva. Mandar un objetivo cualquiera a la vista
        que ve el directorio es peor error que al revés."""
        assert _create().tipo == "operativo"
        assert TIPO_POR_DEFECTO == "operativo"

    def test_el_IMPORT_hereda_ese_default_sin_una_linea_propia(self) -> None:
        """`objetivos_import_service._a_create` arma un `ObjetivoCreate` SIN `tipo`. Mientras el
        Excel no traiga su columna (sesión 2), todo lo importado nace operativo."""
        from services.objetivos_import_service import ObjetivosImportService
        from schemas.importacion_objetivos import FilaObjetivoPreview

        fila = FilaObjetivoPreview(fila=2, titulo="Del Excel", responsable="ana@x.com",
                                   responsable_id=str(USER), responsable_nombre="Ana Gómez",
                                   prioridad="media", fecha_entrega=None, descripcion=None,
                                   responsables_ids=[])

        assert ObjetivosImportService._a_create(fila, EMPRESA).tipo == "operativo"

    def test_el_default_de_la_COLUMNA_es_otro_y_esta_en_la_migracion(self) -> None:
        """No se puede afirmar contra la base desde acá, así que se afirma contra el ARCHIVO: la
        migración 119 declara `DEFAULT 'anual'` y este test lo ata. Si alguien "unifica" los dos
        defaults cambiando la migración, esto rojea y obliga a leer el porqué."""
        from pathlib import Path
        sql = (Path(__file__).resolve().parent.parent / "migrations"
               / "119_objetivo_tipo_y_areas_array.sql").read_text(encoding="utf-8")
        assert "tipo text NOT NULL DEFAULT 'anual'" in sql
        assert TIPO_POR_DEFECTO != "anual", "los dos defaults NO son el mismo, a propósito"


# ── 6. El export y el vocabulario servido por endpoint ───────────────────────

class TestElExportTraeLasTresColumnas:

    def _items(self):
        from repositories._objetivos_arbol import armar_arbol
        from repositories._objetivo_row import ObjetivoResponse as _OR  # noqa: F401
        from schemas.objetivo import ObjetivoResponse
        return armar_arbol([ObjetivoResponse.model_validate(
            {**f, "empresa_nombre": "Karstec", "responsable_nombre": "Ana Gómez",
             "created_at": datetime(2026, 1, 5, 9, 0), "updated_at": datetime(2026, 1, 5, 9, 0)}
        ) for f in _FILAS])

    def test_las_tres_columnas_estan(self) -> None:
        fila = construir_filas_export(self._items())[0]
        assert {"Tipo", "Periodicidad", "Áreas involucradas"} <= set(fila)

    def test_las_areas_se_unen_con_PUNTO_Y_COMA_y_no_con_coma(self) -> None:
        """🔴 Con coma, un área que TIENE una coma adentro ("Legales, Compliance") se leería en
        el Excel como dos — la ambigüedad que la migración 119 sacó de la base, reintroducida en
        el archivo. El `;` es además el separador que el import ya entiende."""
        filas = {f["Título"]: f for f in construir_filas_export(self._items())}
        assert filas["Plan anual de dotación"]["Áreas involucradas"] == "Sistemas; Legales"
        assert filas["Cerrar el mes"]["Áreas involucradas"] == "Legales, Compliance"

    def test_un_objetivo_sin_areas_sale_con_la_celda_VACIA_y_no_con_corchetes(self) -> None:
        sin_areas = [f for f in construir_filas_export(self._items())
                     if f["Título"] == "Relevar proveedores"][0]
        assert "[" not in sin_areas["Áreas involucradas"]

    def test_el_tipo_sale_en_su_columna(self) -> None:
        filas = {f["Título"]: f for f in construir_filas_export(self._items())}
        assert filas["Plan anual de dotación"]["Tipo"] == "anual"
        assert filas["Cerrar el mes"]["Tipo"] == "operativo"


class TestElVocabularioServidoPorEndpoint:

    async def test_el_endpoint_devuelve_los_dos_tipos(self) -> None:
        from routers.objetivos_catalogos import campos_objetivo

        assert [o["value"] for o in (await campos_objetivo())["tipos"]] == ["anual", "operativo"]

    def test_los_values_son_EXACTAMENTE_el_vocabulario_del_Literal(self) -> None:
        """🔴 La aserción que justifica el endpoint. Los `value` son a la vez el CHECK de la
        migración 119 y el `Literal` de los schemas: si el catálogo ofreciera un valor de más (o
        de menos), el front mostraría en un selector algo que el backend rechaza con 422."""
        assert {o["value"] for o in TIPOS_OPCIONES} == TIPOS

    def test_cada_opcion_tiene_etiqueta_legible(self) -> None:
        assert all(o["label"] and o["label"] != o["value"] for o in TIPOS_OPCIONES)

    def test_la_ruta_esta_montada(self) -> None:
        from fastapi.routing import APIRoute
        from main import app

        rutas = {r.path for r in app.routes if isinstance(r, APIRoute) and "GET" in r.methods}
        assert "/api/objetivos/campos" in rutas

    def test_campos_se_registra_ANTES_que_cualquier_ruta_parametrica_del_modulo(self) -> None:
        """Hoy no hay un `GET /api/objetivos/{id}` con el que colisionar, pero
        `ObjetivoService.get_by_id` ya está escrito esperando uno. Starlette resuelve por ORDEN DE
        REGISTRO: el día que aparezca, `/campos` entraría como `id="campos"` y moriría en un 422.
        Es lo que le pasó a `asignaciones_capacitacion` y nadie lo notó por meses."""
        from fastapi.routing import APIRoute
        from main import app

        paths = [r.path for r in app.routes
                 if isinstance(r, APIRoute) and r.path.startswith("/api/objetivos")]
        parametricas = [i for i, p in enumerate(paths) if "{" in p]
        assert paths.index("/api/objetivos/campos") < min(parametricas)


# ── 7. La paridad listado ↔ export, en los tres filtros nuevos ───────────────

def test_el_export_acepta_los_tres_filtros_nuevos() -> None:
    """`test_paridad_list_export` ya barre esto automáticamente para todo el repo; acá se fija
    por NOMBRE para que, si alguien saca objetivos de aquel barrido, quede este.

    ⚠️ Y es la razón por la que los seis Query se declaran DOS VECES en el router en vez de en un
    `Depends` común: la introspección de aquel barrido lee `route.dependant.query_params`, que no
    incluye los de las sub-dependencias — con un `Depends`, los dos endpoints reportarían cero
    filtros y la comparación se cumpliría por vacío."""
    from fastapi.routing import APIRoute
    from main import app

    rutas = {r.path: {p.name for p in r.dependant.query_params}
             for r in app.routes if isinstance(r, APIRoute) and "GET" in r.methods}
    nuevos = {"tipo", "periodicidad", "area"}

    assert nuevos <= rutas["/api/objetivos"]
    assert nuevos <= rutas["/api/objetivos/exportar"]
