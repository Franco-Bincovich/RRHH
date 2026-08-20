"""
El parámetro OPCIONAL de orden del listado de empleados: `fecha_ingreso_asc` y `fecha_egreso_desc`.

Los pide el bloque de pantallas nuevas: "Próximos ingresos" es quién entra PRIMERO y "Bajas" es
quién se fue ÚLTIMO. Sin el parámetro el listado sigue saliendo por apellido, que es lo que ven
las ~37 pantallas que ya lo usan.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 QUÉ TENDRÍA QUE SER DISTINTO EN EL PADRÓN Y EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR
═══════════════════════════════════════════════════════════════════════════════════════════
Es la pregunta obligatoria del repo, y acá tiene tres respuestas porque hay tres formas de que
un test de orden sea una tautología:

  1. **El fake ORDENA DE VERDAD** con las claves que le pidieron, en el orden en que se
     encadenaron y con sort estable. Un fake que devolviera una lista fija dejaría el `.order()`
     sin efecto observable: se le podría sacar el orden entero y esto seguiría verde.

  2. **HAY EMPATES, Y CRUZAN EL CORTE DE PÁGINA.** Una FECHA empata mucho más fácil que un
     apellido —un lote de altas entra todo el mismo día y `fecha_ingreso` no tiene hora—, así que
     acá el empate es el caso normal, no el borde. El padrón tiene 10 filas que comparten fecha y
     caen en los puestos 5..14 de LOS DOS órdenes nuevos, o sea partidas por el corte de la
     página 1 con `page_size=10`. Si el bloque de empates cupiera entero en una página, sacar el
     desempate por `id` no rompería nada y el test no probaría nada.

  3. **Los empatados llegan en OTRO ORDEN en cada consulta**, que es la libertad que se toma
     Postgres: sin un ORDER BY total, dos consultas con OFFSET distinto no tienen por qué
     resolver los empates igual. `_Motor` lo modela invirtiendo la base en las llamadas pares.
     Es lo que hace que `.order("id")` sea falsable y no decoración.

⚠️ Se faltea el CLIENTE de Supabase, un escalón por debajo del repo — la regla del repo para todo
lo que tiene que viajar EN LA QUERY. Un fake de repo que ordenara en Python probaría el contrato
del service, no que el orden esté en la consulta. Molde: `tests/test_paginacion_orden.py`.

⚠️ El 422 del valor inválido SÍ entra por HTTP (`TestClient`), y es la única parte que lo
necesita: la validación del `Literal` la hace FastAPI al resolver los `Query`, así que llamando a
la función del router se saltea entera. La app mínima monta SOLO este router y le pone el
`request.state` a mano; no hay JWKS ni middleware de auth de por medio.
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

from datetime import date, datetime, timedelta  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from typing import List  # noqa: E402

import pytest  # noqa: E402

EMPRESA = "11111111-1111-1111-1111-111111111111"
PAGE_SIZE = 10
TOTAL = 30

# ── El padrón ────────────────────────────────────────────────────────────────────────────────
# 20 personas con fechas propias + 10 que comparten fecha de ingreso Y fecha de egreso.
#
# 🔴 LAS FECHAS DEL BLOQUE EMPATADO ESTÁN ELEGIDAS PARA QUE CAIGA EN LOS PUESTOS 5..14 DE LOS DOS
# ÓRDENES, que son distintos entre sí. No es un número redondo: es el único lugar donde el bloque
# queda partido por el corte de la página 1.
#   · por `fecha_ingreso` ASC  → 2020-01-10 cae entre la del índice 4 (01-09) y la del 5 (01-11).
#   · por `fecha_egreso` DESC  → 2026-01-30 cae entre la del índice 15 (01-31) y la del 14 (01-29).
INGRESO_BASE = date(2020, 1, 1)
EGRESO_BASE = date(2026, 1, 1)
INGRESO_EMPATADO = date(2020, 1, 10)
EGRESO_EMPATADO = date(2026, 1, 30)
IDS_EMPATADOS = [f"{100 + i:08d}-0000-0000-0000-000000000000" for i in range(10)]


def _fila(idx: int, ingreso, egreso) -> dict:
    return {
        "id": f"{idx:08d}-0000-0000-0000-000000000000",
        "nombre": f"Nom{idx:03d}",
        "apellido": f"Ape{idx:03d}",
        "area_id": "22222222-2222-2222-2222-222222222222",
        "empresa_id": EMPRESA,
        "roles": ["Analista"],
        "modalidad_trabajo": "presencial",
        "tipo_contrato": "permanente",
        "fecha_ingreso": ingreso,
        "fecha_egreso": egreso,
        "estado": "baja",
        "created_at": datetime(2020, 1, 1, 12, 0, 0),
    }


def _padron() -> List[dict]:
    filas = [
        _fila(i, INGRESO_BASE + timedelta(days=2 * i), EGRESO_BASE + timedelta(days=2 * i))
        for i in range(20)
    ]
    # ids 100..109: distintos entre sí, así que el desempate SIEMPRE puede resolverlos.
    filas += [_fila(100 + i, INGRESO_EMPATADO, EGRESO_EMPATADO) for i in range(10)]
    return filas


class _Motor:
    """Motor mínimo en memoria: filtra, ORDENA con las claves que le pidieron, y pagina."""

    def __init__(self, filas: List[dict], estado: dict) -> None:
        self._filas = list(filas)
        self._estado = estado
        self._ordenes: List[tuple] = []
        self._rango = None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) == str(val)]
        return self

    def neq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) != str(val)]
        return self

    def in_(self, col, vals):
        self._filas = [r for r in self._filas if str(r.get(col)) in {str(v) for v in vals}]
        return self

    def order(self, col, desc=False):
        self._ordenes.append((col, desc))
        return self

    def range(self, start, end):
        self._rango = (start, end)
        return self

    def execute(self):
        self._estado["llamadas"] += 1
        filas = list(self._filas)
        # 🔴 ACÁ ESTÁ LO QUE HACE FALSABLES A LOS TESTS DE DESEMPATE (punto 3 del encabezado).
        if self._estado["llamadas"] % 2 == 0:
            filas.reverse()
        # Multi-clave con sort estable: de la última a la primera, como cualquier ORDER BY.
        # La clave modela la colocación de NULOS de Postgres: ASC deja los nulos al final y DESC
        # los deja adelante, que es exactamente lo que hace el motor con los defaults.
        for col, desc in reversed(self._ordenes):
            filas = sorted(filas, key=lambda r: (r[col] is None, r[col] or date.min), reverse=desc)
        total = len(filas)
        if self._rango is not None:
            start, end = self._rango
            filas = filas[start:end + 1]
        return SimpleNamespace(data=filas, count=total)


@pytest.fixture
def repo(monkeypatch):
    """EmpleadoRepo contra el motor en memoria. Devuelve (repo, estado)."""
    import repositories.empleado_repo as mod

    estado = {"llamadas": 0}
    padron = _padron()
    monkeypatch.setattr(
        mod, "supabase_admin",
        type("C", (), {"table": lambda s, t: _Motor(padron, estado)})(),
    )
    return mod.EmpleadoRepo(), estado


def _espia(monkeypatch):
    """Captura los `.order()` que viajan en la query, sin traer ninguna fila."""
    import repositories.empleado_repo as mod

    ordenes: List[tuple] = []

    class _Q:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def neq(self, *a, **k):
            return self

        def in_(self, *a, **k):
            return self

        def order(self, col, desc=False):
            ordenes.append((col, desc))
            return self

        def range(self, *a, **k):
            return self

        def execute(self):
            return SimpleNamespace(data=[], count=0)

    monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
    return mod.EmpleadoRepo(), ordenes


# ═══════════════════════════════════════════════════════════════════════════════════════════
# (a) El default no se movió — es el test que protege a las ~37 pantallas que ya existen
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestSinOrdenElListadoSaleIgualQueAntes:
    """🔴 EL TEST MÁS IMPORTANTE DEL ARCHIVO. El parámetro es opcional y agregarlo no puede haber
    cambiado lo que ve nadie: el listado de colaboradores, el export, la ficha, los selectores y
    todo lo que pide `/api/empleados` sin decir nada de orden."""

    def test_la_query_lleva_los_tres_orders_de_siempre(self, monkeypatch) -> None:
        repo, ordenes = _espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA)
        assert ordenes == [("apellido", False), ("nombre", False), ("id", False)]

    def test_pasar_orden_None_explicito_es_lo_mismo_que_no_pasarlo(self, monkeypatch) -> None:
        """La firma nueva tiene default `None`. Si el default y el `None` explícito difirieran,
        cada caller elegiría orden según cómo escribió la llamada."""
        repo, ordenes = _espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA)
        sin_pasarlo = list(ordenes)
        ordenes.clear()
        repo.find_all(1, 20, EMPRESA, orden=None)
        assert ordenes == sin_pasarlo

    def test_las_filas_siguen_saliendo_por_apellido(self, repo) -> None:
        """No solo la query: el resultado. El padrón tiene apellidos correlativos con el índice,
        así que por apellido la página 1 son los índices 0..9."""
        r, _ = repo
        items, _total = r.find_all(1, PAGE_SIZE, EMPRESA)
        assert [e.apellido for e in items] == [f"Ape{i:03d}" for i in range(10)]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# (b) fecha_ingreso ASC — el que entra primero sale primero
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestOrdenPorFechaDeIngreso:
    def test_el_que_entra_primero_sale_primero(self, repo) -> None:
        r, _ = repo
        items, _total = r.find_all(1, PAGE_SIZE, EMPRESA, orden="fecha_ingreso_asc")
        fechas = [e.fecha_ingreso for e in items]
        assert fechas == sorted(fechas), f"no vino ordenado ascendente: {fechas}"
        assert items[0].fecha_ingreso == INGRESO_BASE

    def test_la_query_pide_fecha_ingreso_ascendente(self, monkeypatch) -> None:
        repo, ordenes = _espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA, orden="fecha_ingreso_asc")
        assert ordenes == [("fecha_ingreso", False), ("id", False)]

    def test_ya_no_ordena_por_apellido(self, monkeypatch) -> None:
        """Contracara: el orden nuevo REEMPLAZA al de siempre, no se le suma. Si `apellido`
        siguiera adelante, el parámetro no cambiaría nada — el apellido decidiría todo y la
        fecha quedaría de desempate."""
        repo, ordenes = _espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA, orden="fecha_ingreso_asc")
        assert "apellido" not in [c for c, _d in ordenes]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# (c) fecha_egreso DESC — el último que se fue sale primero
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestOrdenPorFechaDeEgreso:
    def test_el_ultimo_que_se_fue_sale_primero(self, repo) -> None:
        r, _ = repo
        items, _total = r.find_all(1, PAGE_SIZE, EMPRESA, orden="fecha_egreso_desc")
        fechas = [e.fecha_egreso for e in items]
        assert fechas == sorted(fechas, reverse=True), f"no vino descendente: {fechas}"
        assert items[0].fecha_egreso == EGRESO_BASE + timedelta(days=38), (
            "arriba tiene que estar la baja más reciente del padrón"
        )

    def test_la_query_pide_fecha_egreso_descendente(self, monkeypatch) -> None:
        repo, ordenes = _espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA, orden="fecha_egreso_desc")
        assert ordenes == [("fecha_egreso", True), ("id", False)]

    def test_el_desempate_va_ASCENDENTE_aunque_la_fecha_vaya_DESC(self, monkeypatch) -> None:
        """🔴 El `id` NO se invierte con la fecha. Lo pide la forma de los índices (ver
        `_empleado_orden.ordenado`): un desempate descendente ordenaría igual de bien pero
        obligaría a un nodo de sort."""
        repo, ordenes = _espia(monkeypatch)
        repo.find_all(1, 20, EMPRESA, orden="fecha_egreso_desc")
        assert ordenes[-1] == ("id", False)


# ═══════════════════════════════════════════════════════════════════════════════════════════
# (d) Empates: desempate por id ascendente y ninguna fila dos veces entre páginas
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestLosEmpatesDeFechaNoRompenLaPaginacion:
    """El bloque de 10 empatados cae en los puestos 5..14 de los dos órdenes: cruza el corte."""

    @pytest.mark.parametrize("orden", ["fecha_ingreso_asc", "fecha_egreso_desc"])
    def test_las_30_filas_aparecen_exactamente_una_vez(self, repo, orden) -> None:
        """🔴 Sin el `.order("id")`, la página 1 y la 2 traen los mismos empatados y los otros no
        salen en ninguna."""
        r, _ = repo
        vistos: List[str] = []
        for page in (1, 2, 3):
            items, _total = r.find_all(page, PAGE_SIZE, EMPRESA, orden=orden)
            vistos += [e.id for e in items]
        repetidos = sorted({i for i in vistos if vistos.count(i) > 1})
        faltantes = sorted({f["id"] for f in _padron()} - set(vistos))
        assert not repetidos, f"[{orden}] filas repetidas entre páginas: {repetidos}"
        assert not faltantes, f"[{orden}] filas que no aparecieron en ninguna página: {faltantes}"
        assert len(vistos) == TOTAL

    @pytest.mark.parametrize("orden", ["fecha_ingreso_asc", "fecha_egreso_desc"])
    def test_el_bloque_empatado_cruza_el_corte_de_pagina(self, repo, orden) -> None:
        """🔴 LA PREMISA DEL TEST DE ARRIBA, VERIFICADA Y NO SUPUESTA. Si el bloque de empates
        cupiera entero en una página, el desempate no haría falta y aquel test pasaría con
        `.order("id")` borrado. Acá se comprueba que las dos páginas tocan el bloque."""
        r, _ = repo
        p1 = {e.id for e in r.find_all(1, PAGE_SIZE, EMPRESA, orden=orden)[0]}
        p2 = {e.id for e in r.find_all(2, PAGE_SIZE, EMPRESA, orden=orden)[0]}
        empatados = set(IDS_EMPATADOS)
        assert p1 & empatados, f"[{orden}] la página 1 no toca el bloque empatado"
        assert p2 & empatados, f"[{orden}] la página 2 no toca el bloque empatado"

    @pytest.mark.parametrize("orden", ["fecha_ingreso_asc", "fecha_egreso_desc"])
    def test_los_empatados_salen_por_id_ascendente(self, repo, orden) -> None:
        """Dentro del bloque de fecha idéntica, el orden es el del `id`, de menor a mayor."""
        r, _ = repo
        vistos: List[str] = []
        for page in (1, 2, 3):
            vistos += [e.id for e in r.find_all(page, PAGE_SIZE, EMPRESA, orden=orden)[0]]
        solo_empatados = [i for i in vistos if i in set(IDS_EMPATADOS)]
        assert solo_empatados == IDS_EMPATADOS

    def test_el_motor_de_verdad_desordena(self, repo) -> None:
        """🔴 CONTRACARA OBLIGATORIA: si el motor dejara de reordenar entre llamadas, los tests de
        arriba pasarían sin desempate y serían tautologías."""
        _r, estado = repo
        crudo_1 = _Motor(_padron(), estado).range(0, 9).execute().data
        crudo_2 = _Motor(_padron(), estado).range(0, 9).execute().data
        assert [r["id"] for r in crudo_1] != [r["id"] for r in crudo_2]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# El orden LLEGA desde el service, no solo desde el repo
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestElOrdenViajaDeLaPuntaALaQuery:
    """🔴 ESTA CLASE EXISTE PORQUE UN MUTATION CHECK LA PIDIÓ, y vale escribir por qué.

    Todo lo de arriba entra por `EmpleadoRepo.find_all`. Con eso, sacarle el `orden` a la llamada
    que el SERVICE le hace al repo —`self._repo.find_all(..., sin_manager, orden)`— dejaba el
    archivo entero en verde: 29 tests pasando mientras la API ignoraba el parámetro en silencio.
    El repo tenía razón y los tests no lo podían desmentir, que es exactamente el modo de falla
    que la regla transversal describe.

    Acá se ejerce el tramo que faltaba: service → repo → query, para el listado Y para el export.
    """

    def _service_espiado(self, monkeypatch):
        from services.empleado_service import EmpleadoService

        repo, ordenes = _espia(monkeypatch)
        return EmpleadoService(repo=repo), ordenes

    def test_el_listado_propaga_el_orden(self, monkeypatch) -> None:
        service, ordenes = self._service_espiado(monkeypatch)
        service.get_empleados(1, 20, EMPRESA, orden="fecha_egreso_desc")
        assert ordenes == [("fecha_egreso", True), ("id", False)]

    def test_el_listado_sin_orden_sigue_saliendo_por_apellido(self, monkeypatch) -> None:
        service, ordenes = self._service_espiado(monkeypatch)
        service.get_empleados(1, 20, EMPRESA)
        assert ordenes == [("apellido", False), ("nombre", False), ("id", False)]

    def test_el_export_propaga_el_orden(self, monkeypatch) -> None:
        """El archivo tiene que salir en el orden que se ve. El export va por `get_empleados`,
        así que si el orden se cayera en el camino saldría ordenado por apellido sin avisar."""
        service, ordenes = self._service_espiado(monkeypatch)
        service.exportar(EMPRESA, "csv", orden="fecha_ingreso_asc")
        assert ordenes == [("fecha_ingreso", False), ("id", False)]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# (e) Un valor inválido es 422, no 500
# ═══════════════════════════════════════════════════════════════════════════════════════════
def _app_minima():
    """App con SOLO el router de empleados y el `request.state` puesto a mano.

    No hay `AuthMiddleware` ni JWKS: `require_permission` y `get_empresa_id` leen `request.state`,
    así que alcanza con sembrarlo. Es la app más chica que ejerce la validación de los `Query`,
    que es lo único que este bloque verifica.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from routers.empleados import router
    from utils.rate_limit import limiter

    app = FastAPI()
    app.state.limiter = limiter

    @app.middleware("http")
    async def _sembrar(request, call_next):
        request.state.user = {"id": "u1", "rol": "admin_rrhh"}
        request.state.empresa_id = EMPRESA
        return await call_next(request)

    app.include_router(router, prefix="/api/empleados")
    return TestClient(app, raise_server_exceptions=False)


