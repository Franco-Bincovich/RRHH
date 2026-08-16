"""
Agenda de eventos (migración 113): visibilidad, ventana de aviso, toggle de resuelta y CRUD.

## 🚨 LAS TRES PREGUNTAS PREVIAS, CONTESTADAS ANTES DE ESCRIBIR NADA

**1. ¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?**

  · **🔴 EL ALMACÉN TIENE EVENTOS DE DOS AUTORES DISTINTOS** (`YO` y `OTRO`), cada uno con su
    versión pública y su versión privada. Con un solo autor, "la privada ajena no se ve" no
    puede fallar: no existe ninguna fila que el filtro tuviera que sacar.
  · **🔴 `or_()` FILTRA DE VERDAD.** Es la mitad del archivo: el fake parsea la expresión que sale
    hacia PostgREST y la aplica. Un fake que aceptara `or_` y lo ignorara daría verde con el
    filtro de visibilidad BORRADO, que es exactamente el bug que la feature vino a cerrar.
  · **🔴 EL ALMACÉN DESORDENA LOS EMPATES ENTRE CONSULTAS** (`Almacen.rotacion`), igual que
    Postgres, que no garantiza NINGÚN orden sin `ORDER BY`. Sin eso, la lista de Python conserva
    el orden de inserción y **las dos páginas salen disjuntas aunque el `.order("id")` no esté**:
    el test de paginación pasaría con el desempate borrado. Se verifica en
    `TestElAlmacenPuedeDesmentir::test_los_empates_salen_en_distinto_orden`.
  · **🔴 EL ALMACÉN HACE CUMPLIR EL CHECK** `eventos_agenda_resuelta_coherente_check`. Sin él,
    "desresolver deja `resuelta_at` coherente" no podría fallar: cualquier combinación entraría.
  · **`lte` compara fechas de verdad**, así que el techo de la query recorta.
  · **El almacén modela los DEFAULTS de columna** (`resuelta=false`, `resuelta_at=null`): si el
    write path dejara de mandar un campo obligatorio, la fila no lo tiene y el schema no valida.
  · **La escritura se arma A PARTIR del payload recibido**, nunca devuelve un objeto prefabricado.
  · **Los eventos de la ventana de aviso tienen `dias_aviso` DISTINTOS entre sí** (0, 7 y 30).
    Con un solo valor, "la ventana la decide `dias_aviso`" y "la ventana es fija" darían igual.

**2. ¿El fake ES lo que estoy probando?** No. Lo falseado es el CLIENTE DE SUPABASE (un escalón
por debajo de los repos) y la resolución de identidad del middleware. Los repos, el service, los
filtros, `_eventos_pendientes`, los schemas, los gates y el ruteo son los REALES.

**3. ¿El test replica adentro lo que dice verificar?** El filtro de visibilidad NO se reimplementa
en el fake: el fake ejecuta la expresión `or_` que produce el código de producción, así que si esa
expresión está mal, el test lo ve. La ventana de aviso se compara contra fechas cargadas a mano,
no contra `en_ventana`.
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
import repositories._evento_agenda_row as row_mod  # noqa: E402
import repositories._evento_agenda_write_repo as write_mod  # noqa: E402
import repositories.configuracion_repo as config_mod  # noqa: E402
import repositories.evento_agenda_repo as repo_mod  # noqa: E402
from main import app  # noqa: E402
from routers.eventos_agenda import _service as _dep_lecturas  # noqa: E402
from routers.eventos_agenda_escrituras import _service as _dep_escrituras  # noqa: E402
from services.evento_agenda_service import EventoAgendaService  # noqa: E402
from utils.errors import AppError  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

BASE = "/api/eventos"
YO, OTRO = str(uuid4()), str(uuid4())
EMPRESA = str(uuid4())
OTRA_EMPRESA = str(uuid4())
# ⚠️ Los dos "inexistentes" NO comparten prefijo con ningún id del catálogo de abajo, y eso ya
# costó tres rojos: con `33333333-…` coincidían con `PUB_OTRO`, así que "borrar lo inexistente da
# 404" borraba un evento REAL y devolvía 204.
INEXISTENTE = "99999999-9999-9999-9999-999999999999"
OTRO_INEXISTENTE = "88888888-8888-8888-8888-888888888888"

# El "hoy" de los tests de ventana. Fijo, y entra por parámetro al service: leerlo de
# `date.today()` haría que el archivo cambiara de resultado según el día en que corre.
HOY = date(2026, 10, 15)

# Los cuatro eventos del catálogo de visibilidad. El nombre dice autor · visibilidad.
PUB_YO = "11111111-1111-1111-1111-111111111111"
PRIV_YO = "22222222-2222-2222-2222-222222222222"
PUB_OTRO = "33333333-3333-3333-3333-333333333333"
PRIV_OTRO = "44444444-4444-4444-4444-444444444444"


# ── El doble del cliente de Supabase ──────────────────────────────────────────


class _CheckViolado(Exception):
    """Lo que la base devolvería como 23514. Modela el CHECK de coherencia de `resuelta`."""


class _Resp:
    def __init__(self, data, count=None) -> None:
        self.data, self.count = data, count


def _igual(actual, esperado) -> bool:
    """Comparación como la de PostgREST: todo viaja como texto.

    Los booleanos se normalizan a minúscula porque `.eq("resuelta", False)` manda `False` desde
    Python y una expresión `or_` manda `true`/`false` en el formato de PostgREST. Sin esto, el
    filtro de visibilidad no matchearía NUNCA y la mitad de los tests pasarían por el motivo
    equivocado (todo vacío también hace que "la privada ajena no aparece" dé verde).
    """
    if isinstance(actual, bool) or str(esperado).lower() in ("true", "false"):
        return str(actual).lower() == str(esperado).lower()
    return str(actual) == str(esperado)


class _Q:
    """Query encadenable. `eq`/`is_`/`lte`/`in_`/`or_`/`order`/`range` filtran DE VERDAD."""

    def __init__(self, almacen: "Almacen", tabla: str) -> None:
        self._a, self._t = almacen, tabla
        self._eq: List[tuple] = []
        self._nulos: List[str] = []
        self._cmp: List[tuple] = []
        self._in: Optional[tuple] = None
        self._or: Optional[str] = None
        self._orden: list = []
        self._rango: Optional[tuple] = None
        self._limit: Optional[int] = None
        self._single = False
        self._modo, self._payload, self._count = "select", None, None

    def select(self, cols: str = "*", count=None) -> "_Q":
        self._count = count
        return self

    def eq(self, c, v) -> "_Q":
        self._eq.append((c, v))
        return self

    def is_(self, c, _v) -> "_Q":
        self._nulos.append(c)
        return self

    def lte(self, c, v) -> "_Q":
        self._cmp.append((c, "<=", str(v)))
        return self

    def gte(self, c, v) -> "_Q":
        self._cmp.append((c, ">=", str(v)))
        return self

    def in_(self, c, vals) -> "_Q":
        self._in = (c, [str(v) for v in vals])
        return self

    def or_(self, expr) -> "_Q":
        self._or = expr
        self._a.expresiones_or.append(expr)
        return self

    def order(self, c, **k) -> "_Q":
        self._orden.append((c, bool(k.get("desc"))))
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

    def insert(self, p) -> "_Q":
        self._modo, self._payload = "insert", p
        return self

    def update(self, p) -> "_Q":
        self._modo, self._payload = "update", p
        return self

    def delete(self) -> "_Q":
        self._modo = "delete"
        return self

    def _or_ok(self, f: dict) -> bool:
        """Ejecuta la expresión `or_` REAL que armó el código de producción.

        No reimplementa la regla: la interpreta. Si el filtro de visibilidad cambiara de forma
        (o desapareciera), acá se nota — que es justamente lo que un fake que ignora `or_` no
        puede hacer.
        """
        if self._or is None:
            return True
        for parte in self._or.split(","):
            col, op, val = parte.split(".", 2)
            assert op == "eq", f"el fake solo modela `eq` dentro de or_, llegó {op!r}"
            if _igual(f.get(col), val):
                return True
        return False

    def _match(self, f: dict) -> bool:
        if not all(_igual(f.get(c), v) for c, v in self._eq):
            return False
        if any(f.get(c) is not None for c in self._nulos):
            return False
        if self._in and str(f.get(self._in[0])) not in self._in[1]:
            return False
        # Comparación como STRING, que es lo que hace PostgREST con una columna `date` en ISO:
        # el orden lexicográfico y el cronológico coinciden.
        for c, op, v in self._cmp:
            actual = str(f.get(c))
            if op == "<=" and actual > v:
                return False
            if op == ">=" and actual < v:
                return False
        return self._or_ok(f)

    def execute(self) -> _Resp:
        filas = self._a.catalogo.setdefault(self._t, [])
        if self._modo == "insert":
            nueva = {"id": str(uuid4()), "created_at": self._a.ahora, "updated_at": None,
                     **self._a.defaults.get(self._t, {}), **self._payload}
            self._a.verificar_check(self._t, nueva)
            filas.append(nueva)
            return _Resp([nueva])
        if self._modo == "update":
            tocadas = [f for f in filas if self._match(f)]
            self._a.escrituras.append((self._t, dict(self._payload)))
            for f in tocadas:
                self._a.verificar_check(self._t, {**f, **self._payload})
                f.update(self._payload)
            return _Resp(tocadas)
        if self._modo == "delete":
            tocadas = [f for f in filas if self._match(f)]
            self._a.catalogo[self._t] = [f for f in filas if f not in tocadas]
            self._a.borrados.extend(tocadas)
            return _Resp(tocadas)
        hall = [f for f in filas if self._match(f)]
        hall = self._a.desordenar(hall)
        # Multi-clave con sort estable: de la última a la primera, como cualquier ORDER BY.
        for col, desc in reversed(self._orden):
            hall = sorted(hall, key=lambda f, c=col: str(f.get(c, "")), reverse=desc)
        total = len(hall)
        if self._rango:
            hall = hall[self._rango[0]:self._rango[1] + 1]
        if self._limit is not None:
            hall = hall[:self._limit]
        if self._single:
            return _Resp(hall[0] if hall else None)
        return _Resp(hall, count=total if self._count == "exact" else None)


class Almacen:
    """Catálogo en memoria con las tres cosas que la base hace y una lista de Python no.

    🔴 `desordenar` ES LA MÁS IMPORTANTE. Postgres no garantiza NINGÚN orden sin `ORDER BY`, y
    una lista de Python sí: conserva el de inserción, y encima `sorted` es estable, así que un
    `ORDER BY fecha` sobre filas empatadas devolvería siempre lo mismo. Con eso, sacar el
    `.order("id")` del repo no rompería NADA y el test de páginas disjuntas pasaría en el vacío.
    Rotar el conjunto una posición por consulta modela lo que la base no promete.
    """

    def __init__(self, catalogo: Dict[str, List[dict]], defaults: Optional[dict] = None,
                 ahora: str = "2026-10-15T00:00:00+00:00") -> None:
        self.catalogo, self.ahora = catalogo, ahora
        self.defaults = defaults or {}
        self.escrituras: List[tuple] = []
        self.borrados: List[dict] = []
        self.expresiones_or: List[str] = []
        self.rotacion = 0

    def table(self, t: str) -> _Q:
        return _Q(self, t)

    def desordenar(self, filas: list) -> list:
        self.rotacion += 1
        if len(filas) < 2:
            return filas
        k = self.rotacion % len(filas)
        return filas[k:] + filas[:k]

    def verificar_check(self, tabla: str, fila: dict) -> None:
        """`eventos_agenda_resuelta_coherente_check`: resuelta ⇒ resuelta_at NOT NULL."""
        if tabla != "eventos_agenda":
            return
        if fila.get("resuelta") and fila.get("resuelta_at") is None:
            raise _CheckViolado("eventos_agenda_resuelta_coherente_check")


def _evento(id_: str, autor: str, publica: bool, fecha: str, dias_aviso: int = 7,
            resuelta: bool = False, empresa: str = EMPRESA, nombre: str = "Feriado") -> dict:
    return {"id": id_, "empresa_id": empresa, "nombre": nombre, "fecha": fecha,
            "descripcion": None, "dias_aviso": dias_aviso, "es_publica": publica,
            "resuelta": resuelta, "resuelta_at": "2026-01-01T00:00:00+00:00" if resuelta else None,
            "resuelta_por": autor if resuelta else None, "created_by": autor,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": None}


# Los cuatro del catálogo de visibilidad, todos el MISMO día y en la misma empresa: así el único
# eje que puede explicar una diferencia entre ellos es el autor y la visibilidad.
_VISIBILIDAD = [
    _evento(PUB_YO, YO, True, "2026-10-20", nombre="Publico mio"),
    _evento(PRIV_YO, YO, False, "2026-10-20", nombre="Privado mio"),
    _evento(PUB_OTRO, OTRO, True, "2026-10-20", nombre="Publico ajeno"),
    _evento(PRIV_OTRO, OTRO, False, "2026-10-20", nombre="Privado ajeno"),
]

# Fila global de `parametros_empresa`: el default de `dias_aviso_evento` sale de acá.
_PARAMETROS_GLOBAL = {
    "empresa_id": None, "base_dias_habiles": 22, "corte_antiguedad_mes": 10,
    "periodo_vacacional_desde_mes": 10, "periodo_vacacional_hasta_mes": 4,
    "primer_anio_mes_corte": 7, "primer_anio_dias": 5, "vencimiento_anios": 4,
    "periodo_prueba_dias": 90, "dias_aviso_evento": 21,
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen(
        {
            "eventos_agenda": [dict(e) for e in _VISIBILIDAD],
            "empresas": [{"id": EMPRESA, "nombre": "KARSTEC"},
                         {"id": OTRA_EMPRESA, "nombre": "DOSUBA"}],
            "users": [{"id": YO, "nombre": "Sofía", "apellido": "Gómez"},
                      {"id": OTRO, "nombre": "Julián", "apellido": "Paz"}],
            "parametros_empresa": [dict(_PARAMETROS_GLOBAL)],
        },
        # Defaults de columna de la migración 113. Modelarlos es lo que hace que un write path
        # que deje de mandar un campo obligatorio se vea: la fila no lo tiene y el schema falla.
        defaults={"eventos_agenda": {"resuelta": False, "resuelta_at": None,
                                     "resuelta_por": None, "descripcion": None}},
    )
    for mod in (repo_mod, row_mod, write_mod, config_mod):
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
def svc(almacen, auditoria) -> EventoAgendaService:
    """El service REAL sobre el almacén falso. Para lo que necesita fijar `hoy`."""
    return EventoAgendaService(audit=auditoria)


@pytest.fixture
def como(monkeypatch, almacen, auditoria):
    """Fábrica de clientes HTTP autenticados con el rol y el usuario que se pidan.

    🔴 Se falsea la RESOLUCIÓN DE IDENTIDAD del middleware (tiene sus propios tests y montarla
    de verdad exigiría un JWKS). NO se falsean los gates, ni el ruteo, ni Pydantic, ni el
    service, ni los repos, ni los filtros.
    """
    def _fabrica(rol: str = "admin_rrhh", usuario: str = YO,
                 empresa_header: Optional[str] = EMPRESA):
        monkeypatch.setattr(auth_mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(auth_mod, "_verificar_token", lambda t, p: usuario)
        monkeypatch.setattr(auth_mod, "estado_usuario",
                            lambda uid: EstadoUsuario(rol=rol, activo=True, resuelto=True))
        monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
        monkeypatch.setattr(auth_mod, "sesion_expirada", lambda e: False)
        monkeypatch.setattr(auth_mod, "resolver_empresa_id", lambda h, p: empresa_header)
        servicio = EventoAgendaService(audit=auditoria)
        for dep in (_dep_lecturas, _dep_escrituras):
            app.dependency_overrides[dep] = lambda: servicio
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test")

    yield _fabrica
    app.dependency_overrides.clear()


def _nombres(items) -> set:
    return {i["nombre"] if isinstance(i, dict) else i.nombre for i in items}


# ── 0. El almacén tiene que poder desmentir ───────────────────────────────────


class TestElAlmacenPuedeDesmentir:
    """Sin esto, media docena de tests de abajo pasan en el vacío."""

    def test_or_filtra_de_verdad(self, almacen) -> None:
        q = (almacen.table("eventos_agenda").select("*")
             .or_(f"es_publica.eq.true,created_by.eq.{YO}"))
        assert _nombres(q.execute().data) == {"Publico mio", "Privado mio", "Publico ajeno"}, \
            "el almacén devuelve lo mismo con y sin or_: el filtro de visibilidad no se prueba"

    def test_los_empates_salen_en_distinto_orden(self, almacen) -> None:
        """🔴 LA GUARDA DEL TEST DE PÁGINAS. Los cuatro eventos comparten fecha; si el almacén
        devolviera siempre el mismo orden, sacar el `.order("id")` del repo no rompería nada."""
        def primero():
            return (almacen.table("eventos_agenda").select("*")
                    .order("fecha").execute().data[0]["id"])
        assert primero() != primero(), "el almacén no desordena los empates"

    def test_el_orden_completo_si_es_estable(self, almacen) -> None:
        """La contracara: CON las dos claves el resultado no depende del desorden. Sin este,
        el anterior podría estar rompiendo el orden en vez de modelar la falta de garantía."""
        def ids():
            return [f["id"] for f in (almacen.table("eventos_agenda").select("*")
                                      .order("fecha").order("id").execute().data)]
        assert ids() == ids()

    def test_lte_filtra_por_fecha(self, almacen) -> None:
        q = almacen.table("eventos_agenda").select("*").lte("fecha", "2026-10-19")
        assert q.execute().data == [], "el almacén ignora el techo de fecha"

    def test_el_check_de_resuelta_se_hace_cumplir(self, almacen) -> None:
        with pytest.raises(_CheckViolado):
            (almacen.table("eventos_agenda").update({"resuelta": True, "resuelta_at": None})
             .eq("id", PUB_YO).execute())

    def test_hay_eventos_de_dos_autores(self, almacen) -> None:
        autores = {f["created_by"] for f in almacen.catalogo["eventos_agenda"]}
        assert autores == {YO, OTRO}, "con un solo autor la privada ajena no existe"


# ── 1. Visibilidad: la privada ajena no aparece ───────────────────────────────


class TestVisibilidad:
    async def test_la_privada_ajena_NO_aparece_en_el_listado(self, almacen, como) -> None:
        """🔴 EL TEST QUE SOSTIENE LA SESIÓN. Si el filtro de visibilidad devolviera todo, acá
        aparecería "Privado ajeno" — que es un evento de otro usuario, en mi misma empresa."""
        async with como() as c:
            r = await c.get(BASE)
        assert r.status_code == 200
        assert _nombres(r.json()["items"]) == {"Publico mio", "Privado mio", "Publico ajeno"}

    async def test_la_privada_propia_SI_aparece(self, almacen, como) -> None:
        """La contracara: sin ella, un filtro que sacara TODAS las privadas también pasaría."""
        async with como() as c:
            r = await c.get(BASE)
        assert "Privado mio" in _nombres(r.json()["items"])

    async def test_el_otro_usuario_ve_la_suya_y_no_la_mia(self, almacen, como) -> None:
        """El eje es el AUTOR, no una lista fija: con el mismo catálogo, el conjunto cambia."""
        async with como(usuario=OTRO) as c:
            r = await c.get(BASE)
        assert _nombres(r.json()["items"]) == {"Publico mio", "Publico ajeno", "Privado ajeno"}

    async def test_gerencia_lectura_ve_las_privadas_de_todos(self, almacen, como) -> None:
        """Decisión de producto, la misma que en plantillas de onboarding: "privado" es
        privacidad entre pares de RRHH, no confidencialidad frente a la dirección."""
        async with como(rol="gerencia_lectura") as c:
            r = await c.get(BASE)
        assert len(r.json()["items"]) == 4

    async def test_el_detalle_de_la_privada_ajena_da_404(self, almacen, como) -> None:
        async with como() as c:
            r = await c.get(f"{BASE}/{PRIV_OTRO}")
        assert r.status_code == 404 and r.json()["code"] == "EVENTO_NOT_FOUND"

    async def test_el_rechazo_es_INDISTINGUIBLE_del_inexistente(self, almacen, como) -> None:
        """Un mensaje propio para "es privado de otro" confirmaría que existe y de quién es."""
        async with como() as c:
            privado = await c.get(f"{BASE}/{PRIV_OTRO}")
            inexistente = await c.get(f"{BASE}/{INEXISTENTE}")
        assert privado.status_code == inexistente.status_code
        assert privado.json() == inexistente.json()

    async def test_la_regla_NO_lleva_created_by_is_null(self, almacen, como) -> None:
        """`created_by` es NOT NULL y su FK no tiene ON DELETE: la fila huérfana no puede
        existir. La rama que sí lleva el precedente de onboarding sería código muerto acá."""
        async with como() as c:
            await c.get(BASE)
        assert almacen.expresiones_or, "no salió ninguna expresión de visibilidad hacia la base"
        assert all("created_by.is.null" not in e for e in almacen.expresiones_or)

    async def test_las_escrituras_sobre_la_privada_ajena_dan_404(self, almacen, como) -> None:
        """El gate corta ANTES de escribir en las cuatro superficies de escritura."""
        async with como() as c:
            respuestas = [
                await c.put(f"{BASE}/{PRIV_OTRO}", json={"nombre": "Pisado"}),
                await c.put(f"{BASE}/{PRIV_OTRO}/resuelta", json={"resuelta": True}),
                await c.delete(f"{BASE}/{PRIV_OTRO}"),
            ]
        assert [r.status_code for r in respuestas] == [404, 404, 404]
        assert almacen.escrituras == [] and almacen.borrados == []


# ── 2. La ventana de aviso ────────────────────────────────────────────────────


# Cinco eventos con `dias_aviso` DISTINTOS y fechas relativas a HOY. Los tres primeros tienen
# que salir y los dos últimos no, y cada uno por un motivo distinto.
VENCIDO = "aaaaaaaa-0000-0000-0000-000000000001"
HOY_MISMO = "aaaaaaaa-0000-0000-0000-000000000002"
DENTRO = "aaaaaaaa-0000-0000-0000-000000000003"
FUERA = "aaaaaaaa-0000-0000-0000-000000000004"
VENCIDO_RESUELTO = "aaaaaaaa-0000-0000-0000-000000000005"


def _iso(dias: int) -> str:
    return str(HOY + timedelta(days=dias))


@pytest.fixture
def agenda(almacen) -> Almacen:
    almacen.catalogo["eventos_agenda"] = [
        # Pasó hace dos semanas y NADIE lo resolvió. Tiene que seguir apareciendo.
        _evento(VENCIDO, YO, True, _iso(-14), dias_aviso=7, nombre="Vencido sin resolver"),
        # Es hoy, y avisa el mismo día: el borde exacto de `fecha - dias_aviso <= hoy`.
        _evento(HOY_MISMO, YO, True, _iso(0), dias_aviso=0, nombre="Es hoy"),
        # Falta un mes y avisa con 30 días: entró en su ventana justo hoy.
        _evento(DENTRO, YO, True, _iso(30), dias_aviso=30, nombre="Entro en ventana"),
        # Falta un mes y avisa con 7: todavía no.
        _evento(FUERA, YO, True, _iso(30), dias_aviso=7, nombre="Todavia no"),
        # Vencido pero RESUELTO: lo saca el otro filtro, no la ventana.
        _evento(VENCIDO_RESUELTO, YO, True, _iso(-14), dias_aviso=7, resuelta=True,
                nombre="Vencido resuelto"),
    ]
    return almacen


class TestVentanaDeAviso:
    def _pendientes(self, svc, usuario=YO, rol="admin_rrhh"):
        return _nombres(svc.pendientes(EMPRESA, usuario, rol, HOY))

    def test_el_vencido_sin_resolver_SIGUE_apareciendo(self, agenda, svc) -> None:
        """🔴 EL OTRO TEST QUE SOSTIENE LA SESIÓN. Un evento no desaparece por vencer: desaparece
        cuando alguien lo marca. Si la query llevara `fecha >= hoy`, éste se caería — y es
        justamente el que nadie atendió."""
        assert "Vencido sin resolver" in self._pendientes(svc)

    def test_el_de_hoy_con_aviso_CERO_entra(self, agenda, svc) -> None:
        """El borde exacto: `fecha - 0 <= hoy` es una igualdad. Un `<` en vez de `<=` lo pierde."""
        assert "Es hoy" in self._pendientes(svc)

    def test_el_que_ENTRA_HOY_en_su_ventana_aparece(self, agenda, svc) -> None:
        """+30 días con 30 de aviso: el otro borde de la misma igualdad, del lado del futuro."""
        assert "Entro en ventana" in self._pendientes(svc)

    def test_el_que_TODAVIA_no_entro_no_aparece(self, agenda, svc) -> None:
        """Misma fecha que el anterior y distinto `dias_aviso`: lo único que los separa es la
        ventana. Si el filtro fuera por fecha a secas, los dos entrarían o ninguno."""
        assert "Todavia no" not in self._pendientes(svc)

    def test_el_vencido_RESUELTO_no_aparece(self, agenda, svc) -> None:
        assert "Vencido resuelto" not in self._pendientes(svc)

    def test_el_conjunto_completo(self, agenda, svc) -> None:
        assert self._pendientes(svc) == {"Vencido sin resolver", "Es hoy", "Entro en ventana"}

    def test_la_visibilidad_TAMBIEN_aplica_en_los_pendientes(self, agenda, svc) -> None:
        """El dashboard no es una puerta de atrás: la privada ajena tampoco entra acá."""
        agenda.catalogo["eventos_agenda"].append(
            _evento("bbbbbbbb-0000-0000-0000-000000000001", OTRO, False, _iso(0),
                    dias_aviso=0, nombre="Privado ajeno de hoy"))
        assert "Privado ajeno de hoy" not in self._pendientes(svc)

    def test_el_techo_de_la_query_recorta(self, agenda, svc) -> None:
        """Un evento a 400 días no puede estar en ventana ni con el `dias_aviso` máximo que la
        base acepta (365), así que la query ni lo trae. El recorte es exacto, no una heurística."""
        agenda.catalogo["eventos_agenda"].append(
            _evento("bbbbbbbb-0000-0000-0000-000000000002", YO, True, _iso(400),
                    dias_aviso=365, nombre="Lejisimo"))
        assert "Lejisimo" not in self._pendientes(svc)

    def test_el_techo_deja_pasar_al_limite(self, agenda, svc) -> None:
        """Y la contracara: a 365 días con 365 de aviso SÍ entra. Sin este test, un techo
        demasiado corto (o un `<` en vez de `<=`) pasaría inadvertido."""
        agenda.catalogo["eventos_agenda"].append(
            _evento("bbbbbbbb-0000-0000-0000-000000000003", YO, True, _iso(365),
                    dias_aviso=365, nombre="El limite"))
        assert "El limite" in self._pendientes(svc)

    async def test_pendientes_no_matchea_como_id(self, agenda, como) -> None:
        """`/pendientes` está declarado ANTES de `/{id}`: al revés matchearía como el path param
        `id: UUID` y el pedido moriría en un 422 antes de llegar al handler."""
        async with como() as c:
            r = await c.get(f"{BASE}/pendientes")
        assert r.status_code == 200 and isinstance(r.json(), list)


# ── 3. El toggle de resueltos en el listado ───────────────────────────────────


class TestToggleDeResueltos:
    @pytest.fixture(autouse=True)
    def _mixto(self, almacen):
        almacen.catalogo["eventos_agenda"] = [
            _evento(PUB_YO, YO, True, "2026-10-20", nombre="Pendiente"),
            _evento(PRIV_YO, YO, True, "2026-10-21", resuelta=True, nombre="Resuelto"),
        ]

    async def test_por_defecto_el_resuelto_no_aparece(self, como) -> None:
        async with como() as c:
            r = await c.get(BASE)
        assert _nombres(r.json()["items"]) == {"Pendiente"}

    async def test_con_el_toggle_aparece(self, como) -> None:
        async with como() as c:
            r = await c.get(BASE, params={"incluir_resueltas": "true"})
        assert _nombres(r.json()["items"]) == {"Pendiente", "Resuelto"}

    async def test_el_total_tambien_cambia(self, como) -> None:
        """El total sale de `count="exact"` DENTRO de la misma query. Si el filtro se aplicara
        en Python, la barra de paginación diría 2 mientras la tabla muestra 1."""
        async with como() as c:
            sin = await c.get(BASE)
            con = await c.get(BASE, params={"incluir_resueltas": "true"})
        assert (sin.json()["total"], con.json()["total"]) == (1, 2)


# ── 4. Resolver y desresolver ─────────────────────────────────────────────────


class TestResolver:
    async def test_resolver_deja_las_tres_columnas_coherentes(self, almacen, como) -> None:
        async with como() as c:
            r = await c.put(f"{BASE}/{PUB_YO}/resuelta", json={"resuelta": True})
        cuerpo = r.json()
        assert r.status_code == 200 and cuerpo["resuelta"] is True
        assert cuerpo["resuelta_at"] is not None, "el CHECK exige la fecha"
        assert cuerpo["resuelta_por"] == YO

    async def test_desresolver_LIMPIA_la_fecha_y_el_autor(self, almacen, como) -> None:
        """🔴 No alcanza con bajar el flag. Dejar los valores viejos no rompe el CHECK, y el
        evento volvería a los pendientes diciendo que lo resolvió alguien el martes pasado."""
        async with como() as c:
            await c.put(f"{BASE}/{PUB_YO}/resuelta", json={"resuelta": True})
            r = await c.put(f"{BASE}/{PUB_YO}/resuelta", json={"resuelta": False})
        cuerpo = r.json()
        assert cuerpo["resuelta"] is False
        assert cuerpo["resuelta_at"] is None and cuerpo["resuelta_por"] is None

    async def test_el_resuelto_sale_de_los_pendientes_y_vuelve(self, almacen, como) -> None:
        """El ciclo completo por HTTP: resolver lo saca del panel y desresolver lo devuelve.

        ⚠️ Acá el evento se siembra relativo a `date.today()` REAL y no a `HOY`, porque el
        endpoint no recibe la fecha: la toma del día. Los tests de la VENTANA en sí van por el
        service con `hoy` fijo — este mira el ciclo resolver/desresolver, no el cálculo.
        """
        almacen.catalogo["eventos_agenda"] = [
            _evento(VENCIDO, YO, True, str(date.today() - timedelta(days=14)),
                    dias_aviso=7, nombre="Vencido sin resolver"),
        ]
        async with como() as c:
            antes = await c.get(f"{BASE}/pendientes")
            await c.put(f"{BASE}/{VENCIDO}/resuelta", json={"resuelta": True})
            durante = await c.get(f"{BASE}/pendientes")
            await c.put(f"{BASE}/{VENCIDO}/resuelta", json={"resuelta": False})
            despues = await c.get(f"{BASE}/pendientes")
        assert "Vencido sin resolver" in _nombres(antes.json())
        assert "Vencido sin resolver" not in _nombres(durante.json())
        assert "Vencido sin resolver" in _nombres(despues.json())

    async def test_el_PUT_generico_no_puede_tocar_resuelta(self, almacen, como) -> None:
        """`resuelta` no está en `EventoUpdate` y además el write path la descarta: por esa vía
        se podría dejar `resuelta=true` sin fecha, que es un 500 crudo de la base."""
        async with como() as c:
            r = await c.put(f"{BASE}/{PUB_YO}",
                            json={"nombre": "N", "resuelta": True, "resuelta_at": None})
        assert r.status_code == 200 and r.json()["resuelta"] is False


# ── 5. Paginación ─────────────────────────────────────────────────────────────


TOTAL_AGENDA = 40


class TestPaginacion:
    @pytest.fixture(autouse=True)
    def _muchos(self, almacen):
        # 🔴 TODOS EL MISMO DÍA. Los empates son la norma en una agenda (un feriado largo carga
        # varios el mismo día), y son el único escenario en el que el desempate por `id` importa.
        almacen.catalogo["eventos_agenda"] = [
            _evento(f"{i:08d}-0000-0000-0000-000000000000", YO, True, "2026-11-01",
                    nombre=f"Evento {i:02d}")
            for i in range(TOTAL_AGENDA)
        ]

    async def test_la_pagina_por_defecto_trae_20_de_40(self, como) -> None:
        async with como() as c:
            r = await c.get(BASE)
        cuerpo = r.json()
        assert len(cuerpo["items"]) == 20
        assert (cuerpo["total"], cuerpo["total_pages"]) == (TOTAL_AGENDA, 2)

    async def test_las_dos_paginas_son_DISJUNTAS_y_cubren_todo(self, como) -> None:
        """🔴 EL TEST DEL `.order("id")`. Con los 40 eventos empatados en fecha y un almacén que
        desordena los empates entre consultas, sin el desempate las dos páginas comparten filas
        y dejan otras afuera — el usuario ve una repetida y nunca ve otra."""
        async with como() as c:
            p1 = await c.get(BASE, params={"page": 1})
            p2 = await c.get(BASE, params={"page": 2})
        n1, n2 = _nombres(p1.json()["items"]), _nombres(p2.json()["items"])
        assert not (n1 & n2), "las dos páginas comparten eventos: falta el desempate del ORDER BY"
        assert len(n1 | n2) == TOTAL_AGENDA, "entre las dos páginas falta algún evento"

    async def test_la_misma_pagina_pedida_dos_veces_da_lo_mismo(self, como) -> None:
        """La otra cara del mismo problema: sin orden total, recargar la pantalla cambia lo que
        se ve sin que nadie haya tocado nada."""
        async with como() as c:
            a = await c.get(BASE, params={"page": 1})
            b = await c.get(BASE, params={"page": 1})
        assert _nombres(a.json()["items"]) == _nombres(b.json()["items"])

    async def test_page_size_mayor_a_100_lo_rechaza_el_router(self, como) -> None:
        """Sin techo, el listado sería un export encubierto — y este módulo no tiene export."""
        async with como() as c:
            r = await c.get(BASE, params={"page_size": 5000})
        assert r.status_code == 422

    async def test_la_agenda_vacia_no_rompe(self, almacen, como) -> None:
        """No es un borde inventado: es el estado de producción hasta que RRHH cargue el primero.

        Además es el único camino que ejercita el early-return de `build([])` — el mapper corta
        antes de los lookups por lote porque `.in_("id", [])` no es un filtro válido.
        """
        almacen.catalogo["eventos_agenda"] = []
        async with como() as c:
            r = await c.get(BASE)
        assert r.status_code == 200
        assert r.json()["items"] == [] and r.json()["total"] == 0

    async def test_ordena_por_fecha_ASCENDENTE(self, almacen, como) -> None:
        """Lo primero que se lee es lo más urgente, incluidos los vencidos sin resolver."""
        almacen.catalogo["eventos_agenda"] = [
            _evento(PUB_YO, YO, True, "2026-12-01", nombre="Despues"),
            _evento(PRIV_YO, YO, True, "2026-10-01", nombre="Antes"),
        ]
        async with como() as c:
            r = await c.get(BASE)
        assert [i["nombre"] for i in r.json()["items"]] == ["Antes", "Despues"]


# ── 6. Barrera de empresa ─────────────────────────────────────────────────────


class TestBarreraDeEmpresa:
    @pytest.fixture(autouse=True)
    def _dos_empresas(self, almacen):
        almacen.catalogo["eventos_agenda"] = [
            _evento(PUB_YO, YO, True, "2026-10-20", nombre="De la mia"),
            _evento(PUB_OTRO, YO, True, "2026-10-20", empresa=OTRA_EMPRESA, nombre="De la otra"),
        ]

    async def test_el_listado_no_trae_la_de_otra_empresa(self, como) -> None:
        async with como() as c:
            r = await c.get(BASE)
        assert _nombres(r.json()["items"]) == {"De la mia"}

    async def test_ser_el_autor_no_abre_la_puerta_de_otra_empresa(self, como) -> None:
        """Los dos eventos son MÍOS y los dos son públicos: lo único que los separa es la
        empresa. Los dos ejes se componen por intersección, no se reemplazan."""
        async with como() as c:
            r = await c.get(f"{BASE}/{PUB_OTRO}")
        assert r.status_code == 404

    async def test_el_404_de_otra_empresa_es_el_mismo_que_el_inexistente(self, como) -> None:
        async with como() as c:
            ajeno = await c.get(f"{BASE}/{PUB_OTRO}")
            inexistente = await c.get(f"{BASE}/{OTRO_INEXISTENTE}")
        assert ajeno.json() == inexistente.json()

    async def test_el_consolidado_no_afloja_la_visibilidad(self, almacen, como) -> None:
        """`empresa_id=None` no restringe por empresa — pero el autor sigue filtrando. Es donde
        más fácil se colaría un evento privado ajeno."""
        almacen.catalogo["eventos_agenda"].append(
            _evento(PRIV_OTRO, OTRO, False, "2026-10-20", empresa=OTRA_EMPRESA,
                    nombre="Privado ajeno de la otra"))
        async with como(empresa_header=None) as c:
            r = await c.get(BASE)
        nombres = _nombres(r.json()["items"])
        assert nombres == {"De la mia", "De la otra"}

    async def test_crear_sin_empresa_activa_pide_elegirla(self, almacen, como) -> None:
        """El alta usa `require_empresa_id`: en consolidado no hay a qué empresa cargarlo, y
        adivinar sería escribirle a una sociedad que nadie eligió."""
        async with como(empresa_header=None) as c:
            r = await c.post(BASE, json={"nombre": "X", "fecha": "2026-12-01"})
        assert r.status_code == 400 and r.json()["code"] == "EMPRESA_ID_REQUIRED"

    async def test_la_empresa_persistida_es_la_del_header(self, almacen, como) -> None:
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "Nuevo", "fecha": "2026-12-01"})
        assert r.json()["empresa_id"] == EMPRESA


# ── 7. El alta: autor, default de días de aviso y visibilidad ─────────────────


class TestAlta:
    async def test_el_autor_sale_del_TOKEN_y_no_del_body(self, almacen, como) -> None:
        async with como(usuario=OTRO) as c:
            r = await c.post(BASE, json={"nombre": "Mío", "fecha": "2026-12-01",
                                         "created_by": YO})
        assert r.json()["created_by"] == OTRO

    async def test_sin_dias_aviso_toma_el_de_CONFIGURACION(self, almacen, como) -> None:
        """🔑 21 es el valor sembrado en `parametros_empresa`, NO el 7 del default de la columna
        ni ninguna constante del código. Si el service dejara de consultar la configuración, la
        fila saldría con 7 y este test lo vería."""
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "Sin aviso", "fecha": "2026-12-01"})
        assert r.json()["dias_aviso"] == 21

    async def test_con_dias_aviso_propio_lo_respeta(self, almacen, como) -> None:
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "Con aviso", "fecha": "2026-12-01",
                                         "dias_aviso": 3})
        assert r.json()["dias_aviso"] == 3

    async def test_dias_aviso_CERO_no_es_lo_mismo_que_ausente(self, almacen, como) -> None:
        """0 es un valor legítimo ("avisar el mismo día"). Un `or` en vez de un `is not None`
        lo confundiría con "no vino" y lo pisaría con el default de la empresa."""
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "Mismo día", "fecha": "2026-12-01",
                                         "dias_aviso": 0})
        assert r.json()["dias_aviso"] == 0

    async def test_nace_publico_por_defecto(self, almacen, como) -> None:
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "Del equipo", "fecha": "2026-12-01"})
        assert r.json()["es_publica"] is True

    async def test_nace_sin_resolver(self, almacen, como) -> None:
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "Nuevo", "fecha": "2026-12-01"})
        assert r.json()["resuelta"] is False and r.json()["resuelta_at"] is None

    async def test_dias_aviso_fuera_de_rango_da_422(self, almacen, como) -> None:
        """El CHECK de la base es la red; el 422 de Pydantic es el mensaje."""
        async with como() as c:
            r = await c.post(BASE, json={"nombre": "X", "fecha": "2026-12-01",
                                         "dias_aviso": 400})
        assert r.status_code == 422

    async def test_sin_nombre_da_422(self, almacen, como) -> None:
        async with como() as c:
            r = await c.post(BASE, json={"fecha": "2026-12-01"})
        assert r.status_code == 422


# ── 8. Edición y baja ─────────────────────────────────────────────────────────


class TestEdicionYBaja:
    async def test_editar_cambia_solo_lo_que_viaja(self, almacen, como) -> None:
        async with como() as c:
            r = await c.put(f"{BASE}/{PUB_YO}", json={"nombre": "Renombrado"})
        cuerpo = r.json()
        assert cuerpo["nombre"] == "Renombrado"
        assert cuerpo["fecha"] == "2026-10-20" and cuerpo["dias_aviso"] == 7

    async def test_se_puede_volver_privado_un_evento_propio(self, almacen, como) -> None:
        async with como() as c:
            r = await c.put(f"{BASE}/{PUB_YO}", json={"es_publica": False})
        assert r.json()["es_publica"] is False

    async def test_borrar_saca_la_fila_de_verdad(self, almacen, como) -> None:
        """🔴 Baja FÍSICA, al revés que clientes. Si fuera lógica, la fila seguiría en el
        almacén y el listado la traería con el toggle de resueltos."""
        async with como() as c:
            r = await c.delete(f"{BASE}/{PUB_YO}")
            quedan = await c.get(BASE, params={"incluir_resueltas": "true"})
        assert r.status_code == 204
        assert "Publico mio" not in _nombres(quedan.json()["items"])
        assert [f["id"] for f in almacen.borrados] == [PUB_YO]

    async def test_borrar_lo_inexistente_da_404_sin_tocar_nada(self, almacen, como) -> None:
        async with como() as c:
            r = await c.delete(f"{BASE}/{INEXISTENTE}")
        assert r.status_code == 404 and almacen.borrados == []

    async def test_un_id_mal_formado_da_422_sin_llegar_a_la_base(self, almacen, como) -> None:
        async with como() as c:
            r = await c.get(f"{BASE}/no-es-un-uuid")
        assert r.status_code == 422


# ── 9. Auditoría ──────────────────────────────────────────────────────────────


class TestAuditoria:
    def _eventos(self, auditoria, nombre: str) -> list:
        return [e for e in auditoria.eventos if e["evento"] == nombre]

    async def test_el_alta_emite_su_evento_con_entidad_propia(self, almacen, como,
                                                              auditoria) -> None:
        async with como() as c:
            await c.post(BASE, json={"nombre": "Auditado", "fecha": "2026-12-01"})
        evento = self._eventos(auditoria, "alta_evento")[0]
        assert evento["entidad"] == "evento_agenda" and evento["accion"] == "INSERT"
        assert evento["datos_nuevos"]["nombre"] == "Auditado"
        assert evento["usuario_id"] == YO

    async def test_la_empresa_del_evento_sale_de_la_FILA(self, almacen, como,
                                                         auditoria) -> None:
        """No del header: es la única fuente que no puede mentir, y con NULL el evento se caería
        del filtro por empresa de /auditoria."""
        async with como() as c:
            await c.post(BASE, json={"nombre": "Auditado", "fecha": "2026-12-01"})
        assert str(self._eventos(auditoria, "alta_evento")[0]["empresa_id"]) == EMPRESA

    async def test_la_edicion_emite_un_diff(self, almacen, como, auditoria) -> None:
        async with como() as c:
            await c.put(f"{BASE}/{PUB_YO}", json={"nombre": "Renombrado"})
        evento = self._eventos(auditoria, "update_evento")[0]
        assert evento["datos_anteriores"]["nombre"] == "Publico mio"
        assert evento["datos_nuevos"]["nombre"] == "Renombrado"

    async def test_el_diff_NO_registra_los_nombres_de_join(self, almacen, como,
                                                           auditoria) -> None:
        """El "diff fantasma": los derivados salen resueltos en la lectura y en null en la
        escritura, así que sin excluirlos cada edición registraría un cambio que no ocurrió."""
        async with como() as c:
            await c.put(f"{BASE}/{PUB_YO}", json={"nombre": "Renombrado"})
        evento = self._eventos(auditoria, "update_evento")[0]
        derivados = {"empresa_nombre", "created_by_nombre", "resuelta_por_nombre"}
        assert not (set(evento["datos_anteriores"]) & derivados)
        assert not (set(evento["datos_nuevos"]) & derivados)

    async def test_la_edicion_que_no_cambia_nada_registra_un_diff_vacio(self, almacen, como,
                                                                        auditoria) -> None:
        """No es un caso de borde inventado: es lo que pasa al abrir el modal y guardar sin
        tocar. El evento se emite igual —alguien apretó Guardar— pero no inventa cambios."""
        async with como() as c:
            await c.put(f"{BASE}/{PUB_YO}", json={"nombre": "Publico mio"})
        evento = self._eventos(auditoria, "update_evento")[0]
        assert evento["datos_anteriores"] == {} and evento["datos_nuevos"] == {}

    async def test_resolver_emite_un_evento_PROPIO(self, almacen, como, auditoria) -> None:
        """No un `update_evento`: la pregunta de negocio es quién lo dio por atendido, y tiene
        que poder filtrarse por `evento` sin leer el JSONB de cada UPDATE."""
        async with como() as c:
            await c.put(f"{BASE}/{PUB_YO}/resuelta", json={"resuelta": True})
        evento = self._eventos(auditoria, "resolucion_evento")[0]
        assert evento["datos_nuevos"]["resuelta"] is True
        assert self._eventos(auditoria, "update_evento") == []

    async def test_desresolver_TAMBIEN_queda_registrado(self, almacen, como,
                                                        auditoria) -> None:
        """Sin esto, un evento resuelto por error y revertido dejaría en el log solo la mitad
        que confunde."""
        async with como() as c:
            await c.put(f"{BASE}/{PUB_YO}/resuelta", json={"resuelta": True})
            await c.put(f"{BASE}/{PUB_YO}/resuelta", json={"resuelta": False})
        estados = [e["datos_nuevos"]["resuelta"] for e in
                   self._eventos(auditoria, "resolucion_evento")]
        assert estados == [True, False]

    async def test_la_baja_guarda_el_SNAPSHOT_previo(self, almacen, como, auditoria) -> None:
        """Se arma ANTES de borrar: después no hay fila que fotografiar, y un evento privado
        creado y borrado no dejaría rastro en ninguna pantalla."""
        async with como() as c:
            await c.delete(f"{BASE}/{PRIV_YO}")
        evento = self._eventos(auditoria, "baja_evento")[0]
        assert evento["accion"] == "DELETE"
        assert evento["datos_anteriores"]["nombre"] == "Privado mio"
        assert evento["datos_anteriores"]["es_publica"] is False
        assert evento["datos_nuevos"] is None

    async def test_una_baja_que_falla_el_gate_NO_audita(self, almacen, como,
                                                        auditoria) -> None:
        async with como() as c:
            await c.delete(f"{BASE}/{PRIV_OTRO}")
        assert auditoria.eventos == []


# ── 10. Permisos ──────────────────────────────────────────────────────────────


_ESCRITURAS = [
    ("post", BASE, {"nombre": "X", "fecha": "2026-12-01"}),
    ("put", f"{BASE}/{PUB_YO}", {"nombre": "X"}),
    ("put", f"{BASE}/{PUB_YO}/resuelta", {"resuelta": True}),
    ("delete", f"{BASE}/{PUB_YO}", None),
]


class TestPermisos:
    async def test_gerencia_lectura_lee(self, almacen, como) -> None:
        async with como(rol="gerencia_lectura") as c:
            assert (await c.get(BASE)).status_code == 200

    @pytest.mark.parametrize("metodo,ruta,cuerpo", _ESCRITURAS,
                             ids=["crear", "editar", "resolver", "borrar"])
    async def test_gerencia_lectura_no_escribe(self, almacen, como, metodo, ruta,
                                               cuerpo) -> None:
        async with como(rol="gerencia_lectura") as c:
            kw = {"json": cuerpo} if cuerpo is not None else {}
            r = await getattr(c, metodo)(ruta, **kw)
        assert r.status_code == 403

    @pytest.mark.parametrize("ruta", [BASE, f"{BASE}/pendientes", f"{BASE}/{PUB_YO}"])
    async def test_mandos_medios_no_llega_ni_a_leer(self, almacen, como, ruta) -> None:
        """`EVENTOS` no está en `MANDOS_MEDIOS_SECCIONES`: ese rol solo opera en vacaciones y
        ausencias."""
        async with como(rol="mandos_medios") as c:
            assert (await c.get(ruta)).status_code == 403

    async def test_rol_desconocido_es_fail_closed(self, almacen, como) -> None:
        async with como(rol="rol_inventado") as c:
            assert (await c.get(BASE)).status_code == 403


# ── 11. El literal del 404 y la sección, en su lugar ──────────────────────────


class TestContratoDelModulo:
    def test_el_404_es_uno_solo(self) -> None:
        """Los tres motivos de rechazo (no existe / otra empresa / privado ajeno) salen del
        MISMO literal. Tres constantes serían tres mensajes que pueden divergir."""
        from services._eventos_write import NO_ENCONTRADO
        assert NO_ENCONTRADO == ("Evento no encontrado", "EVENTO_NOT_FOUND", 404)

    def test_la_seccion_no_es_de_mandos_medios(self) -> None:
        from utils.permisos import MANDOS_MEDIOS_SECCIONES, Seccion
        assert Seccion.EVENTOS not in MANDOS_MEDIOS_SECCIONES

    def test_el_rol_que_ve_las_privadas_ajenas_es_UNO_SOLO(self) -> None:
        """El literal es compartido con las plantillas de onboarding a propósito: dos copias
        podrían separarse, y la que se olvidara de cambiar dejaría abierto lo que la otra cerró.
        """
        from repositories._evento_agenda_filtros import ROL_VE_PRIVADAS_AJENAS
        from repositories._onboarding_templates_filtros import ROL_VE_TODO
        assert ROL_VE_PRIVADAS_AJENAS is ROL_VE_TODO

    def test_el_techo_de_la_ventana_es_el_del_CHECK(self) -> None:
        """Si el CHECK de la base sube, este número tiene que subir con él o el recorte de la
        query dejaría de ser exacto y empezaría a perder eventos en silencio."""
        from schemas.evento_agenda import MAX_DIAS_AVISO
        from services._eventos_pendientes import TECHO_DIAS
        assert TECHO_DIAS == MAX_DIAS_AVISO

    def test_no_hay_export(self) -> None:
        """Decisión de producto. Un `formato` en alguna ruta metería el módulo en el barrido de
        paridad list/export y en el del límite de filas, que acá no tienen nada que mirar."""
        rutas = [r for r in app.routes if getattr(r, "path", "").startswith(BASE)]
        assert rutas, "el módulo no está montado"
        assert not any("exportar" in r.path for r in rutas)

    def test_las_seis_rutas_estan_montadas(self) -> None:
        montadas = {(m, r.path) for r in app.routes if getattr(r, "path", "").startswith(BASE)
                    for m in (r.methods - {"HEAD", "OPTIONS"})}
        assert montadas == {
            ("GET", "/api/eventos"), ("POST", "/api/eventos"),
            ("GET", "/api/eventos/pendientes"),
            ("GET", "/api/eventos/{id}"), ("PUT", "/api/eventos/{id}"),
            ("DELETE", "/api/eventos/{id}"), ("PUT", "/api/eventos/{id}/resuelta"),
        }
