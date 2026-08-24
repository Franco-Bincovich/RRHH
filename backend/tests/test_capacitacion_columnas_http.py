"""
Las 7 columnas de formación (mig 116) VIAJAN por HTTP: entran por el POST/PUT, salen por el GET
y aparecen en el export. Complemento dinámico del barrido estático
(`test_columnas_capacitaciones.py`): aquel prueba que el schema DECLARA cada columna; este, que
el camino completo router → service → repo → insert las escribe y las devuelve de verdad.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

**El doble construye cada respuesta A PARTIR DE LO QUE EL REPO LE ENTREGA, nunca de un objeto
prefabricado.** El `insert()` guarda el payload que el repo armó y el `select` posterior devuelve
ESA fila (más los defaults que pondría la base: id, created_at, activo). Así:
  · si `save()` deja de escribir una columna, la fila guardada no la tiene y el GET la devuelve
    en None → rojo;
  · si el Response la pierde, Pydantic la descarta al validar y el body no la trae → rojo;
  · si el export deja de proyectarla, el CSV pierde el header o el valor → rojo.
Un doble que devolviera una fila completa preescrita pasaría con `save()` roto — exactamente el
verde falso que la regla del repo prohíbe (ver `test_domicilio_desglosado.py`).

Se falsea la autenticación, no la autorización: el gate de `Seccion.CAPACITACIONES` corre de
verdad, por eso el rol es `admin_rrhh`. Molde: `test_capacitacion_nombre_libre.py`.
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
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import middleware.auth as auth_mod  # noqa: E402
import repositories._asignacion_row as asig_row_mod  # noqa: E402
import repositories._capacitacion_row as cap_row_mod  # noqa: E402
import repositories.asignacion_repo as asig_repo_mod  # noqa: E402
import repositories.capacitacion_repo as cap_repo_mod  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

_RUTA_CAT = "/api/capacitaciones"
_RUTA_ASIG = "/api/capacitaciones/asignaciones"
_EMPRESA = str(uuid4())
_CAP = str(uuid4())
_EMPLEADO = str(uuid4())

# Lo que la base pondría por DEFAULT en un INSERT — lo único que el doble agrega de su cosecha.
# Todo lo demás de cada fila sale del payload que el repo escribió.
_DEFAULTS = {
    "capacitaciones": {"activo": True, "created_at": "2026-08-19T10:00:00+00:00"},
    "empleado_capacitacion": {"created_at": "2026-08-19T10:00:00+00:00"},
}


class _SupabaseEscritura:
    """Doble de `supabase_admin` con memoria: el insert/update pega contra las mismas tablas que
    después sirve el select. Ver el encabezado: la respuesta nace del payload recibido."""

    def __init__(self, tablas: dict) -> None:
        self._tablas = {t: list(rows) for t, rows in tablas.items()}

    def table(self, t):
        return _Query(self._tablas, t)


class _Query:
    def __init__(self, tablas: dict, t: str) -> None:
        self._tablas, self._t = tablas, t
        self._rows = list(tablas.get(t, []))
        self._una = False
        self._insertada = None
        self._update = None

    def select(self, *a, **k): return self
    def order(self, *a, **k): return self
    def range(self, *a, **k): return self

    def maybe_single(self):
        self._una = True
        return self

    def insert(self, payload: dict):
        fila = {"id": str(uuid4()), **_DEFAULTS.get(self._t, {}), **payload}
        self._tablas.setdefault(self._t, []).append(fila)
        self._insertada = fila
        return self

    def update(self, payload: dict):
        self._update = payload
        return self

    def eq(self, campo, valor):
        self._rows = [r for r in self._rows if str(r.get(campo)) == str(valor)]
        return self

    def in_(self, campo, valores):
        self._rows = [r for r in self._rows if str(r.get(campo)) in {str(v) for v in valores}]
        return self

    def execute(self):
        if self._insertada is not None:
            return SimpleNamespace(data=[self._insertada], count=1)
        if self._update is not None:
            # El update real muta la tabla compartida, no la copia filtrada de esta query.
            ids = {r["id"] for r in self._rows}
            for r in self._tablas.get(self._t, []):
                if r["id"] in ids:
                    r.update(self._update)
            return SimpleNamespace(data=self._rows, count=len(self._rows))
        if self._una:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        return SimpleNamespace(data=self._rows, count=len(self._rows))


def _tablas_base() -> dict:
    return {
        "empresas": [{"id": _EMPRESA, "nombre": "Karstec"}],
        "capacitaciones": [{
            "id": _CAP, "empresa_id": _EMPRESA, "nombre": "Explorando la IA",
            "descripcion": None, "categoria": None, "duracion_horas": 6.0,
            "entidad_capacitadora": "Kinetic", "modalidad": "Virtual", "tipo": "Capacitación",
            "obligatoria": False, "activo": True, "created_at": "2026-08-19T10:00:00+00:00",
        }],
        "empleados": [{"id": _EMPLEADO, "empresa_id": _EMPRESA, "nombre": "Ana",
                       "apellido": "Gómez", "area_id": None}],
        "areas": [],
        "empleado_capacitacion": [],
    }


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: (str(uuid4()), "smoke@x.test"))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda user_id: EstadoUsuario(rol="admin_rrhh", activo=True))


def _montar(monkeypatch) -> _SupabaseEscritura:
    """Falsea el ÚNICO punto de contacto con la base, en los CUATRO módulos que lo importan
    (los dos repos y sus dos satélites `_row`): parchear menos deja alguno pegando al real."""
    doble = _SupabaseEscritura(_tablas_base())
    for mod in (cap_repo_mod, cap_row_mod, asig_repo_mod, asig_row_mod):
        monkeypatch.setattr(mod, "supabase_admin", doble)
    return doble


async def _req(metodo: str, ruta: str, body: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                                 base_url="http://test") as c:
        return await c.request(metodo, ruta, json=body,
                               headers={"Authorization": "Bearer token-valido"})


# ─── Catálogo: las tres de la mig 116 entran y vuelven ───────────────────────

class TestCatalogo:
    async def test_post_con_las_tres_columnas_las_devuelve(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        r = await _req("POST", _RUTA_CAT, {
            "empresa_id": _EMPRESA, "nombre": "HTML desde Cero", "obligatoria": False,
            "entidad_capacitadora": "Udemy", "modalidad": "Virtual", "tipo": "Capacitación",
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["entidad_capacitadora"] == "Udemy"
        assert body["modalidad"] == "Virtual"
        assert body["tipo"] == "Capacitación"

    async def test_el_listado_trae_las_tres(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        item = [i for i in (await _req("GET", _RUTA_CAT)).json()["items"] if i["id"] == _CAP][0]
        assert item["entidad_capacitadora"] == "Kinetic"
        assert item["modalidad"] == "Virtual"
        assert item["tipo"] == "Capacitación"

    async def test_el_put_escribe_una_de_las_tres(self, auth, monkeypatch) -> None:
        doble = _montar(monkeypatch)
        r = await _req("PUT", f"{_RUTA_CAT}/{_CAP}", {"modalidad": "Presencial"})
        assert r.status_code == 200, r.text
        assert r.json()["modalidad"] == "Presencial"
        fila = doble._tablas["capacitaciones"][0]
        assert fila["modalidad"] == "Presencial", "el PUT respondió bien pero no escribió la fila"

    async def test_el_export_del_catalogo_las_incluye(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        r = await _req("GET", f"{_RUTA_CAT}/exportar?formato=csv")
        assert r.status_code == 200, r.text
        texto = r.content.decode("utf-8-sig")
        assert "Entidad capacitadora" in texto and "Kinetic" in texto
        assert "Modalidad" in texto and "Tipo" in texto


# ─── Asignaciones: proyecto/anio/mes/nombre_libre entran y vuelven ───────────

class TestAsignaciones:
    _BODY = {
        "capacitacion_id": _CAP, "empleado_id": _EMPLEADO,
        "proyecto": "Elinpar", "anio": "2026", "mes": "marzo", "nombre_libre": "Perez Juan",
    }

    async def test_post_con_las_cuatro_columnas_las_devuelve(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        r = await _req("POST", _RUTA_ASIG, self._BODY)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["proyecto"] == "Elinpar"
        assert body["anio"] == "2026", "anio es TEXT en la base: tiene que volver como string"
        assert body["mes"] == "marzo"
        assert body["nombre_libre"] == "Perez Juan"

    async def test_el_put_escribe_proyecto_y_mes(self, auth, monkeypatch) -> None:
        doble = _montar(monkeypatch)
        creada = (await _req("POST", _RUTA_ASIG, self._BODY)).json()
        r = await _req("PUT", f"{_RUTA_ASIG}/{creada['id']}",
                       {"proyecto": "Escobar", "mes": "Julio"})
        assert r.status_code == 200, r.text
        assert r.json()["proyecto"] == "Escobar"
        assert r.json()["mes"] == "Julio"
        fila = doble._tablas["empleado_capacitacion"][0]
        assert fila["proyecto"] == "Escobar", "el PUT respondió bien pero no escribió la fila"

    async def test_el_export_de_asignaciones_las_incluye(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        await _req("POST", _RUTA_ASIG, self._BODY)
        r = await _req("GET", f"{_RUTA_ASIG}/exportar?formato=csv")
        assert r.status_code == 200, r.text
        texto = r.content.decode("utf-8-sig")
        for esperado in ("Proyecto", "Año", "Mes", "Elinpar", "2026", "marzo"):
            assert esperado in texto, f"el export perdió {esperado!r}"