class TestUnOrdenInvalidoEs422:
    """El vocabulario es un `Literal`, así que lo corta Pydantic en la frontera. Sin él, el valor
    viajaría hasta `ORDENES[orden]` y saldría un KeyError → 500 del handler global."""

    @pytest.mark.parametrize("valor", ["dni", "apellido_desc", "fecha_ingreso", "'; drop--", ""])
    def test_el_listado_rechaza_lo_que_no_esta_en_el_vocabulario(self, valor) -> None:
        cliente = _app_minima()
        assert cliente.get("/api/empleados", params={"orden": valor}).status_code == 422

    @pytest.mark.parametrize("valor", ["fecha_ingreso_asc", "fecha_egreso_desc"])
    def test_los_dos_validos_NO_dan_422(self, valor) -> None:
        """Contracara: si el endpoint rechazara todo, el test de arriba pasaría por el motivo
        equivocado. Acá no se afirma sobre el body —la base no está—, solo que la validación de
        los Query los deja pasar."""
        cliente = _app_minima()
        assert cliente.get("/api/empleados", params={"orden": valor}).status_code != 422

    def test_el_export_valida_con_el_MISMO_vocabulario(self) -> None:
        """El export acepta los mismos Query que el listado (invariante del bloque B), así que
        también tiene que rechazar lo mismo. Si aceptara cualquier string, el archivo saldría en
        un orden que la pantalla no puede pedir."""
        cliente = _app_minima()
        assert cliente.get("/api/empleados/exportar", params={"orden": "dni"}).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Conducta DECLARADA: los nulos de `fecha_egreso` salen ARRIBA en el orden descendente
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestLosNulosDeFechaEgresoQuedanArriba:
    """🔴 ESTO NO ES LO DESEABLE: ESTÁ PINEADO PARA QUE SEA UNA CONDUCTA DECLARADA Y NO UNA
    SORPRESA. En Postgres `ORDER BY ... DESC` es `NULLS FIRST` por default, y `postgrest` 0.17.2
    expone `nullsfirst=True` pero **no tiene `nullslast`**, así que `NULLS LAST` no se puede pedir
    desde el cliente. Consecuencia: una baja sin `fecha_egreso` —hoy alcanzable con un
    `PUT /api/empleados/{id}` que mande `estado: "baja"`, que no pasa por `dar_de_baja`— sale
    arriba de las bajas recientes.

    Si algún día se resuelve (vista, RPC o cliente nuevo), ESTE test es el que hay que dar vuelta,
    y su rojo es el aviso de que la conducta cambió.
    """

    @pytest.fixture
    def repo_con_nulos(self, monkeypatch):
        import repositories.empleado_repo as mod

        filas = [
            _fila(1, INGRESO_BASE, date(2026, 6, 1)),
            _fila(2, INGRESO_BASE, None),
            _fila(3, INGRESO_BASE, date(2026, 3, 1)),
        ]
        estado = {"llamadas": 1}  # impar: el motor no invierte, el orden lo decide el `.order()`
        monkeypatch.setattr(
            mod, "supabase_admin",
            type("C", (), {"table": lambda s, t: _Motor(filas, estado)})(),
        )
        return mod.EmpleadoRepo()

    def test_la_baja_sin_fecha_sale_primera(self, repo_con_nulos) -> None:
        items, _t = repo_con_nulos.find_all(1, 10, EMPRESA, orden="fecha_egreso_desc")
        assert items[0].fecha_egreso is None
        assert [e.fecha_egreso for e in items[1:]] == [date(2026, 6, 1), date(2026, 3, 1)]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# El vocabulario y su traducción no se pueden separar
