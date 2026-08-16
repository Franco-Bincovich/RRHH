"""
Asignaciones de capacitación con `empleado_id` NULL (migración 116, filas de nombre libre).

## Qué cubre

El Excel de formación trae 41 nombres escritos a mano contra 31 colaboradores cargados. Lo que
no matchea entra igual, con `nombre_libre` y sin empleado. Hoy `empleado_capacitacion` está en 0
filas, así que la migración es INERTE — y por eso estos tests se escriben ahora: el día que el
import cargue la primera fila con NULL, sin los cuatro arreglos **se cae el listado ENTERO**, no
la fila.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

**1. 🔴 EL BUG PRINCIPAL VIVE EN EL REPO, NO EN EL SERVICE — y un doble de repo no puede
cazarlo.** El `None` no rompe en Python: rompe cuando el SDK RENDERIZA el filtro y PostgREST lo
castea a uuid. Un `_FakeAsignacionRepo` que devuelva `AsignacionResponse` ya armados nunca arma
esa URL, así que pasaría con el bug vivo. Por eso acá corren el **router, el service y el repo
REALES**, y lo falseado es `supabase_admin` — el punto exacto donde el payload sale hacia
PostgREST. Molde: `_SupabaseEspia` de `test_ids_tipados_uuid.py`.

**2. 🔴 EL DOBLE RENDERIZA COMO EL SDK, NO COMO A MÍ ME CONVIENE.** `postgrest-py` arma el `in_`
haciendo `",".join(map(str, valores))`: un `None` viaja literalmente como `in.(None,<uuid>)` y
Postgres falla al castear `"None"` a uuid. El doble reproduce ESE renderizado y rechaza lo que
PostgREST rechazaría — si en cambio guardara la lista tal cual, aceptaría el `None` sin chistar y
el test pasaría con el filtro borrado, que es exactamente lo que revienta en producción.

**3. 🔴 EL DOBLE TIENE SU PROPIO TEST** (`TestElDobleSabeDecirQueNo`). Un doble que no rechaza
nada convierte a todos los demás tests de este archivo en decorativos, y eso NO se ve leyéndolos:
se ven verdes igual. Se verifica que rechace el `None` y la lista vacía ANTES de confiar en él.

**4. 🔴 EL CONTRASTE.** Un listado sin ninguna fila NULL tiene que seguir andando idéntico: sin
ese caso, un repo que devolviera `[]` siempre haría pasar "no se cae el listado".

⚠️ Se falsea la autenticación, no la autorización (molde `test_ids_tipados_uuid.py`): el gate de
`Seccion.CAPACITACIONES` corre de verdad, por eso el rol es `admin_rrhh`.
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

from types import SimpleNamespace  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import middleware.auth as auth_mod  # noqa: E402
import repositories._asignacion_row as row_mod  # noqa: E402
import repositories.asignacion_repo as repo_mod  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

_RUTA = "/api/capacitaciones/asignaciones"
_EMPRESA = str(uuid4())
_CAP = str(uuid4())
_EMPLEADO = str(uuid4())
_AREA = str(uuid4())


class _RechazoPostgrestError(Exception):
    """Lo que PostgREST devuelve como 400: el filtro no se pudo parsear o castear."""


def _render_in(valores: list) -> str:
    """El renderizado REAL de `postgrest-py`: `in.(<str(v) por coma>)`. Es la línea que convierte
    un `None` de Python en el texto `None` dentro de la URL."""
    return ",".join(str(v) for v in valores)


class _SupabaseEspia:
    """Doble de `supabase_admin` que renderiza los filtros como el SDK y rechaza como PostgREST.

    🔴 ES LO QUE HACE FALSABLE EL FILTRO DE `None`. Un doble que se quedara con la lista de
    Python aceptaría cualquier cosa; acá el `.in_()` se convierte en el texto que viaja en la URL
    y se valida contra el tipo de la columna, igual que del otro lado.
    """

    def __init__(self, tablas: dict) -> None:
        self._tablas = tablas
        self.filtros_in: list = []      # (tabla, campo, texto renderizado)
        self._t = ""
        self._rows: list = []
        self._una = False

    def table(self, t):
        self._t = t
        self._rows = list(self._tablas.get(t, []))
        self._una = False
        return self

    def select(self, *a, **k): return self
    def order(self, *a, **k): return self

    def maybe_single(self):
        self._una = True
        return self

    def eq(self, campo, valor):
        self._rows = [r for r in self._rows if str(r.get(campo)) == str(valor)]
        return self

    def in_(self, campo, valores):
        texto = _render_in(valores)
        self.filtros_in.append((self._t, campo, texto))
        if not valores:
            # `id=in.()` no es un filtro válido: PostgREST no lo parsea.
            raise _RechazoPostgrestError(f"{campo}=in.() — lista vacía")
        for token in texto.split(","):
            try:
                UUID(token)
            except ValueError:
                raise _RechazoPostgrestError(
                    f'{campo}=in.({texto}) — invalid input syntax for type uuid: "{token}"'
                ) from None
        self._rows = [r for r in self._rows if str(r.get(campo)) in texto.split(",")]
        return self

    def range(self, desde, hasta):
        self._rango = (desde, hasta)
        return self

    def execute(self):
        if self._una:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        # `count` es el del filtro y el `.range()` recorta DESPUÉS — el orden de PostgREST.
        total = len(self._rows)
        rango = getattr(self, "_rango", None)
        filas = self._rows[rango[0]:rango[1] + 1] if rango else self._rows
        return SimpleNamespace(data=filas, count=total)


def _fila(empleado_id, nombre_libre=None) -> dict:
    """Una fila cruda de `empleado_capacitacion` como la devuelve `select("*")`."""
    return {
        "id": str(uuid4()), "empresa_id": _EMPRESA, "capacitacion_id": _CAP,
        "empleado_id": empleado_id, "nombre_libre": nombre_libre, "estado": "completado",
        "fecha_asignacion": None, "fecha_limite": None, "fecha_completado": None,
        "certificado_url": None, "created_at": "2026-08-13T10:00:00+00:00",
        "proyecto": None, "anio": "2024", "mes": "marzo",
    }


_CON_EMPLEADO = _fila(_EMPLEADO)
_SIN_EMPLEADO = _fila(None, "Perez Juan")
_NOMBRE_SUELTO = "Perez Juan"


def _tablas(filas: list) -> dict:
    return {
        "empleado_capacitacion": filas,
        "empresas": [{"id": _EMPRESA, "nombre": "Karstec"}],
        "capacitaciones": [{"id": _CAP, "nombre": "Higiene y seguridad"}],
        "empleados": [{"id": _EMPLEADO, "nombre": "Ana", "apellido": "Gómez", "area_id": _AREA}],
        "areas": [{"id": _AREA, "nombre": "Sistemas"}],
    }


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: str(uuid4()))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda user_id: EstadoUsuario(rol="admin_rrhh", activo=True))


def _montar(monkeypatch, filas: list) -> _SupabaseEspia:
    """Falsea el ÚNICO punto de contacto con la base. El repo, el service y el router son reales.

    Son DOS módulos porque el enriquecido vive en `_asignacion_row` desde que se dividió el repo:
    parchear uno solo dejaría el otro pegando contra el cliente real."""
    espia = _SupabaseEspia(_tablas(filas))
    monkeypatch.setattr(repo_mod, "supabase_admin", espia)
    monkeypatch.setattr(row_mod, "supabase_admin", espia)
    return espia


async def _get(ruta: str) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                                 base_url="http://test") as c:
        return await c.get(ruta, headers={"Authorization": "Bearer token-valido"})


# ─── El doble, antes de confiar en él ────────────────────────────────────────

class TestElDobleSabeDecirQueNo:
    """Sin esto, el resto del archivo podría estar en verde sobre un doble que acepta todo."""

    def test_un_none_adentro_del_in_es_rechazado(self) -> None:
        espia = _SupabaseEspia(_tablas([]))
        with pytest.raises(_RechazoPostgrestError):
            espia.table("empleados").select("id").in_("id", [None, _EMPLEADO])

    def test_la_lista_vacia_tambien(self) -> None:
        espia = _SupabaseEspia(_tablas([]))
        with pytest.raises(_RechazoPostgrestError):
            espia.table("empleados").select("id").in_("id", [])

    def test_una_lista_de_uuid_pasa(self) -> None:
        """La contracara: si rechazara TODO, los tests de abajo no probarían nada tampoco."""
        espia = _SupabaseEspia(_tablas([]))
        assert espia.table("empleados").select("id").in_("id", [_EMPLEADO]).execute().data


# ─── El listado ──────────────────────────────────────────────────────────────

class TestElListadoNoSeCae:
    async def test_una_fila_sin_empleado_no_tumba_el_listado(self, auth, monkeypatch) -> None:
        """🔴 EL TEST DE LA SESIÓN. Con el `None` sin filtrar, el lookup de empleados manda
        `id=in.(None,<uuid>)` y responde 400: se caen LAS DOS filas, no la incompleta."""
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        r = await _get(_RUTA)
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 2, "la fila con empleado también desapareció"

    async def test_la_fila_sin_empleado_trae_el_nombre_libre(self, auth, monkeypatch) -> None:
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        items = (await _get(_RUTA)).json()["items"]
        suelta = [i for i in items if i["empleado_id"] is None]
        assert len(suelta) == 1, "sin `Optional[str]` en el schema esto es un 500, no una fila"
        assert suelta[0]["nombre_libre"] == _NOMBRE_SUELTO
        assert suelta[0]["empleado_nombre"] is None, "no hay empleado: el nombre resuelto es None"
        assert suelta[0]["area_nombre"] is None, "el área sale del empleado"

    async def test_la_fila_con_empleado_sigue_resolviendo_nombre_y_area(self, auth, monkeypatch) -> None:
        """El contraste dentro del mismo listado: el enriquecido no se rompió al filtrar."""
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        items = (await _get(_RUTA)).json()["items"]
        vinculada = [i for i in items if i["empleado_id"] == _EMPLEADO]
        assert len(vinculada) == 1
        assert vinculada[0]["empleado_nombre"] == "Ana Gómez"
        assert vinculada[0]["area_nombre"] == "Sistemas"

    async def test_un_listado_sin_ninguna_fila_null_funciona_igual(self, auth, monkeypatch) -> None:
        """🔴 EL CONTRASTE. Sin este caso, un repo que devolviera siempre `[]` pasaría el test
        de arriba: 'no se cayó' y 'no trajo nada' son indistinguibles con un solo escenario."""
        _montar(monkeypatch, [_CON_EMPLEADO])
        cuerpo = (await _get(_RUTA)).json()
        assert cuerpo["total"] == 1
        assert cuerpo["items"][0]["empleado_nombre"] == "Ana Gómez"

    async def test_todas_las_filas_sin_empleado_tampoco_lo_tumban(self, auth, monkeypatch) -> None:
        """El borde del otro lado: con NINGÚN empleado que resolver, la lista de ids queda vacía
        y `.in_("id", [])` viaja como `id=in.()`, que tampoco es un filtro válido."""
        _montar(monkeypatch, [_SIN_EMPLEADO])
        r = await _get(_RUTA)
        assert r.status_code == 200, r.text
        assert r.json()["items"][0]["nombre_libre"] == _NOMBRE_SUELTO


# ─── El export ───────────────────────────────────────────────────────────────

class TestElExport:
    async def test_el_archivo_sale_y_la_columna_empleado_no_esta_vacia(self, auth, monkeypatch) -> None:
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        r = await _get(f"{_RUTA}/exportar?formato=csv")
        assert r.status_code == 200, r.text
        texto = r.content.decode("utf-8-sig")
        assert _NOMBRE_SUELTO in texto, "la columna Empleado salió vacía en la fila sin vincular"
        assert "Ana Gómez" in texto

    async def test_las_dos_filas_se_distinguen_por_la_columna_vinculado(self, auth, monkeypatch) -> None:
        """🔴 LO QUE HACE ÚTIL AL FALLBACK. Sin esta columna, RRHH abre el Excel y ve dos nombres
        iguales sin saber cuál cuelga de alguien del sistema."""
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        texto = (await _get(f"{_RUTA}/exportar?formato=csv")).content.decode("utf-8-sig")
        filas = {ln.split(",")[1]: ln for ln in texto.splitlines() if "," in ln}
        assert "Empleado vinculado" in texto, "el export no distingue un nombre suelto de uno real"
        assert filas["Ana Gómez"].split(",")[2] == "Sí"
        assert filas[_NOMBRE_SUELTO].split(",")[2] == "No"


# ─── El filtro por área, documentado (no es un arreglo) ──────────────────────

class TestElFiltroPorAreaEscondeLasFilasSueltas:
    """⚠️ NO ES UN BUG NI UN PENDIENTE: es la definición. El área sale del empleado, así que una
    fila sin empleado no cae bajo ninguna. Mismo criterio que el filtro por proyecto en
    evaluaciones y que "un proyecto sin asignados no aparece bajo ninguna área".

    🔴 Pero el usuario NO recibe ningún aviso: ve menos filas y nada se lo dice. Queda fijado acá
    para que el día que se decida avisarlo, este test sea el que cambia."""

    async def test_filtrar_por_area_excluye_la_fila_de_nombre_libre(self, auth, monkeypatch) -> None:
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        cuerpo = (await _get(f"{_RUTA}?area_id={_AREA}")).json()
        assert cuerpo["total"] == 1, "el filtro por área dejó de acotar"
        assert cuerpo["items"][0]["empleado_id"] == _EMPLEADO

    async def test_sin_filtro_de_area_las_dos_aparecen(self, auth, monkeypatch) -> None:
        """El contraste que prueba que la de arriba desaparece POR el filtro y no por otra cosa."""
        _montar(monkeypatch, [_CON_EMPLEADO, _SIN_EMPLEADO])
        assert (await _get(_RUTA)).json()["total"] == 2


# ─── La guarda que exige `test_mappers_ejercitados` ──────────────────────────

def test_la_lista_vacia_no_prueba_nada() -> None:
    """`_asignacion_row._build` abre con `if not rows: return []`. Llamarlo con `[]` no ejecuta
    una sola línea de su cuerpo: este test deja constancia de que los de arriba lo llaman CON
    elementos, que es lo que el barrido de mappers pide."""
    assert row_mod._build([]) == []
