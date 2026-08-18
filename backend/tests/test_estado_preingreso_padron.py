"""
Comportamiento de las lecturas con un PREINGRESO en el padrón — el archivo que le da al backend
la primera fila que no es ni `activo` ni `baja`.

═══════════════════════════════════════════════════════════════════════════════════════════
🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
═══════════════════════════════════════════════════════════════════════════════════════════
**Que el padrón tenga un preingreso y alguien en licencia.** Es TODA la respuesta, y es la razón
de ser del archivo. Hasta hoy los 160 archivos de test tenían **4 filas de empleado no-activo en
total** (3 `baja`, 1 `licencia`) y **cero preingresos**, así que:

  · `= 'activo'`, `!= 'baja'` y "sin filtro de estado" seleccionaban EL MISMO conjunto;
  · los dos sitios que había que arreglar y los cinco contadores por fecha **no tenían un solo
    test capaz de rojear**: se los podía romper enteros y la suite quedaba verde.

Por eso el padrón trae, además del preingreso:
  · `lic1` EN LICENCIA — sin esta fila, `in_(ESTADOS_EN_PLANTILLA)` y `eq('activo')` darían lo
    mismo en el conteo por área, y "no rompimos la decisión de producto" sería indemostrable.
  · `fant1` ACTIVO PERO CON `fecha_egreso` CARGADA — la única fila que puede desmentir el
    `.eq("estado","baja")` que le faltaba al listado nominal de bajas. Sin ella, filtrar por
    estado y no filtrar devuelven lo mismo.
  · `pre1` con `fecha_ingreso` DENTRO del período — si estuviera fuera, el rango de fechas ya lo
    excluiría y el `neq` sería inobservable.

El fake es un mini-motor que APLICA los predicados (`eq`/`neq`/`in_`/`gte`/`lte`) sobre las
filas: nunca devuelve listas prefabricadas, y el `count` sale de lo que sobrevive al WHERE.

═══════════════════════════════════════════════════════════════════════════════════════════
⚠️ POR QUÉ NO ES `TestClient` AUNQUE LOS TESTS ENTREN POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════════════════════
En esta suite **no hay superficie autenticada alcanzable por HTTP**: no existe `conftest.py`, no
hay fixture de JWT, y el único archivo que levanta el app real (`test_rate_limit.py`) lo dice en
el docstring de su fixture — assessment es "la única superficie alcanzable sin JWT válido".
Llegar por HTTP exigiría falsear JWKS, `AuthMiddleware`, permisos y `empresas_cache`, que es
infraestructura nueva y ajena a lo que este archivo verifica.

Se entra por **la función del router con un `Request` real** (molde: `test_areas_export.py`),
que es el escalón más alto que el repo sabe ejercitar: recorre router → service → repo → query,
e incluye los `Query(None)` — que es exactamente donde vive el default del listado.
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

from datetime import date  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import UUID  # noqa: E402

import pytest  # noqa: E402
from starlette.requests import Request  # noqa: E402

import repositories._area_row as area_row_mod  # noqa: E402
import repositories._empleado_row as emp_row_mod  # noqa: E402
import repositories.empleado_repo as empleado_repo_mod  # noqa: E402
import routers.areas as areas_router  # noqa: E402
import routers.empleados as empleados_router  # noqa: E402
import services.dashboard_service as dash_mod  # noqa: E402
import services.reportes._reporte_dotacion as dot_mod  # noqa: E402
import services.reportes._reporte_movimientos as mov_mod  # noqa: E402
from services.area_service import AreaService  # noqa: E402
from services.dashboard_service import DashboardService  # noqa: E402
from services.empleado_service import EmpleadoService  # noqa: E402

EMPRESA = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
AREA = "11111111-1111-1111-1111-111111111111"

# 🔴 EL PERÍODO ES EL MES CORRIENTE, NO UNO FIJO. El KPI del dashboard calcula su rango con
# `date.today()` y no recibe mes/año, así que con un período escrito a mano (`3, 2026`) el
# preingreso caería FUERA del rango, el contador daría 0 por el motivo equivocado y el test
# pasaría con el `.neq()` borrado. Los generadores de reportes sí reciben mes/año: se les pasa
# el mismo mes corriente para que las dos superficies miren exactamente las mismas filas.
_HOY = date.today()
MES, ANIO = _HOY.month, _HOY.year
_DENTRO = date(ANIO, MES, 10).isoformat()   # dentro del período, en las dos superficies
_ANTES = "2020-01-05"                       # fuera, para que el rango no lo tome

_BASE = {"empresa_id": EMPRESA, "area_id": AREA, "roles": ["Analista"],
         "modalidad_trabajo": "presencial", "tipo_contrato": "Full time",
         "created_at": "2026-01-01T00:00:00+00:00"}

# 🔴 SEIS FILAS, CUATRO ESTADOS. Ver el encabezado: cada una existe para desmentir algo concreto.
_EMPLEADOS = [
    {**_BASE, "id": "act1", "estado": "activo",
     "nombre": "Ana", "apellido": "Activa", "fecha_ingreso": _DENTRO, "fecha_egreso": None},
    {**_BASE, "id": "act2", "estado": "activo",
     "nombre": "Bruno", "apellido": "Viejo", "fecha_ingreso": _ANTES, "fecha_egreso": None},
    {**_BASE, "id": "lic1", "estado": "licencia",
     "nombre": "Clara", "apellido": "Licencia", "fecha_ingreso": _ANTES, "fecha_egreso": None},
    {**_BASE, "id": "pre1", "estado": "preingreso",
     "nombre": "Diego", "apellido": "Preingreso", "fecha_ingreso": _DENTRO, "fecha_egreso": None},
    {**_BASE, "id": "baja1", "estado": "baja",
     "nombre": "Elsa", "apellido": "Egresada", "fecha_ingreso": _ANTES, "fecha_egreso": _DENTRO},
    {**_BASE, "id": "fant1", "estado": "activo",
     "nombre": "Fabio", "apellido": "Fantasma", "fecha_ingreso": _ANTES, "fecha_egreso": _DENTRO},
]

_AREAS = [{"id": AREA, "empresa_id": EMPRESA, "nombre": "Sistemas", "descripcion": None,
           "responsable_id": None, "activo": True, "created_at": "2026-01-01T00:00:00+00:00"}]


class _Q:
    """Mini-motor: aplica de verdad eq / neq / in_ / gte / lte sobre las filas de una tabla."""

    def __init__(self, filas: list) -> None:
        self._filas = list(filas)

    def select(self, *_a, **_k) -> "_Q":
        return self

    def eq(self, col, val) -> "_Q":
        self._filas = [f for f in self._filas if str(f.get(col)) == str(val)]
        return self

    def neq(self, col, val) -> "_Q":
        self._filas = [f for f in self._filas if str(f.get(col)) != str(val)]
        return self

    def in_(self, col, vals) -> "_Q":
        permitidos = {str(v) for v in vals}
        self._filas = [f for f in self._filas if str(f.get(col)) in permitidos]
        return self

    def gte(self, col, val) -> "_Q":
        self._filas = [f for f in self._filas if f.get(col) and str(f[col]) >= str(val)]
        return self

    def lte(self, col, val) -> "_Q":
        self._filas = [f for f in self._filas if f.get(col) and str(f[col]) <= str(val)]
        return self

    def ilike(self, *_a, **_k) -> "_Q":
        return self

    def is_(self, *_a, **_k) -> "_Q":
        return self

    def or_(self, *_a, **_k) -> "_Q":
        return self

    def order(self, *_a, **_k) -> "_Q":
        return self

    def limit(self, *_a, **_k) -> "_Q":
        return self

    def range(self, desde, hasta) -> "_Q":
        self._filas = self._filas[desde:hasta + 1]
        return self

    def execute(self):
        return SimpleNamespace(data=list(self._filas), count=len(self._filas))


class _DB:
    def __init__(self, tablas: dict) -> None:
        self._t = tablas

    def table(self, nombre: str) -> _Q:
        return _Q(self._t.get(nombre, []))


def _db() -> _DB:
    return _DB({"empleados": _EMPLEADOS, "areas": _AREAS})


def _request() -> Request:
    req = Request({"type": "http", "path": "/x", "headers": [], "client": ("6.6.6.6", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    req.state.empresa_id = EMPRESA
    return req


@pytest.fixture
def db_empleados(monkeypatch):
    """Parchea `supabase_admin` en TODOS los módulos que consultan `empleados` en este archivo.

    Los tres módulos satélite del dashboard (`_dashboard_kpis`, `_dashboard_headcount`,
    `_dashboard_alertas`) se parchean aunque ningún test afirme sobre ellos: sin eso salen a la
    red de verdad, fallan por DNS y el fail-safe por sección se los traga. No rompería este
    archivo, pero llenaría la corrida de ERROR reales y el próximo fallo de verdad quedaría
    escondido entre el ruido."""
    import services._dashboard_alertas as al_mod
    import services._dashboard_headcount as hc_mod
    import services._dashboard_kpis as kpis_mod
    modulos = (area_row_mod, emp_row_mod, empleado_repo_mod, dash_mod, dot_mod, mov_mod,
               al_mod, hc_mod, kpis_mod)
    for mod in modulos:
        monkeypatch.setattr(mod, "supabase_admin", _db(), raising=False)
    return _db()


# ── 0. Guardianes del fake ──────────────────────────────────────────────────────────────────

class TestElPadronPuedeDesmentir:
    """Sin estas condiciones, todo lo de abajo pasaría con los filtros borrados."""

    def test_hay_un_preingreso_y_alguien_en_licencia(self) -> None:
        estados = {e["estado"] for e in _EMPLEADOS}
        assert {"preingreso", "licencia", "baja", "activo"} <= estados

    def test_el_preingreso_ingresa_dentro_del_periodo(self) -> None:
        """Si su fecha cayera fuera, el rango ya lo excluiría y el `neq` sería inobservable.
        El período es el MES CORRIENTE porque el KPI del dashboard lo calcula con `date.today()`
        y no lo recibe por parámetro — ver el comentario de `_HOY`."""
        pre = next(e for e in _EMPLEADOS if e["estado"] == "preingreso")
        assert date.fromisoformat(pre["fecha_ingreso"]).month == _HOY.month
        assert date.fromisoformat(pre["fecha_ingreso"]).year == _HOY.year

    def test_hay_una_fecha_de_egreso_en_alguien_que_no_esta_de_baja(self) -> None:
        """`fant1` es la única fila que puede desmentir el `.eq("estado","baja")` de las bajas."""
        fant = next(e for e in _EMPLEADOS if e["id"] == "fant1")
        assert fant["estado"] != "baja" and fant["fecha_egreso"] is not None


# ── a) y b) El contador de empleados por área, por el router de /areas ───────────────────────

class TestElConteoPorArea:
    async def _areas(self) -> list:
        resp = await areas_router.list_areas(empresa_id=EMPRESA, search=None, page=1,
                                             page_size=20, service=AreaService())
        return resp.items

    async def test_un_preingreso_no_suma_al_contador_de_su_area(self, db_empleados) -> None:
        """(a) 6 filas en el área, pero el preingreso y la baja no son dotación → 4."""
        assert (await self._areas())[0].cantidad_empleados == 4

    async def test_alguien_en_licencia_si_suma(self, db_empleados, monkeypatch) -> None:
        """(b) La decisión de producto no se rompió al cambiar el filtro: si `licencia` hubiera
        quedado afuera del conjunto, el contador daría 3 en vez de 4."""
        assert (await self._areas())[0].cantidad_empleados == 4
        sin_licencia = [e for e in _EMPLEADOS if e["estado"] != "licencia"]
        monkeypatch.setattr(area_row_mod, "supabase_admin",
                            _DB({"empleados": sin_licencia, "areas": _AREAS}))
        assert (await self._areas())[0].cantidad_empleados == 3


# ── c) El KPI de ingresos del mes, por el router del dashboard ───────────────────────────────

class TestElKpiDeIngresos:
    async def test_un_preingreso_del_mes_no_cuenta_como_alta(self, db_empleados) -> None:
        """(c) `act1` y `pre1` ingresan en el período; solo `act1` es un alta."""
        resp = await dashboard_kpis()
        assert resp.kpis.ingresos_mes == 1

    async def test_y_las_bajas_del_mes_siguen_contando(self, db_empleados) -> None:
        """El contador hermano no se movió: `baja1` sí, `fant1` no (no está de baja)."""
        assert (await dashboard_kpis()).kpis.bajas_mes == 1


async def dashboard_kpis():
    import routers.dashboard as dash_router
    return await dash_router.get_dashboard(request=_request(), service=DashboardService())


# ── d) Los dos `ingresos_periodo` de los reportes de dotación ────────────────────────────────

class TestLosIngresosDeLosReportes:
    def test_headcount_no_cuenta_el_preingreso_como_alta(self, db_empleados) -> None:
        r = dot_mod.generate_headcount(MES, ANIO, UUID(EMPRESA))
        assert r["ingresos_periodo"] == 1
        assert r["bajas_periodo"] == 1

    def test_la_variacion_neta_sale_coherente(self, db_empleados) -> None:
        """(d) Hereda el filtro por construcción: `ingresos - bajas` sobre los dos locales ya
        corregidos, no una tercera query. Con el preingreso contado daría 1 en vez de 0."""
        r = dot_mod.generate_headcount(MES, ANIO, UUID(EMPRESA))
        assert r["variacion_neta"] == r["ingresos_periodo"] - r["bajas_periodo"] == 0

    def test_rotacion_tampoco_lo_cuenta(self, db_empleados) -> None:
        r = dot_mod.generate_rotacion(MES, ANIO, UUID(EMPRESA))
        assert r["ingresos_periodo"] == 1

    def test_el_headcount_total_sigue_siendo_solo_activos(self, db_empleados) -> None:
        """Grupo A intacto: `act1`, `act2` y `fant1` son los `activo`; licencia no entra acá."""
        assert dot_mod.generate_headcount(MES, ANIO, UUID(EMPRESA))["total_empleados"] == 3


# ── e) y f) El listado NOMINAL de altas y bajas ──────────────────────────────────────────────

class TestElListadoNominal:
    def _r(self) -> dict:
        return mov_mod.generate_altas_bajas(MES, ANIO, UUID(EMPRESA))

    def test_el_nombre_del_preingreso_no_aparece_en_las_altas(self, db_empleados) -> None:
        """(e) Es lo que más pesa del bloque: esto sale con nombre y apellido en un PDF."""
        altas = self._r()["altas"]
        assert [a["empleado"] for a in altas] == ["Activa, Ana"]
        assert not any("Preingreso" in a["empleado"] for a in altas)

    def test_una_baja_del_periodo_si_aparece(self, db_empleados) -> None:
        """(f) primera mitad."""
        assert [b["empleado"] for b in self._r()["bajas"]] == ["Egresada, Elsa"]

    def test_una_fecha_de_egreso_sin_estado_baja_no_aparece(self, db_empleados) -> None:
        """(f) segunda mitad — el filtro que FALTABA. `fant1` tiene `fecha_egreso` dentro del
        período y está `activo`: sin el `.eq("estado","baja")` figuraría como una baja que no
        ocurrió, y los totales de este reporte no coincidirían con los del dashboard."""
        assert not any("Fantasma" in b["empleado"] for b in self._r()["bajas"])
        assert self._r()["total_bajas"] == 1


# ── g) y h) El default del listado y del export, por el router de /empleados ─────────────────

class TestElDefaultDelListado:
    async def _listar(self, estado=None):
        return await empleados_router.list_empleados(
            request=_request(), page=1, page_size=20, area_id=None, estado=estado,
            search=None, es_lider=None, proyecto_id=None, sin_manager=None,
            service=EmpleadoService(),
        )

    async def test_sin_parametro_no_trae_preingresos(self, db_empleados) -> None:
        """(g) primera mitad. 6 filas en el padrón, 5 en el listado."""
        resp = await self._listar()
        ids = {i.id for i in resp.items}
        assert "pre1" not in ids
        assert len(ids) == 5 and resp.total == 5

    async def test_con_estado_preingreso_si_los_trae(self, db_empleados) -> None:
        """(g) segunda mitad: el default no ESCONDE filas, solo cambia qué se pide por omisión."""
        resp = await self._listar(estado="preingreso")
        assert [i.id for i in resp.items] == ["pre1"]

    async def test_el_estado_explicito_sigue_mandando_para_los_demas(self, db_empleados) -> None:
        assert [i.id for i in (await self._listar(estado="baja")).items] == ["baja1"]

    async def test_el_export_sale_con_el_mismo_criterio_que_el_listado(self, db_empleados) -> None:
        """(h) No se compara el archivo contra un número escrito a mano: se compara contra LO QUE
        DEVOLVIÓ EL LISTADO en la misma corrida. Si los dos criterios divergieran —que es el bug
        que el bloque B declara como invariante 1— esta igualdad se rompe."""
        del_listado = {i.id for i in (await self._listar()).items}
        capturado: dict = {}
        original = EmpleadoService.get_empleados

        def espia(self, page, page_size, *a, **k):
            pagina = original(self, page, page_size, *a, **k)
            capturado["ids"] = {i.id for i in pagina.items}
            return pagina

        EmpleadoService.get_empleados = espia
        try:
            await empleados_router.exportar_empleados(
                request=_request(), formato="csv", area_id=None, estado=None, search=None,
                es_lider=None, proyecto_id=None, sin_manager=None, service=EmpleadoService(),
            )
        finally:
            EmpleadoService.get_empleados = original
        assert capturado["ids"] == del_listado
        assert "pre1" not in capturado["ids"]
