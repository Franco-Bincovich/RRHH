"""
Recategorizaciones — las dos reglas de la fecha retroactiva, permisos y CRUD, POR HTTP.

## 🚨 LAS TRES PREGUNTAS PREVIAS, CONTESTADAS ANTES DE ESCRIBIR NADA

**1. ¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?**

  · **🔴 `lt`/`neq`/`order` FILTRAN DE VERDAD SOBRE LA FECHA.** Es LA condición del archivo: los
    cuatro tests de las reglas 1 y 2 preguntan "¿cuál es la previa a esta fecha?" y "¿cuál es la
    más reciente?", y **un almacén que devolviera siempre el mismo conjunto los volvería vacuos
    a los cuatro a la vez**. Acá `lt` compara fechas ISO, `neq` excluye, y `order(desc=True) +
    limit(1)` devuelve realmente la primera. Se verifica en `TestElAlmacenPuedeDesmentir`.
  · **El almacén tiene 120 filas** en la planilla: con ≤ page_size, paginar y no paginar dan lo
    mismo.
  · **`count="exact"` se honra** y sale del total ANTES de recortar.
  · **La escritura se arma A PARTIR del payload recibido**: si el repo deja de mandar un campo,
    la fila no lo tiene y el schema no valida. Un `insert` que devolviera una constante del test
    estaría afirmando algo sobre su propia constante.
  · **El empleado del almacén tiene DOS roles** (`ANALISTA`, `SOPORTE`). Con uno solo,
    "reemplaza la lista entera" y "reemplaza solo roles[0]" son indistinguibles.
  · **`EmpleadoService` es el REAL**, corriendo sobre el mismo almacén. Un doble que registrara
    "me llamaron" no podría desmentir QUÉ se escribió en `empleados.roles`.

**2. ¿El fake ES lo que estoy probando?** No. Lo falseado es el CLIENTE DE SUPABASE (un escalón
por debajo de los repos) y la resolución de identidad del middleware. El repo, el service, las
dos reglas, los schemas, los gates y el ruteo son los REALES, y los requests entran por HTTP.

**3. ¿El test replica adentro lo que dice verificar?** No hay ningún valor esperado copiado del
código de producción: los `*_anterior` se comparan contra lo que se cargó en el almacén, el
efecto sobre el empleado se lee de la fila del almacén (no del response), y los dos 404 se
comparan entre sí.
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

from typing import Dict, List, Optional  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import middleware.auth as auth_mod  # noqa: E402
import repositories._empleado_lookup_repo as emp_lookup_mod  # noqa: E402
import repositories._empleado_write_repo as emp_write_mod  # noqa: E402
import repositories._recategorizacion_cadena as cadena_mod  # noqa: E402
import repositories._recategorizacion_row as row_mod  # noqa: E402
import repositories._recategorizacion_write_repo as write_mod  # noqa: E402
import repositories.recategorizacion_repo as repo_mod  # noqa: E402
from main import app  # noqa: E402
from routers.recategorizaciones import _service as _dep_lecturas  # noqa: E402
from routers.recategorizaciones_empleado import _service as _dep_ficha  # noqa: E402
from routers.recategorizaciones_escrituras import _service as _dep_escrituras  # noqa: E402
import routers._recategorizaciones_costos as costos_dep_mod  # noqa: E402
from services.empleado_service import EmpleadoService  # noqa: E402
from services.recategorizacion_service import RecategorizacionService  # noqa: E402
from utils.permisos import Seccion  # noqa: E402
from utils.permisos import puede as puede_real  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

BASE = "/api/recategorizaciones"
USUARIO = str(uuid4())
EMPRESA = str(uuid4())
OTRA_EMPRESA = str(uuid4())
EMPLEADO = str(uuid4())
AREA = str(uuid4())
INEXISTENTE = "33333333-3333-3333-3333-333333333333"
OTRO_INEXISTENTE = "44444444-4444-4444-4444-444444444444"
TOTAL_PLANILLA = 120


# ── El doble del cliente de Supabase ──────────────────────────────────────────


class _Resp:
    def __init__(self, data, count=None) -> None:
        self.data, self.count = data, count


class _Q:
    """Query encadenable. `eq`/`neq`/`lt`/`gte`/`lte`/`in_`/`order`/`range` filtran DE VERDAD."""

    def __init__(self, a: "Almacen", tabla: str) -> None:
        self._a, self._t = a, tabla
        self._eq: List[tuple] = []
        self._neq: List[tuple] = []
        self._cmp: List[tuple] = []
        self._in: Optional[tuple] = None
        self._orden: Optional[tuple] = None
        self._rango: Optional[tuple] = None
        self._limit: Optional[int] = None
        self._single = False
        self._modo, self._payload, self._count = "select", None, None

    def select(self, cols: str = "*", count=None) -> "_Q":
        self._count = count
        return self

    def eq(self, c, v) -> "_Q":
        self._eq.append((c, str(v)))
        return self

    def neq(self, c, v) -> "_Q":
        self._neq.append((c, str(v)))
        return self

    def lt(self, c, v) -> "_Q":
        self._cmp.append((c, "<", str(v)))
        return self

    def gte(self, c, v) -> "_Q":
        self._cmp.append((c, ">=", str(v)))
        return self

    def lte(self, c, v) -> "_Q":
        self._cmp.append((c, "<=", str(v)))
        return self

    def in_(self, c, vals) -> "_Q":
        self._in = (c, [str(v) for v in vals])
        return self

    def order(self, c, **k) -> "_Q":
        self._orden = (c, bool(k.get("desc")))
        return self

    def range(self, d, h) -> "_Q":
        self._rango = (d, h)
        return self

    def limit(self, n) -> "_Q":
        self._limit = n
        return self

    def maybe_single(self) -> "_Q":
        self._single = True
        return self

    def single(self) -> "_Q":
        self._single = True
        return self

    def insert(self, p) -> "_Q":
        self._modo, self._payload = "insert", p
        return self

    def update(self, p) -> "_Q":
        self._modo, self._payload = "update", p
        return self

    def _match(self, f: dict) -> bool:
        if not all(str(f.get(c)) == v for c, v in self._eq):
            return False
        if any(str(f.get(c)) == v for c, v in self._neq):
            return False
        if self._in and str(f.get(self._in[0])) not in self._in[1]:
            return False
        # Comparación como STRING, que es lo que hace PostgREST con una columna `date` en ISO:
        # el orden lexicográfico y el cronológico coinciden.
        for c, op, v in self._cmp:
            actual = str(f.get(c))
            if op == "<" and not actual < v:
                return False
            if op == ">=" and actual < v:
                return False
            if op == "<=" and actual > v:
                return False
        return True

    def execute(self) -> _Resp:
        filas = self._a.catalogo.setdefault(self._t, [])
        self._a.consultas.append({"tabla": self._t, "modo": self._modo,
                                  "count": self._count, "rango": self._rango})
        if self._modo == "insert":
            nueva = {"id": str(uuid4()), "created_at": self._a.ahora, "updated_at": None,
                     **self._payload}
            filas.append(nueva)
            return _Resp([nueva])
        if self._modo == "update":
            tocadas = [f for f in filas if self._match(f)]
            self._a.escrituras.append((self._t, dict(self._payload)))
            for f in tocadas:
                f.update(self._payload)
            return _Resp(tocadas)
        hall = [f for f in filas if self._match(f)]
        if self._orden:
            col, desc = self._orden
            hall = sorted(hall, key=lambda f: str(f.get(col, "")), reverse=desc)
        total = len(hall)
        if self._rango:
            hall = hall[self._rango[0]:self._rango[1] + 1]
        if self._limit is not None:
            hall = hall[:self._limit]
        if self._single:
            return _Resp(hall[0] if hall else None)
        return _Resp(hall, count=total if self._count == "exact" else None)


class Almacen:
    def __init__(self, catalogo: Dict[str, List[dict]],
                 ahora: str = "2026-08-14T00:00:00+00:00") -> None:
        self.catalogo, self.ahora = catalogo, ahora
        self.consultas: List[dict] = []
        self.escrituras: List[tuple] = []

    def table(self, t: str) -> _Q:
        return _Q(self, t)


def _empleado(roles=("ANALISTA", "SOPORTE"), seniority="SEMI_SENIOR", categoria="3") -> dict:
    """El colaborador. DOS roles a propósito: con uno solo, la regla de `roles[0]` no se prueba."""
    return {"id": EMPLEADO, "empresa_id": EMPRESA, "area_id": AREA, "nombre": "Ana",
            "apellido": "Pérez", "email_corporativo": "ana@ejemplo.com",
            "roles": list(roles), "seniority": seniority, "categoria": categoria,
            "modalidad_trabajo": "presencial", "tipo_contrato": "RELACION DE DEPENDENCIA",
            "fecha_ingreso": "2020-01-01", "estado": "activo",
            "created_at": "2020-01-01T00:00:00+00:00"}


def _recat(fecha: str, rol=None, sen=None, cat=None, id_=None) -> dict:
    return {"id": id_ or str(uuid4()), "empresa_id": EMPRESA, "empleado_id": EMPLEADO,
            "fecha_efectiva": fecha, "rol_anterior": None, "rol_nuevo": rol,
            "seniority_anterior": None, "seniority_nueva": sen,
            "categoria_anterior": None, "categoria_nueva": cat,
            "motivo": "carga previa", "impacto_salarial": None, "registrado_por": None,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": None}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen({
        "recategorizaciones": [],
        "empleados": [_empleado()],
        "empresas": [{"id": EMPRESA, "nombre": "KARSTEC"},
                     {"id": OTRA_EMPRESA, "nombre": "DOSUBA"}],
        "users": [{"id": USUARIO, "nombre": "Sofía", "apellido": "Gómez"}],
        "areas": [{"id": AREA, "empresa_id": EMPRESA, "nombre": "Sistemas"}],
    })
    for mod in (repo_mod, row_mod, cadena_mod, write_mod, emp_write_mod, emp_lookup_mod):
        monkeypatch.setattr(mod, "supabase_admin", a, raising=False)
    return a


class _AuditoriaFalsa:
    """Guarda cada llamada ENTERA y cuenta: un payload al que le falte un campo se ve."""

    def __init__(self) -> None:
        self.eventos: List[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


@pytest.fixture
def auditoria() -> _AuditoriaFalsa:
    return _AuditoriaFalsa()


@pytest.fixture
def como(monkeypatch, almacen, auditoria):
    """Fábrica de clientes HTTP autenticados con el rol que se pida.

    🔴 Se falsea la RESOLUCIÓN DE IDENTIDAD del middleware (tiene sus propios tests y montarla
    de verdad exigiría un JWKS). NO se falsean los gates, ni el ruteo, ni Pydantic, ni el
    service, ni los repos, ni `EmpleadoService` — que corre REAL sobre el mismo almacén, que es
    lo único que permite afirmar qué quedó escrito en `empleados`.
    """
    def _fabrica(rol: str = "admin_rrhh", empresa_header: Optional[str] = EMPRESA):
        monkeypatch.setattr(auth_mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(auth_mod, "_verificar_token", lambda t, p: USUARIO)
        monkeypatch.setattr(auth_mod, "estado_usuario",
                            lambda uid: EstadoUsuario(rol=rol, activo=True, resuelto=True))
        monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
        monkeypatch.setattr(auth_mod, "sesion_expirada", lambda e: False)
        monkeypatch.setattr(auth_mod, "resolver_empresa_id", lambda h, p: empresa_header)
        # 🔴 El MISMO doble de auditoría entra también en `EmpleadoService`. Sin esto, el evento
        # `update_empleado` iría al `AuditService` real —que intenta salir a la red y se traga
        # el fallo por diseño— y el test de "se emiten DOS eventos" no tendría con qué contarlos.
        svc = RecategorizacionService(audit=auditoria,
                                      empleado_service=EmpleadoService(audit=auditoria))
        for dep in (_dep_lecturas, _dep_escrituras, _dep_ficha):
            app.dependency_overrides[dep] = lambda: svc
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test")

    yield _fabrica
    app.dependency_overrides.clear()


def _alta(fecha=None, rol=None, sen=None, cat=None, impacto=None) -> dict:
    body: dict = {"empleado_id": EMPLEADO, "motivo": "ascenso"}
    for k, v in (("fecha_efectiva", fecha), ("rol_nuevo", rol), ("seniority_nueva", sen),
                 ("categoria_nueva", cat), ("impacto_salarial", impacto)):
        if v is not None:
            body[k] = v
    return body


def _fila_empleado(almacen: Almacen) -> dict:
    return next(f for f in almacen.catalogo["empleados"] if f["id"] == EMPLEADO)


# ── 0. El almacén tiene que poder desmentir ───────────────────────────────────


class TestElAlmacenPuedeDesmentir:
    """Sin esto, los cuatro tests de las reglas 1 y 2 pasan en el vacío."""

    def test_lt_filtra_por_fecha(self, almacen) -> None:
        almacen.catalogo["recategorizaciones"] = [_recat("2026-08-01"), _recat("2026-09-01")]
        q = almacen.table("recategorizaciones").select("*").lt("fecha_efectiva", "2026-09-01")
        assert len(q.execute().data) == 1, "el almacén devuelve lo mismo sin importar la fecha"

    def test_order_desc_y_limit_devuelven_la_primera(self, almacen) -> None:
        almacen.catalogo["recategorizaciones"] = [_recat("2026-08-01"), _recat("2026-09-01")]
        q = (almacen.table("recategorizaciones").select("*")
             .order("fecha_efectiva", desc=True).limit(1))
        assert q.execute().data[0]["fecha_efectiva"] == "2026-09-01"

    def test_neq_excluye(self, almacen) -> None:
        f = _recat("2026-08-01")
        almacen.catalogo["recategorizaciones"] = [f]
        q = almacen.table("recategorizaciones").select("*").neq("id", f["id"])
        assert q.execute().data == []

    def test_el_empleado_arranca_con_dos_roles(self, almacen) -> None:
        assert len(_fila_empleado(almacen)["roles"]) == 2


# ── 1. REGLA 1 — de dónde salen los *_anterior ────────────────────────────────


class TestValoresAnteriores:
    async def test_sin_previa_salen_del_EMPLEADO(self, almacen, como) -> None:
        """Primera recategorización de la persona: el empleado ES el estado anterior."""
        async with como() as c:
            r = await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", sen="SENIOR", cat="4"))
        assert r.status_code == 201
        b = r.json()
        emp = _empleado()
        assert b["rol_anterior"] == emp["roles"][0]
        assert b["seniority_anterior"] == emp["seniority"]
        assert b["categoria_anterior"] == emp["categoria"]

    async def test_con_previa_salen_de_LA_PREVIA_y_no_del_empleado(self, almacen, como) -> None:
        """🔴 EL TEST DE LA REGLA 1. La previa dice `LIDER/SENIOR/4`; el empleado sigue en
        `ANALISTA/SEMI_SENIOR/3`. Los dos conjuntos son DISTINTOS a propósito: si los
        `*_anterior` salieran del empleado, esto rojea."""
        almacen.catalogo["recategorizaciones"] = [
            _recat("2026-08-01", rol="LIDER", sen="SENIOR", cat="4")]
        async with como() as c:
            b = (await c.post(BASE, json=_alta("2026-09-01", rol="MANAGER"))).json()
        assert b["rol_anterior"] == "LIDER"
        assert b["seniority_anterior"] == "SENIOR"
        assert b["categoria_anterior"] == "4"
        emp = _empleado()
        assert b["rol_anterior"] != emp["roles"][0], "salió del empleado, no de la previa"

    async def test_la_previa_es_la_ANTERIOR_a_la_fecha_no_la_ultima(self, almacen, como) -> None:
        """Cargando una del 15/8 con previas del 1/8 y del 1/9, la anterior es la del 1/8."""
        almacen.catalogo["recategorizaciones"] = [
            _recat("2026-08-01", rol="VIEJA"), _recat("2026-09-01", rol="NUEVA")]
        async with como() as c:
            b = (await c.post(BASE, json=_alta("2026-08-15", rol="X"))).json()
        assert b["rol_anterior"] == "VIEJA"

    async def test_cada_campo_cae_al_empleado_por_SEPARADO(self, almacen, como) -> None:
        """Una previa que solo cambió el rol NO borra el seniority anterior: ese sigue siendo
        el del empleado. Resolver los tres en bloque daría None acá."""
        almacen.catalogo["recategorizaciones"] = [_recat("2026-08-01", rol="LIDER")]
        async with como() as c:
            b = (await c.post(BASE, json=_alta("2026-09-01", sen="SENIOR"))).json()
        assert b["rol_anterior"] == "LIDER"
        assert b["seniority_anterior"] == _empleado()["seniority"]


# ── 2. REGLA 2 — cuándo se pisa al empleado ───────────────────────────────────


class TestEfectoSobreElEmpleado:
    async def test_fecha_POSTERIOR_se_registra_Y_actualiza(self, almacen, como) -> None:
        almacen.catalogo["recategorizaciones"] = [_recat("2026-08-01", rol="LIDER")]
        async with como() as c:
            r = await c.post(BASE, json=_alta("2026-09-01", rol="MANAGER", sen="SENIOR"))
        assert r.status_code == 201
        emp = _fila_empleado(almacen)
        assert emp["roles"][0] == "MANAGER"
        assert emp["seniority"] == "SENIOR"

    async def test_fecha_ANTERIOR_se_registra_y_NO_actualiza(self, almacen, como) -> None:
        """🔴 EL TEST DE LA REGLA 2. Ya existe una del 1/9; se carga una del 1/8. El histórico
        queda completo y el empleado NO se pisa con el valor viejo."""
        almacen.catalogo["recategorizaciones"] = [_recat("2026-09-01", rol="MANAGER")]
        antes = dict(_fila_empleado(almacen))
        async with como() as c:
            r = await c.post(BASE, json=_alta("2026-08-01", rol="RETROACTIVO", sen="TRAINEE"))
        assert r.status_code == 201, "la fila retroactiva TIENE que registrarse"
        assert len(almacen.catalogo["recategorizaciones"]) == 2
        emp = _fila_empleado(almacen)
        assert emp["roles"] == antes["roles"], "pisó al empleado con un valor viejo"
        assert emp["seniority"] == antes["seniority"]

    async def test_la_primera_de_todas_actualiza(self, almacen, como) -> None:
        """Sin ninguna previa no hay con qué compararse: es la más reciente por definición."""
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))
        assert _fila_empleado(almacen)["roles"][0] == "LIDER"

    async def test_el_EMPATE_de_fecha_actualiza(self, almacen, como) -> None:
        """`>=` y no `>`: corregir una del mismo día cargando otra encima tiene que aplicar."""
        almacen.catalogo["recategorizaciones"] = [_recat("2026-09-01", rol="PRIMERA")]
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="SEGUNDA"))
        assert _fila_empleado(almacen)["roles"][0] == "SEGUNDA"

    async def test_sin_fecha_toma_hoy_y_actualiza(self, almacen, como) -> None:
        """El default es hoy, que contra una previa de 2026-08-01 es posterior."""
        almacen.catalogo["recategorizaciones"] = [_recat("2026-08-01", rol="VIEJA")]
        async with como() as c:
            r = await c.post(BASE, json=_alta(rol="NUEVA"))
        assert r.status_code == 201 and r.json()["fecha_efectiva"]
        assert _fila_empleado(almacen)["roles"][0] == "NUEVA"


# ── 3. roles: reemplaza solo roles[0] ─────────────────────────────────────────


class TestRoles:
    async def test_conserva_los_roles_SECUNDARIOS(self, almacen, como) -> None:
        """🔴 `EmpleadoUpdate.roles` es reemplazo de lista completa: mandar `[rol_nuevo]`
        borraría `SOPORTE` sin ningún error. Con un solo rol esto no se puede probar."""
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))
        assert _fila_empleado(almacen)["roles"] == ["LIDER", "SOPORTE"]

    async def test_promover_un_secundario_no_lo_duplica(self, almacen, como) -> None:
        """Si el rol nuevo YA era secundario, pasa a principal y queda UNA sola vez.

        Parte de `["ANALISTA", "SOPORTE"]` y recategoriza a SOPORTE: queda `["SOPORTE"]`. El
        principal viejo (ANALISTA) se va —eso ES recategorizar— y SOPORTE no se duplica.
        ⚠️ `["SOPORTE", "ANALISTA"]` sería el resultado de conservar el principal viejo como
        secundario, que es el bug que este bloque cazó: la persona acumularía un rol por cada
        recategorización de su carrera.
        """
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="SOPORTE"))
        assert _fila_empleado(almacen)["roles"] == ["SOPORTE"]

    async def test_una_recategorizacion_sin_rol_no_toca_los_roles(self, almacen, como) -> None:
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", cat="4"))
        emp = _fila_empleado(almacen)
        assert emp["roles"] == ["ANALISTA", "SOPORTE"]
        assert emp["categoria"] == "4"


# ── 4. impacto_salarial y el gate de COSTOS ───────────────────────────────────


class TestImpactoSalarial:
    """🔴 HALLAZGO QUE ESTE BLOQUE DEJÓ ESCRITO: **hoy NO EXISTE un rol que pueda leer
    recategorizaciones y no costos.**

    `puede()` da lectura sobre TODA sección a `admin_rrhh` y a `gerencia_lectura`, y
    `mandos_medios` no llega ni a entrar al módulo (403 en el gate de sección). O sea que el
    gate de `impacto_salarial` **es correcto y hoy es inalcanzable por rol**. Es exactamente lo
    que `routers/costos.py:63-76` documenta para el historial salarial: "hoy no existe un rol
    con acceso a una sección y no a la otra, pero los roles cambian y este endpoint no se va a
    volver a mirar".

    ⚠️ POR ESO SE FALSEA `puede`, Y SOLO ESO. Si estos tests usaran `gerencia_lectura` para
    afirmar "no ve el monto", **pasarían al revés de lo que dicen** — o peor, alguien los
    "arreglaría" sacando el gate. Lo falseado es el oráculo de permisos (una función pura, con
    sus propios tests); el ruteo, el service, los repos y las cuatro superficies son los reales,
    así que si una se olvida de pasar `puede_ver_costos` esto rojea igual.
    """

    @pytest.fixture
    def sin_costos(self, monkeypatch):
        """Simula un rol con lectura en el módulo y NO en costos. Ver el docstring de arriba."""
        def _puede(rol, seccion, accion):
            if seccion is Seccion.COSTOS:
                return False
            return puede_real(rol, seccion, accion)
        monkeypatch.setattr(costos_dep_mod, "puede", _puede)

    async def test_admin_lo_ve(self, almacen, como) -> None:
        async with como("admin_rrhh") as c:
            b = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER",
                                               impacto="15000.50"))).json()
        assert b["impacto_salarial"] is not None

    async def test_gerencia_lectura_HOY_lo_ve(self, almacen, como) -> None:
        """No es un bug: `gerencia_lectura` tiene READ en todas las secciones, COSTOS incluida.
        Queda escrito para que el día que se agregue un rol sin costos alguien mire este test."""
        async with como("admin_rrhh") as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", impacto="15000.50"))
        async with como("gerencia_lectura") as c:
            fila = (await c.get(BASE)).json()["items"][0]
        assert fila["impacto_salarial"] is not None

    @pytest.mark.parametrize("superficie", ["listado", "detalle", "ficha"])
    async def test_sin_permiso_de_costos_NO_viaja_en_ninguna_superficie(
            self, almacen, como, sin_costos, superficie) -> None:
        """🔴 Las CUATRO superficies aplican el gate: tres acá y el export abajo. Una sola que
        se olvide devuelve el monto a quien no debe verlo, y nada más lo notaría."""
        async with como("admin_rrhh") as c:
            creada = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER",
                                                    impacto="15000.50"))).json()
        rutas = {"listado": BASE, "detalle": f"{BASE}/{creada['id']}",
                 "ficha": f"/api/empleados/{EMPLEADO}/recategorizaciones"}
        async with como("admin_rrhh") as c:
            body = (await c.get(rutas[superficie])).json()
        filas = body["items"] if superficie == "listado" else (
            body if isinstance(body, list) else [body])
        assert filas, "no había ninguna fila: el test quedaría vacuo"
        assert all(f["impacto_salarial"] is None for f in filas)

    async def test_el_campo_SIGUE_ESTANDO_en_la_respuesta(self, almacen, como,
                                                          sin_costos) -> None:
        """Se anula, no se quita: cambiar la forma de la respuesta según el rol rompe el
        contrato, y un campo ausente confirmaría que hay monto cargado."""
        async with como("admin_rrhh") as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", impacto="15000.50"))
            fila = (await c.get(BASE)).json()["items"][0]
        assert "impacto_salarial" in fila and fila["impacto_salarial"] is None

    async def test_el_export_CON_permiso_trae_la_columna(self, almacen, como) -> None:
        async with como("admin_rrhh") as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", impacto="15000.50"))
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        assert "Impacto salarial" in r.content.decode("utf-8", errors="replace")

    async def test_el_export_SIN_permiso_saca_la_COLUMNA_entera(self, almacen, como,
                                                                sin_costos) -> None:
        """En un Excel una columna vacía se lee como "no había monto", que es otra afirmación
        distinta de "no lo podés ver" — y un archivo se reenvía por mail."""
        async with como("admin_rrhh") as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", impacto="15000.50"))
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        assert "Impacto salarial" not in r.content.decode("utf-8", errors="replace")


# ── 5. Auditoría ──────────────────────────────────────────────────────────────


class TestAuditoria:
    async def test_el_alta_emite_su_evento_con_entidad_propia(self, almacen, como,
                                                              auditoria) -> None:
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))
        propios = [e for e in auditoria.eventos if e["entidad"] == "recategorizacion"]
        assert len(propios) == 1
        ev = propios[0]
        assert ev["evento"] == "alta_recategorizacion" and ev["accion"] == "INSERT"
        assert ev["usuario_id"] == USUARIO
        assert ev["datos_nuevos"]["rol_nuevo"] == "LIDER"

    async def test_la_empresa_del_evento_es_la_del_EMPLEADO_y_no_la_del_header(
            self, almacen, como, auditoria) -> None:
        """🔴 Vista vs Acción. El header dice otra empresa; el evento tiene que llevar la del
        empleado. Con un header igual a la del empleado, esto no podría fallar."""
        async with como(empresa_header=None) as c:
            r = await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))
        assert r.status_code == 201
        ev = next(e for e in auditoria.eventos if e["entidad"] == "recategorizacion")
        assert str(ev["empresa_id"]) == EMPRESA

    async def test_el_monto_NO_entra_en_el_evento_del_alta(self, almacen, como,
                                                           auditoria) -> None:
        """`/auditoria` la lee cualquiera con esa sección: un monto adentro saltearía COSTOS."""
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", impacto="15000.50"))
        ev = next(e for e in auditoria.eventos if e["entidad"] == "recategorizacion")
        assert "impacto_salarial" not in ev["datos_nuevos"]

    async def test_pisar_al_empleado_emite_TAMBIEN_el_evento_del_empleado(
            self, almacen, como, auditoria) -> None:
        """Son DOS eventos con entidades distintas: negocio y técnico. Que compartieran
        entidad es lo que los volvería ruido duplicado."""
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))
        entidades = [e["entidad"] for e in auditoria.eventos]
        assert "recategorizacion" in entidades and "empleado" in entidades

    async def test_la_retroactiva_NO_emite_el_evento_del_empleado(self, almacen, como,
                                                                  auditoria) -> None:
        """Contracara del anterior: si no se pisó al empleado, no hay cambio técnico que
        auditar. Un evento acá sería un cambio que no ocurrió."""
        almacen.catalogo["recategorizaciones"] = [_recat("2026-09-01", rol="MANAGER")]
        async with como() as c:
            await c.post(BASE, json=_alta("2026-08-01", rol="RETROACTIVO"))
        assert [e["entidad"] for e in auditoria.eventos] == ["recategorizacion"]

    async def test_la_edicion_emite_un_diff(self, almacen, como, auditoria) -> None:
        async with como() as c:
            creada = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))).json()
            await c.put(f"{BASE}/{creada['id']}", json={"motivo": "corregido"})
        ev = [e for e in auditoria.eventos if e["evento"] == "update_recategorizacion"][-1]
        assert ev["datos_anteriores"]["motivo"] == "ascenso"
        assert ev["datos_nuevos"]["motivo"] == "corregido"

    async def test_el_diff_NO_registra_los_nombres_de_join(self, almacen, como,
                                                           auditoria) -> None:
        """El "diff fantasma": los tres nombres son derivados y no pueden aparecer como cambios."""
        async with como() as c:
            creada = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))).json()
            await c.put(f"{BASE}/{creada['id']}", json={"motivo": "corregido"})
        ev = [e for e in auditoria.eventos if e["evento"] == "update_recategorizacion"][-1]
        for campo in ("empleado_nombre", "empresa_nombre", "registrado_por_nombre"):
            assert campo not in (ev["datos_anteriores"] or {})
            assert campo not in (ev["datos_nuevos"] or {})


# ── 6. Edición ────────────────────────────────────────────────────────────────


class TestEdicion:
    async def test_mover_la_fecha_recalcula_los_anteriores(self, almacen, como) -> None:
        """🔴 Es la razón por la que los `*_anterior` se recalculan SIEMPRE en la edición. La
        fila nace después de la del 1/9 (anterior = MANAGER) y se la mueve al 15/8, donde la
        previa pasa a ser la del 1/8 (anterior = LIDER)."""
        almacen.catalogo["recategorizaciones"] = [
            _recat("2026-08-01", rol="LIDER"), _recat("2026-09-01", rol="MANAGER")]
        async with como() as c:
            creada = (await c.post(BASE, json=_alta("2026-09-15", rol="X"))).json()
            assert creada["rol_anterior"] == "MANAGER"
            editada = (await c.put(f"{BASE}/{creada['id']}",
                                   json={"fecha_efectiva": "2026-08-15"})).json()
        assert editada["rol_anterior"] == "LIDER"

    async def test_no_se_toma_a_si_misma_de_previa(self, almacen, como) -> None:
        """Sin `excepto_id`, editar sin mover la fecha copiaría sus propios valores nuevos como
        anteriores.

        🔴 SE USA UNA FILA RETROACTIVA A PROPÓSITO. Con una que SÍ actualiza al empleado, el
        empleado termina con el mismo rol que la fila, así que "se tomó a sí misma" y "cayó al
        empleado" darían el MISMO resultado y el test no podría fallar. Con la retroactiva el
        empleado queda en ANALISTA y la fila dice RETRO: los dos caminos se distinguen.
        """
        almacen.catalogo["recategorizaciones"] = [_recat("2026-09-01", rol="MANAGER")]
        async with como() as c:
            creada = (await c.post(BASE, json=_alta("2026-08-01", rol="RETRO"))).json()
            editada = (await c.put(f"{BASE}/{creada['id']}", json={"motivo": "x"})).json()
        assert _fila_empleado(almacen)["roles"][0] == "ANALISTA", "la fila no era retroactiva"
        assert editada["rol_anterior"] != "RETRO", "se tomó a sí misma de previa"
        assert editada["rol_anterior"] == "ANALISTA"

    async def test_editar_la_mas_reciente_reaplica_al_empleado(self, almacen, como) -> None:
        """Sin `excepto_id` en `find_ultima`, la fila nunca sería más reciente que sí misma y
        editarla no actualizaría jamás al colaborador."""
        async with como() as c:
            creada = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))).json()
            await c.put(f"{BASE}/{creada['id']}", json={"rol_nuevo": "MANAGER"})
        assert _fila_empleado(almacen)["roles"][0] == "MANAGER"

    async def test_no_hay_DELETE(self, almacen, como) -> None:
        """Se puede editar, no borrar: borrar rompe la cadena de `*_anterior`."""
        async with como() as c:
            creada = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))).json()
            r = await c.delete(f"{BASE}/{creada['id']}")
        assert r.status_code == 405


# ── 7. Validación, barrera de empresa y rechazo ───────────────────────────────


class TestValidacionYBarrera:
    async def test_sin_ningun_valor_nuevo_da_422(self, almacen, como) -> None:
        """Espejo del CHECK de la migración 117: 422 legible en vez del 23514 crudo."""
        async with como() as c:
            r = await c.post(BASE, json={"empleado_id": EMPLEADO, "motivo": "nada"})
        assert r.status_code == 422
        assert r.json()["code"] == "RECATEGORIZACION_SIN_CAMBIOS"
        assert almacen.catalogo["recategorizaciones"] == []

    async def test_solo_categoria_SI_entra(self, almacen, como) -> None:
        """Lo que habilitó la migración 117, y es el caso más frecuente."""
        async with como() as c:
            r = await c.post(BASE, json=_alta("2026-09-01", cat="4"))
        assert r.status_code == 201 and r.json()["categoria_nueva"] == "4"

    async def test_un_empleado_de_OTRA_empresa_da_404(self, almacen, como) -> None:
        async with como(empresa_header=OTRA_EMPRESA) as c:
            r = await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))
        assert r.status_code == 404
        assert almacen.catalogo["recategorizaciones"] == []

    async def test_el_rechazo_es_UNO_SOLO(self, como) -> None:
        """Se comparan DOS rechazos REALES entre sí, no contra un literal escrito acá."""
        async with como() as c:
            a = await c.get(f"{BASE}/{INEXISTENTE}")
            b = await c.put(f"{BASE}/{OTRO_INEXISTENTE}", json={"motivo": "x"})
        assert a.status_code == b.status_code == 404
        assert a.json()["code"] == b.json()["code"] == "RECATEGORIZACION_NOT_FOUND"
        assert a.json()["message"] == b.json()["message"]

    async def test_un_id_mal_formado_da_422_sin_llegar_a_la_base(self, almacen, como) -> None:
        antes = len(almacen.consultas)
        async with como() as c:
            r = await c.get(f"{BASE}/no-soy-un-uuid")
        assert r.status_code == 422 and len(almacen.consultas) == antes

    async def test_la_empresa_persistida_sale_del_EMPLEADO(self, almacen, como) -> None:
        """Con el header en consolidado (None) la fila igual queda etiquetada con la empresa
        del empleado — si saliera del header, quedaría en NULL y rompería el NOT NULL."""
        async with como(empresa_header=None) as c:
            b = (await c.post(BASE, json=_alta("2026-09-01", rol="LIDER"))).json()
        assert b["empresa_id"] == EMPRESA


# ── 8. Permisos ───────────────────────────────────────────────────────────────


class TestPermisos:
    async def test_gerencia_lectura_lee(self, almacen, como) -> None:
        async with como("gerencia_lectura") as c:
            assert (await c.get(BASE)).status_code == 200

    @pytest.mark.parametrize("metodo,ruta", [
        ("post", BASE), ("put", f"{BASE}/{INEXISTENTE}"),
    ])
    async def test_gerencia_lectura_no_escribe(self, almacen, como, metodo, ruta) -> None:
        async with como("gerencia_lectura") as c:
            r = await getattr(c, metodo)(ruta, json=_alta("2026-09-01", rol="LIDER"))
        assert r.status_code == 403
        assert almacen.catalogo["recategorizaciones"] == []

    @pytest.mark.parametrize("ruta", [BASE, f"/api/empleados/{EMPLEADO}/recategorizaciones"])
    async def test_mandos_medios_no_llega_ni_a_leer(self, como, ruta) -> None:
        async with como("mandos_medios") as c:
            assert (await c.get(ruta)).status_code == 403

    async def test_rol_desconocido_es_fail_closed(self, como) -> None:
        async with como("rol_inventado") as c:
            assert (await c.get(BASE)).status_code == 403


# ── 9. Las dos vistas ─────────────────────────────────────────────────────────


class TestPlanillaPaginada:
    @pytest.fixture(autouse=True)
    def _llenar(self, almacen) -> None:
        almacen.catalogo["recategorizaciones"] = [
            _recat(f"2026-{1 + n // 28:02d}-{1 + n % 28:02d}", rol=f"R{n}")
            for n in range(TOTAL_PLANILLA)]

    def test_hay_mas_filas_que_una_pagina(self, almacen) -> None:
        assert len(almacen.catalogo["recategorizaciones"]) > 100

    async def test_la_pagina_por_defecto_trae_20_de_120(self, como) -> None:
        async with como() as c:
            b = (await c.get(BASE)).json()
        assert len(b["items"]) == 20 and b["total"] == TOTAL_PLANILLA
        assert b["total_pages"] == 6

    async def test_la_segunda_pagina_trae_otras_filas(self, como) -> None:
        async with como() as c:
            p1 = (await c.get(BASE, params={"page": 1})).json()["items"]
            p2 = (await c.get(BASE, params={"page": 2})).json()["items"]
        assert not ({i["id"] for i in p1} & {i["id"] for i in p2})

    async def test_page_size_mayor_a_100_lo_rechaza_el_router(self, como) -> None:
        async with como() as c:
            assert (await c.get(BASE, params={"page_size": 500})).status_code == 422

    async def test_ordena_por_fecha_efectiva_descendente(self, como) -> None:
        async with como() as c:
            items = (await c.get(BASE)).json()["items"]
        fechas = [i["fecha_efectiva"] for i in items]
        assert fechas == sorted(fechas, reverse=True)

    async def test_el_rango_filtra_por_fecha_EFECTIVA(self, como) -> None:
        async with como() as c:
            b = (await c.get(BASE, params={"fecha_desde": "2026-01-01",
                                           "fecha_hasta": "2026-01-31"})).json()
        assert 0 < b["total"] < TOTAL_PLANILLA
        assert all(i["fecha_efectiva"] <= "2026-01-31" for i in b["items"])


class TestHistorialDeLaFicha:
    async def test_devuelve_una_LISTA_PLANA_sin_paginar(self, almacen, como) -> None:
        almacen.catalogo["recategorizaciones"] = [
            _recat("2026-08-01", rol="A"), _recat("2026-09-01", rol="B")]
        async with como() as c:
            b = (await c.get(f"/api/empleados/{EMPLEADO}/recategorizaciones")).json()
        assert isinstance(b, list) and len(b) == 2

    async def test_del_mas_reciente_al_mas_viejo(self, almacen, como) -> None:
        almacen.catalogo["recategorizaciones"] = [
            _recat("2026-08-01", rol="VIEJA"), _recat("2026-09-01", rol="NUEVA")]
        async with como() as c:
            b = (await c.get(f"/api/empleados/{EMPLEADO}/recategorizaciones")).json()
        assert [f["rol_nuevo"] for f in b] == ["NUEVA", "VIEJA"]

    async def test_sin_historial_devuelve_vacio_y_no_es_un_error(self, como) -> None:
        async with como() as c:
            r = await c.get(f"/api/empleados/{EMPLEADO}/recategorizaciones")
        assert r.status_code == 200 and r.json() == []

    async def test_un_empleado_de_otra_empresa_da_404(self, como) -> None:
        async with como(empresa_header=OTRA_EMPRESA) as c:
            r = await c.get(f"/api/empleados/{EMPLEADO}/recategorizaciones")
        assert r.status_code == 404


# ── 10. Export ────────────────────────────────────────────────────────────────


class TestExport:
    async def test_devuelve_un_archivo(self, almacen, como) -> None:
        async with como() as c:
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        assert r.status_code == 200
        assert "recategorizaciones" in r.headers["content-disposition"]

    async def test_exportar_no_matchea_como_un_id(self, almacen, como) -> None:
        async with como() as c:
            assert (await c.get(f"{BASE}/exportar")).status_code == 200

    async def test_los_pares_antes_despues_salen_en_columnas_separadas(self, almacen,
                                                                       como) -> None:
        async with como() as c:
            await c.post(BASE, json=_alta("2026-09-01", rol="LIDER", sen="SENIOR", cat="4"))
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        lineas = r.content.decode("utf-8", errors="replace").splitlines()
        cab = next((ln for ln in lineas if "Motivo" in ln), "")
        assert cab, "no se encontró la fila de encabezados"
        for col in ("Rol anterior", "Rol nuevo", "Seniority anterior", "Seniority nueva",
                    "Categor", "Colaborador"):
            assert col in cab, f"falta la columna {col}"
