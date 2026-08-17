"""
El fix de offboarding: iniciar el trámite NO da de baja, y la baja se efectiviza aparte.

Cubre las dos mitades del bug y el contador que lo hacía invisible:
  · `POST /api/offboarding` deja al empleado `activo` y sin `fecha_egreso`.
  · `POST /api/offboarding/{id}/efectivizar` lo da de baja CON fecha y cierra la instancia.
  · `bajas_mes` / `bajas_periodo` cuentan por `fecha_egreso`, no por `updated_at`.

Todo atraviesa HTTP contra la app real: ruteo, gates de permiso, Pydantic, services y repos
corren de verdad. Lo único falseado es la RESOLUCIÓN DE IDENTIDAD del middleware (tiene sus
propios tests y montarla exigiría un JWKS) y `supabase_admin`, reemplazado por el almacén de
abajo. El efecto sobre el empleado se lee del ALMACÉN, no del response: es la única forma de
afirmar qué quedó escrito en `empleados`.

## 🔴 QUÉ TENDRÍA QUE SER DISTINTO EN EL ALMACÉN PARA QUE ESTOS TESTS PUEDAN FALLAR

La pregunta obligatoria del repo, contestada por test:

  · **(a) y (b)** — que `dar_de_baja` escriba de verdad. El almacén APLICA los UPDATE sobre sus
    filas, así que si alguien repone la llamada en `_offboarding_iniciar`, la fila queda en
    `baja` y las dos aserciones rojean. Un doble que solo REGISTRARA las llamadas sin aplicarlas
    no podría distinguir "no lo dio de baja" de "lo dio de baja y no se nota".
  · **(c)** — lo mismo al revés: si `efectivizar` no escribiera, la fila seguiría `activo`.
  · **(d), (e), (f)** — que el almacén devuelva el `estado` real de la instancia y la
    `fecha_ingreso` real del empleado. Con filas prefabricadas por el test, las guardas
    afirmarían algo sobre una constante del propio test.
  · **(g) — EL QUE DISTINGUE LOS DOS MUNDOS.** El almacén filtra los rangos **por la columna que
    se le pidió**, y su UPDATE **mueve `updated_at` y NO toca `fecha_egreso`**, igual que el
    trigger de la base. Sin esas dos cosas el test no podría fallar: si los rangos ignoraran el
    nombre de la columna, `fecha_egreso` y `updated_at` serían indistinguibles y volver al
    `updated_at` viejo pasaría en verde; y si el UPDATE no moviera `updated_at`, la segunda mitad
    —editar el legajo y comprobar que el contador NO se mueve— no ejercitaría nada.
  · **(h)** — que las dos superficies lean del MISMO almacén. Con dos fakes separados, "los dos
    dan el mismo número" sería una coincidencia entre dos constantes.
  · **(i)** — nada del almacén: se afirma sobre el ruteo real de FastAPI.

## 🔴 LAS FECHAS SE CALCULAN DESDE HOY, Y NO SON DECORATIVAS

`GET /api/dashboard` **no acepta mes/año**: siempre informa el mes corriente. Así que la baja del
padrón tiene `fecha_egreso` el día 1 de ESTE mes (pasado, para no chocar con la guarda de fecha
futura) y `updated_at` en el mes ANTERIOR. Esa separación es la que da poder de distinción:

    contador          mes de fecha_egreso   mes de updated_at
    nuevo (correcto)         1                     0
    viejo (el bug)           0                     1

Los dos números se invierten, así que cualquiera de las dos aserciones caza una reversión. Con
fechas fijas escritas a mano el test caducaría al cambiar de mes.
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

from datetime import date, timedelta  # noqa: E402
from typing import Dict, List, Optional  # noqa: E402
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import middleware.auth as auth_mod  # noqa: E402
import repositories._empleado_lookup_repo as emp_lookup_mod  # noqa: E402
import repositories._empleado_row as emp_row_mod  # noqa: E402
import repositories._empleado_write_repo as emp_write_mod  # noqa: E402
import repositories._offboarding_activos_repo as activos_mod  # noqa: E402
import repositories.audit_repo as audit_repo_mod  # noqa: E402
import repositories.configuracion_repo as config_repo_mod  # noqa: E402
import repositories.empleado_repo as emp_repo_mod  # noqa: E402
import repositories.offboarding_repo as off_repo_mod  # noqa: E402
import repositories.reporte_repo as reporte_repo_mod  # noqa: E402
import services._dashboard_alertas as alertas_mod  # noqa: E402
import services._dashboard_headcount as headcount_mod  # noqa: E402
import services._dashboard_kpis as kpis_mod  # noqa: E402
import services.dashboard_service as dash_mod  # noqa: E402
import services.reportes._reporte_ausentismo as r_aus_mod  # noqa: E402
import services.reportes._reporte_costos as r_cost_mod  # noqa: E402
import services.reportes._reporte_distribucion as r_dist_mod  # noqa: E402
import services.reportes._reporte_dotacion as r_dot_mod  # noqa: E402
import services.reportes._reporte_movimientos as r_mov_mod  # noqa: E402
from main import app  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

USUARIO = str(uuid4())
EMPRESA = str(uuid4())
AREA = str(uuid4())
EMP_LIBRE = str(uuid4())        # activo y SIN proceso: el que arranca el offboarding en (a)/(b)
EMP_CON_PROCESO = str(uuid4())  # activo y CON instancia abierta: el que se efectiviza en (c)-(f)
EMP_BAJA = str(uuid4())         # baja consumada: el padrón de los contadores
INSTANCIA = str(uuid4())
INEXISTENTE = "33333333-3333-3333-3333-333333333333"

INGRESO = "2020-01-01"

# Ver "LAS FECHAS SE CALCULAN DESDE HOY" en el encabezado.
_HOY = date.today()
_PRIMERO = _HOY.replace(day=1)
_ULT_MES_PREVIO = _PRIMERO - timedelta(days=1)
EGRESO = _PRIMERO.isoformat()                                  # baja de ESTE mes
TOCADO = f"{_ULT_MES_PREVIO.isoformat()}T10:00:00+00:00"       # updated_at, mes ANTERIOR
MES_BAJA, ANIO_BAJA = _HOY.month, _HOY.year
MES_PREVIO, ANIO_PREVIO = _ULT_MES_PREVIO.month, _ULT_MES_PREVIO.year


# ── El almacén ────────────────────────────────────────────────────────────────────────────


class _Resp:
    def __init__(self, data, count=None) -> None:
        self.data, self.count = data, count


class _Not:
    def __init__(self, q: "_Q") -> None:
        self._q = q

    def in_(self, columna: str, valores) -> "_Q":
        self._q._not_in = (columna, [str(v) for v in valores])
        return self._q

    def is_(self, columna: str, valor) -> "_Q":
        self._q._not_null.append(columna)
        return self._q


class _Q:
    def __init__(self, almacen: "Almacen", tabla: str) -> None:
        self._a, self._t = almacen, tabla
        self._eq: List[tuple] = []
        self._neq: List[tuple] = []
        self._rangos: List[tuple] = []
        self._in: Optional[tuple] = None
        self._not_in: Optional[tuple] = None
        self._null: List[str] = []
        self._not_null: List[str] = []
        self._contar = False
        self._modo = "select"
        self._payload = None
        self._single = False

    def select(self, *a, **k) -> "_Q":
        self._contar = k.get("count") == "exact"
        return self

    def eq(self, columna: str, valor) -> "_Q":
        """ACUMULA. Quedarse con el último borraría la composición `estado='baja' AND rango`."""
        self._eq.append((columna, str(valor)))
        return self

    def neq(self, columna: str, valor) -> "_Q":
        """Lo usa el KPI de vacantes (`.neq("estado", "cerrada")`).

        ⚠️ Que falte un operador NO es inocuo acá: el dashboard es fail-safe POR SECCIÓN, así que
        un `AttributeError` en cualquier query de los KPIs se traga entero el bloque y devuelve
        `empleados_activos` y `bajas_mes` en 0 — un verde falso perfecto si los tests asertaran
        `== 0`. Por eso las aserciones de (b) y (h) piden números distintos de cero."""
        self._neq.append((columna, str(valor)))
        return self

    def gte(self, columna: str, valor) -> "_Q":
        """Registra la COLUMNA, no solo el valor: es lo que separa fecha_egreso de updated_at."""
        self._rangos.append((columna, ">=", str(valor)))
        return self

    def lte(self, columna: str, valor) -> "_Q":
        self._rangos.append((columna, "<=", str(valor)))
        return self

    def in_(self, columna: str, valores) -> "_Q":
        self._in = (columna, [str(v) for v in valores])
        return self

    def is_(self, columna: str, valor) -> "_Q":
        self._null.append(columna)
        return self

    def or_(self, *a, **k) -> "_Q":
        return self

    @property
    def not_(self) -> _Not:
        return _Not(self)

    def order(self, columna: str, **k) -> "_Q":
        return self

    def limit(self, n: int) -> "_Q":
        return self

    def range(self, desde: int, hasta: int) -> "_Q":
        return self

    def maybe_single(self) -> "_Q":
        self._single = True
        return self

    def single(self) -> "_Q":
        self._single = True
        return self

    def insert(self, payload) -> "_Q":
        self._modo, self._payload = "insert", payload
        return self

    def update(self, patch: dict) -> "_Q":
        self._modo, self._payload = "update", patch
        return self

    def _match(self, fila: dict) -> bool:
        if not all(str(fila.get(c)) == v for c, v in self._eq):
            return False
        if any(str(fila.get(c)) == v for c, v in self._neq):
            return False
        if self._in and str(fila.get(self._in[0])) not in self._in[1]:
            return False
        if self._not_in and str(fila.get(self._not_in[0])) in self._not_in[1]:
            return False
        if any(fila.get(c) is not None for c in self._null):
            return False
        if any(fila.get(c) is None for c in self._not_null):
            return False
        for col, op, val in self._rangos:
            actual = fila.get(col)
            # Un NULL no matchea ningún rango — igual que PostgREST. Es lo que hace que una baja
            # sin fecha_egreso no caiga en ningún período, en vez de caer en todos.
            if actual is None:
                return False
            if op == ">=" and str(actual) < val:
                return False
            if op == "<=" and str(actual) > val:
                return False
        return True

    def execute(self) -> _Resp:
        filas = self._a.catalogo.setdefault(self._t, [])
        if self._modo == "insert":
            nuevas = self._payload if isinstance(self._payload, list) else [self._payload]
            creadas = []
            for p in nuevas:
                fila = {"id": str(uuid4()), "created_at": self._a.ahora,
                        "updated_at": self._a.ahora, **p}
                filas.append(fila)
                creadas.append(fila)
            return _Resp(creadas)
        if self._modo == "update":
            tocadas = [f for f in filas if self._match(f)]
            for f in tocadas:
                f.update(self._payload)
                # 🔴 EMULA EL TRIGGER `updated_at` DE LA BASE, y es lo que le da sentido a (g):
                # toda escritura mueve `updated_at`, y ninguna toca `fecha_egreso` salvo que venga
                # en el payload. Sin esto, "editar el legajo no mueve el contador" no probaría nada.
                f["updated_at"] = self._a.ahora
            return _Resp(tocadas)
        halladas = [f for f in filas if self._match(f)]
        if self._single:
            return _Resp(halladas[0] if halladas else None)
        return _Resp(list(halladas), len(halladas) if self._contar else None)


class Almacen:
    def __init__(self, catalogo: Dict[str, List[dict]], ahora: str) -> None:
        self.catalogo, self.ahora = catalogo, ahora

    def table(self, tabla: str) -> _Q:
        return _Q(self, tabla)

    def fila(self, tabla: str, id_: str) -> dict:
        return next(f for f in self.catalogo[tabla] if str(f.get("id")) == str(id_))


def _empleado(id_: str, estado: str, fecha_egreso=None, updated_at=None) -> dict:
    return {
        "id": id_, "nombre": "Nom", "apellido": id_[:4], "email_corporativo": "n@k.com",
        "empresa_id": EMPRESA, "area_id": AREA, "roles": ["Analista"],
        "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": INGRESO, "estado": estado, "fecha_egreso": fecha_egreso,
        "motivo_baja": "renuncia" if estado == "baja" else None, "manager_id": None,
        "created_at": "2020-01-01T00:00:00+00:00", "updated_at": updated_at,
        "areas": {"nombre": "Tec"}, "empresas": {"nombre": "Karstec"},
    }


@pytest.fixture
def almacen() -> Almacen:
    return Almacen({
        "empleados": [
            _empleado(EMP_LIBRE, "activo"),
            _empleado(EMP_CON_PROCESO, "activo"),
            _empleado(EMP_BAJA, "baja", fecha_egreso=EGRESO, updated_at=TOCADO),
        ],
        "areas": [{"id": AREA, "nombre": "Tec", "empresa_id": EMPRESA, "activo": True}],
        "offboarding_instancias": [{
            "id": INSTANCIA, "empleado_id": EMP_CON_PROCESO, "empresa_id": EMPRESA,
            "estado": "iniciado", "motivo_egreso": "renuncia", "fecha_ultimo_dia": "2099-09-30",
            "created_at": "2026-08-01T00:00:00+00:00", "entrevista_salida": False,
            "notas_entrevista": None, "empleados": {"nombre": "Nom", "apellido": "Ape"},
            "empresas": {"nombre": "Karstec"},
        }],
        "offboarding_activos": [],
    }, ahora=TOCADO)


@pytest.fixture
def cliente(monkeypatch, almacen):
    """App real con identidad falseada y `supabase_admin` reemplazado en los módulos que lo usan.

    Se parchea MÓDULO POR MÓDULO porque cada uno hizo `from integrations.supabase_client import
    supabase_admin`, o sea que tiene su propia referencia ligada en tiempo de import: parchear el
    módulo de origen no alcanzaría y los repos seguirían saliendo a la red.
    """
    monkeypatch.setattr(auth_mod, "_extract_token", lambda r: "token")
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda t, p: USUARIO)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda uid: EstadoUsuario(rol="admin_rrhh", activo=True, resuelto=True))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
    monkeypatch.setattr(auth_mod, "sesion_expirada", lambda e: False)
    monkeypatch.setattr(auth_mod, "resolver_empresa_id", lambda h, p: EMPRESA)
    for mod in (emp_lookup_mod, emp_row_mod, emp_write_mod, emp_repo_mod, off_repo_mod,
                activos_mod, audit_repo_mod, config_repo_mod, reporte_repo_mod, dash_mod,
                headcount_mod, alertas_mod, kpis_mod, r_dot_mod, r_mov_mod, r_aus_mod,
                r_cost_mod, r_dist_mod):
        monkeypatch.setattr(mod, "supabase_admin", almacen, raising=False)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _alta(empleado_id: str) -> dict:
    return {"empleado_id": empleado_id, "motivo": "renuncia"}


async def _reporte(c, tipo: str, mes: int, anio: int) -> dict:
    r = await c.post("/api/reportes/generar",
                     json={"tipo": tipo, "mes": mes, "anio": anio, "empresa_id": EMPRESA})
    assert r.status_code == 201, r.text
    return r.json()["datos"]


# ── (a) y (b) — iniciar NO da de baja ─────────────────────────────────────────────────────


class TestIniciarNoDaDeBaja:
    """El bug original: abrir el trámite ponía `estado='baja'` con la persona trabajando."""

    async def test_a_el_empleado_sigue_activo_y_sin_fecha_egreso(self, cliente, almacen) -> None:
        async with cliente as c:
            r = await c.post("/api/offboarding", json=_alta(EMP_LIBRE))
        assert r.status_code == 201, r.text
        fila = almacen.fila("empleados", EMP_LIBRE)
        assert fila["estado"] == "activo"
        assert fila["fecha_egreso"] is None

    async def test_b_sigue_en_el_listado_de_activos_y_en_el_headcount(self, cliente) -> None:
        """No alcanza con que la fila diga `activo`: lo que importa es que las superficies que
        cuentan dotación lo sigan viendo. Son las dos que el bug vaciaba."""
        async with cliente as c:
            assert (await c.post("/api/offboarding", json=_alta(EMP_LIBRE))).status_code == 201
            listado = await c.get("/api/empleados?estado=activo")
            dashboard = await c.get("/api/dashboard")
        assert EMP_LIBRE in [e["id"] for e in listado.json()["items"]]
        cuerpo = dashboard.json()
        # Los dos activos del padrón: EMP_LIBRE (recién puesto en offboarding) y EMP_CON_PROCESO.
        assert cuerpo["kpis"]["empleados_activos"] == 2
        assert [h for h in cuerpo["headcount_por_area"] if h["total"] == 2]


# ── (c) a (f) — la efectivización y sus guardas ───────────────────────────────────────────


class TestEfectivizar:
    async def test_c_da_de_baja_con_fecha_y_cierra_la_instancia(self, cliente, almacen) -> None:
        async with cliente as c:
            r = await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar",
                             json={"fecha_egreso": EGRESO})
        assert r.status_code == 200, r.text
        emp = almacen.fila("empleados", EMP_CON_PROCESO)
        assert emp["estado"] == "baja" and emp["fecha_egreso"] == EGRESO
        assert almacen.fila("offboarding_instancias", INSTANCIA)["estado"] == "completado"

    async def test_c_bis_no_sincroniza_fecha_ultimo_dia(self, cliente, almacen) -> None:
        """Previsión y hecho son datos distintos: la previsión queda como estaba."""
        async with cliente as c:
            await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar", json={"fecha_egreso": EGRESO})
        assert almacen.fila("offboarding_instancias", INSTANCIA)["fecha_ultimo_dia"] == "2099-09-30"

    async def test_d_efectivizar_dos_veces_da_409(self, cliente) -> None:
        async with cliente as c:
            primera = await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar",
                                   json={"fecha_egreso": EGRESO})
            segunda = await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar",
                                   json={"fecha_egreso": EGRESO})
        assert primera.status_code == 200
        assert segunda.status_code == 409
        assert segunda.json()["code"] == "OFFBOARDING_YA_CERRADO"

    async def test_e_fecha_futura_da_400(self, cliente) -> None:
        """🔴 Es la guarda que impide reinstalar el bug: una fecha que todavía no ocurrió daría
        de baja HOY a alguien que sigue trabajando, que es exactamente lo que se arregló."""
        manana = (date.today() + timedelta(days=1)).isoformat()
        async with cliente as c:
            r = await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar",
                             json={"fecha_egreso": manana})
        assert r.status_code == 400 and r.json()["code"] == "FECHA_EGRESO_FUTURA"

    async def test_e_bis_la_fecha_futura_no_escribio_nada(self, cliente, almacen) -> None:
        """Un 400 que ya hubiera dado de baja sería peor que no validar."""
        manana = (date.today() + timedelta(days=1)).isoformat()
        async with cliente as c:
            await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar", json={"fecha_egreso": manana})
        assert almacen.fila("empleados", EMP_CON_PROCESO)["estado"] == "activo"
        assert almacen.fila("offboarding_instancias", INSTANCIA)["estado"] == "iniciado"

    async def test_f_fecha_anterior_al_ingreso_da_400(self, cliente) -> None:
        async with cliente as c:
            r = await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar",
                             json={"fecha_egreso": "2019-06-01"})
        assert r.status_code == 400 and r.json()["code"] == "FECHA_EGRESO_INVALIDA"

    async def test_instancia_inexistente_da_404(self, cliente) -> None:
        async with cliente as c:
            r = await c.post(f"/api/offboarding/{INEXISTENTE}/efectivizar",
                             json={"fecha_egreso": EGRESO})
        assert r.status_code == 404 and r.json()["code"] == "OFFBOARDING_NO_ENCONTRADO"

    async def test_el_contrato_de_error_es_el_unico(self, cliente) -> None:
        """Los rechazos salen con la misma forma `{error, message, code}`."""
        async with cliente as c:
            respuestas = [
                await c.post(f"/api/offboarding/{INEXISTENTE}/efectivizar",
                             json={"fecha_egreso": EGRESO}),
                await c.post(f"/api/offboarding/{INSTANCIA}/efectivizar",
                             json={"fecha_egreso": "2019-06-01"}),
            ]
        for r in respuestas:
            cuerpo = r.json()
            assert cuerpo["error"] is True
            assert set(cuerpo) >= {"error", "message", "code"}


# ── (g) y (h) — el contador ───────────────────────────────────────────────────────────────


class TestBajasSeCuentanPorFechaEgreso:
    """🔴 LOS TESTS QUE DISTINGUEN LOS DOS MUNDOS. Ver el encabezado del módulo.

    El padrón tiene UNA baja con `fecha_egreso` en el mes corriente y `updated_at` en el
    anterior. El contador viejo la imputaba al mes de `updated_at`; el nuevo, al de
    `fecha_egreso`. Los dos números se invierten, así que las aserciones cazan la reversión.
    """

    async def test_g_cuenta_en_el_mes_de_fecha_egreso(self, cliente) -> None:
        async with cliente as c:
            datos = await _reporte(c, "headcount", MES_BAJA, ANIO_BAJA)
        assert datos["bajas_periodo"] == 1   # con el contador viejo daba 0

    async def test_g_bis_no_cuenta_en_el_mes_de_updated_at(self, cliente) -> None:
        async with cliente as c:
            datos = await _reporte(c, "headcount", MES_PREVIO, ANIO_PREVIO)
        assert datos["bajas_periodo"] == 0   # con el contador viejo daba 1

    async def test_g_ter_editar_el_legajo_despues_no_mueve_el_contador(self, cliente, almacen) -> None:
        """La otra mitad del bug: con `updated_at`, tocarle el teléfono a alguien en otro mes
        movía su baja a ese mes. El contador cambiaba solo, sin que nadie diera de baja a nadie."""
        async with cliente as c:
            antes = (await _reporte(c, "headcount", MES_BAJA, ANIO_BAJA))["bajas_periodo"]
            almacen.ahora = "2099-06-05T09:00:00+00:00"
            r = await c.put(f"/api/empleados/{EMP_BAJA}", json={"telefono": "1122334455"})
            assert r.status_code == 200, r.text
            despues = (await _reporte(c, "headcount", MES_BAJA, ANIO_BAJA))["bajas_periodo"]
        fila = almacen.fila("empleados", EMP_BAJA)
        # El UPDATE movió `updated_at` de verdad — si no, esta mitad no ejercitaría nada.
        assert fila["updated_at"] == "2099-06-05T09:00:00+00:00"
        assert fila["fecha_egreso"] == EGRESO
        assert antes == 1 and despues == 1

    async def test_h_el_dashboard_y_el_reporte_dan_el_MISMO_numero(self, cliente) -> None:
        """Antes divergían: el dashboard contaba por `updated_at` y el reporte de movimientos por
        `fecha_egreso`, así que para el mismo mes decían cosas distintas sobre la misma gente.

        Se asertan DISTINTOS DE CERO además de iguales: el dashboard es fail-safe por sección, así
        que una excepción tragada daría 0 == 0 y el test pasaría sin haber contado nada."""
        async with cliente as c:
            dashboard = await c.get("/api/dashboard")
            movimientos = await _reporte(c, "altas_bajas", MES_BAJA, ANIO_BAJA)
        kpi = dashboard.json()["kpis"]["bajas_mes"]
        assert kpi == movimientos["total_bajas"] == 1


# ── (i) — el endpoint borrado ─────────────────────────────────────────────────────────────


class TestDeleteEmpleadoYaNoExiste:
    async def test_i_delete_empleado_no_responde(self, cliente) -> None:
        """🔑 405, no 404, y el motivo importa: el PATH `/api/empleados/{id}` SIGUE montado con
        GET y PUT, así que Starlette lo matchea y rechaza por MÉTODO. Un 404 significaría que el
        path entero desapareció, que no es el caso. Verificado contra el ruteo real, no adivinado.
        """
        async with cliente as c:
            r = await c.delete(f"/api/empleados/{EMP_LIBRE}")
        assert r.status_code == 405

    async def test_i_bis_el_path_sigue_vivo_para_get(self, cliente) -> None:
        """La contracara: si el 405 de arriba viniera de que el módulo entero se rompió, esto
        también fallaría. Con las dos aserciones, el 405 solo puede venir del método."""
        async with cliente as c:
            r = await c.get(f"/api/empleados/{EMP_LIBRE}")
        assert r.status_code == 200