# ═══════════════════════════════════════════════════════════════════════════════════════════
class TestElVocabularioYLaTraduccionSonElMismoConjunto:
    """`OrdenEmpleados` (schemas, lo que la API acepta) y `ORDENES` (repositories, contra qué
    columna se traduce) son dos mitades de lo mismo en dos capas distintas — o sea un espejo
    manual, que es la forma de deuda que este repo documenta una y otra vez. Acá se ata.

    Un valor en el Literal sin entrada en el mapa sale por `/docs` como válido y revienta con
    KeyError → 500. Uno en el mapa sin entrada en el Literal es código muerto que nadie puede
    pedir.
    """

    def _valores_del_literal(self) -> set:
        from typing import get_args

        from schemas._empleado_orden import OrdenEmpleados

        return set(get_args(OrdenEmpleados))

    def test_todo_valor_aceptado_tiene_columna(self) -> None:
        from repositories._empleado_orden import ORDENES

        assert self._valores_del_literal() - set(ORDENES) == set()

    def test_toda_columna_declarada_se_puede_pedir(self) -> None:
        from repositories._empleado_orden import ORDENES

        assert set(ORDENES) - self._valores_del_literal() == set()

    def test_la_derivacion_encuentra_algo(self) -> None:
        """Guarda contra el falso verde: si `get_args` devolviera vacío —porque alguien cambió el
        `Literal` por un `str`— los dos tests de arriba compararían dos conjuntos vacíos y
        pasarían sin haber comparado nada."""
        assert len(self._valores_del_literal()) >= 2

    def test_las_columnas_existen_en_la_tabla(self) -> None:
        """Que el mapa no apunte a una columna inventada: es el bug que `_postgrest_schema` caza
        en los selects, y acá el nombre viaja por otro camino (el `.order()`), que ese barrido no
        mira."""
        from repositories._empleado_orden import ORDENES
        from tests._postgrest_schema import cargar_schema

        columnas = set(cargar_schema().columnas["empleados"])
        pedidas = {col for col, _desc in ORDENES.values()} | {"id", "apellido", "nombre"}
        assert pedidas <= columnas, f"columnas de orden que no existen: {sorted(pedidas - columnas)}"
