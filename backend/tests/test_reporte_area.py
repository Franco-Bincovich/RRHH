"""
Tests del filtro de empresa/área en reportes (Sesión 3A):
- (a) el schema acepta los tipos que antes daban 422 (anual_consolidado / altas_bajas / distribucion);
- (b) filtro de área DIRECTO (headcount) excluye otras áreas y sin área trae toda la empresa;
- (c) filtro de área con JOIN por empleado (rotacion / onboarding / costos) EXCLUYE otras áreas;
- (e) el router usa la empresa del BODY, no la del header del sidebar.
El fake de supabase aplica de verdad los .eq / .gte / .lte (incl. claves anidadas "empleados.area_id"),
así que si el código no agrega el filtro, el test lo detecta (no solo "no rompe").
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

from types import SimpleNamespace

from starlette.requests import Request

import services.reportes._reporte_costos as cos
import services.reportes._reporte_dotacion as dot
import services.reportes._reporte_seleccion as sel
from routers.reportes import generar_reporte
from schemas.reporte import ReporteGenerarRequest


def _get(row: dict, col: str):
    if "." in col:
        a, b = col.split(".", 1)
        return (row.get(a) or {}).get(b)
    return row.get(col)


class _Q:
    """Query fake que aplica realmente eq/gte/lte sobre un dataset (soporta clave anidada)."""
    def __init__(self, rows):
        self._rows, self._eq, self._gte, self._lte = rows, {}, {}, {}

    def select(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def eq(self, col, val):
        self._eq[col] = str(val)
        return self

    def gte(self, col, val):
        self._gte[col] = str(val)
        return self

    def lte(self, col, val):
        self._lte[col] = str(val)
        return self

    def _match(self, row) -> bool:
        for c, v in self._eq.items():
            if str(_get(row, c)) != v:
                return False
        for c, v in self._gte.items():
            a = _get(row, c)
            if a is None or str(a) < v:
                return False
        for c, v in self._lte.items():
            a = _get(row, c)
            if a is None or str(a) > v:
                return False
        return True

    def execute(self):
        data = [r for r in self._rows if self._match(r)]
        return SimpleNamespace(data=data, count=len(data))


class _FakeDB:
    def __init__(self, tablas: dict):
        self._t = tablas

    def table(self, name):
        return _Q(self._t.get(name, []))


# ── (a) schema ──────────────────────────────────────────────────────────────────

def test_schema_acepta_tipos_que_daban_422():
    for t in ("anual_consolidado", "altas_bajas", "distribucion"):
        assert ReporteGenerarRequest(tipo=t).tipo == t


# ── (b) filtro directo + (d) sin área = toda la empresa ─────────────────────────

def _empleados_db():
    return _FakeDB({
        "empleados": [
            {"id": 1, "estado": "activo", "area_id": "A", "fecha_ingreso": "2026-03-05"},
            {"id": 2, "estado": "activo", "area_id": "B", "fecha_ingreso": "2026-03-06"},
        ],
        "areas": [{"id": "A", "nombre": "Tec", "activo": True},
                  {"id": "B", "nombre": "Ventas", "activo": True}],
    })


def test_headcount_area_directo_excluye_otras(monkeypatch):
    monkeypatch.setattr(dot, "supabase_admin", _empleados_db())
    r = dot.generate_headcount(3, 2026, empresa_id=None, area_id="A")
    assert r["total_empleados"] == 1 and r["ingresos_periodo"] == 1     # solo área A
    assert {x["nombre"] for x in r["por_area"]} == {"Tec"}              # B excluido


def test_headcount_sin_area_toda_la_empresa(monkeypatch):
    monkeypatch.setattr(dot, "supabase_admin", _empleados_db())
    r = dot.generate_headcount(3, 2026, empresa_id=None, area_id=None)
    assert r["total_empleados"] == 2                                    # A y B


# ── (c) filtro con JOIN por empleado excluye otras áreas ────────────────────────

def test_rotacion_area_join_excluye_otras(monkeypatch):
    monkeypatch.setattr(dot, "supabase_admin", _FakeDB({
        "empleados": [{"id": 1, "estado": "activo", "area_id": "A"}],
        "offboarding_instancias": [
            {"motivo": "renuncia", "created_at": "2026-03-10T00:00:00", "empleados": {"area_id": "A"}},
            {"motivo": "despido", "created_at": "2026-03-11T00:00:00", "empleados": {"area_id": "B"}},
        ],
    }))
    r = dot.generate_rotacion(3, 2026, empresa_id=None, area_id="A")
    assert r["bajas_periodo"] == 1                    # la baja de B queda excluida por el join
    assert r["motivos_egreso"] == {"renuncia": 1}


def test_onboarding_area_join_excluye_otras(monkeypatch):
    monkeypatch.setattr(sel, "supabase_admin", _FakeDB({
        "onboarding_instancias": [
            {"id": 1, "progreso": 50, "estado": "en_progreso", "created_at": "2026-01-01",
             "empleados": {"nombre": "Ana", "apellido": "G", "area_id": "A"}},
            {"id": 2, "progreso": 80, "estado": "en_progreso", "created_at": "2026-01-02",
             "empleados": {"nombre": "Beto", "apellido": "R", "area_id": "B"}},
        ],
    }))
    r = sel.generate_onboarding(empresa_id=None, area_id="A")
    assert r["total_activos"] == 1 and r["detalle"][0]["empleado"] == "Ana G"


def test_costos_area_join_excluye_otras(monkeypatch):
    monkeypatch.setattr(cos, "supabase_admin", _FakeDB({
        "costos_nomina": [
            {"total": 1000, "mes": 3, "anio": 2026, "empleados": {"area_id": "A", "areas": {"nombre": "Tec"}}},
            {"total": 500, "mes": 3, "anio": 2026, "empleados": {"area_id": "B", "areas": {"nombre": "Ventas"}}},
        ],
        "presupuesto_areas": [
            {"monto_presupuestado": 800, "mes": 3, "anio": 2026, "tipo_costo": "nomina", "area_id": "A", "areas": {"nombre": "Tec"}},
            {"monto_presupuestado": 400, "mes": 3, "anio": 2026, "tipo_costo": "nomina", "area_id": "B", "areas": {"nombre": "Ventas"}},
        ],
    }))
    r = cos.generate_costos(3, 2026, empresa_id=None, area_id="A")
    assert r["total_nomina"] == 1000.0 and r["total_presupuesto"] == 800.0   # B excluido en ambos lados


# ── (e) el router usa la empresa del BODY, no la del header ─────────────────────

async def test_router_usa_empresa_del_body_no_del_header():
    captured: dict = {}

    class _Svc:
        def generar(self, **kw):
            captured.update(kw)
            return SimpleNamespace(id="r1")

    # request.state.empresa_id (header del sidebar) es DISTINTO de la empresa del body
    # Request real y no SimpleNamespace: generar_reporte está decorado con el rate
    # limiter, que exige un starlette Request de verdad para poder leer la IP.
    req = Request({"type": "http", "path": "/api/reportes/generar", "headers": [],
                   "client": ("9.0.0.1", 1)})
    req.state.user = {"email": "u@x.com"}
    req.state.empresa_id = "HEADER-EMP"
    body = ReporteGenerarRequest(tipo="headcount", mes=3, anio=2026,
                                 empresa_id="11111111-1111-1111-1111-111111111111",
                                 area_id="22222222-2222-2222-2222-222222222222")
    await generar_reporte(req, body, _Svc())
    assert str(captured["empresa_id"]) == "11111111-1111-1111-1111-111111111111"  # del body
    assert str(captured["area_id"]) == "22222222-2222-2222-2222-222222222222"
    assert "HEADER-EMP" not in {str(v) for v in captured.values()}                # nunca el header
