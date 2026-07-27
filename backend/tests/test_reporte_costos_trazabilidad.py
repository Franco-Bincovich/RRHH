"""
Tests SINTÉTICOS de los reportes de Costos + Trazabilidad (Sesión 4). Las tablas tienen pocos/0
datos en prod, esta es la única verificación real. El fake de supabase aplica de verdad los
.eq/.gte/.lte (incl. "empleados.area_id"), así que un filtro faltante se detecta.
- R5 costos: suma por período + filtro de área por JOIN excluye la otra.
- R8 presupuesto: presupuestado vs ejecutado → desvío y % ejecución; área directa filtra.
- R16 capacitación: conteo por estado + horas por área; filtro de área excluye la otra.
- R17 auditoría: proyecta fecha/usuario(nombre)/entidad/evento/acción; período recorta; empresa del body.
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

from datetime import date, datetime
from types import SimpleNamespace

from starlette.requests import Request

import services.reportes._reporte_auditoria as aud
import services.reportes._reporte_capacitacion as cap
import services.reportes._reporte_costos as cos
from routers.reportes import generar_reporte
from schemas.reporte import ReporteGenerarRequest


def _get(row: dict, col: str):
    if "." in col:
        a, b = col.split(".", 1)
        return (row.get(a) or {}).get(b)
    return row.get(col)


class _Q:
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


# ── R5 costos ────────────────────────────────────────────────────────────────────

def _costos_db():
    return _FakeDB({
        "costos_nomina": [
            {"total": 1000, "mes": 3, "anio": 2026, "empleados": {"area_id": "A", "areas": {"nombre": "Tec"}}},
            {"total": 400, "mes": 3, "anio": 2026, "empleados": {"area_id": "B", "areas": {"nombre": "Ventas"}}},
        ],
        "presupuesto_areas": [],
    })


def test_costos_suma_periodo(monkeypatch):
    monkeypatch.setattr(cos, "supabase_admin", _costos_db())
    r = cos.generate_costos(3, 2026, None, None)
    assert r["total_nomina"] == 1400.0
    assert {a["area"] for a in r["por_area"]} == {"Tec", "Ventas"}


def test_costos_filtro_area_excluye_otra(monkeypatch):
    monkeypatch.setattr(cos, "supabase_admin", _costos_db())
    r = cos.generate_costos(3, 2026, None, "A")
    assert r["total_nomina"] == 1000.0 and {a["area"] for a in r["por_area"]} == {"Tec"}


# ── R8 presupuesto vs real ────────────────────────────────────────────────────────

def _pre_db():
    return _FakeDB({
        "presupuesto_areas": [
            {"monto_presupuestado": 1000, "monto_ejecutado": 1200, "mes": 3, "anio": 2026,
             "area_id": "A", "areas": {"nombre": "Tec"}},
            {"monto_presupuestado": 500, "monto_ejecutado": 300, "mes": 3, "anio": 2026,
             "area_id": "B", "areas": {"nombre": "Ventas"}},
        ],
    })


def test_presupuesto_desvio_y_pct(monkeypatch):
    monkeypatch.setattr(cos, "supabase_admin", _pre_db())
    r = cos.generate_presupuesto(3, 2026, None, None)
    por = {a["area"]: a for a in r["por_area"]}
    assert por["Tec"]["desvio"] == 200.0 and por["Tec"]["ejecucion_pct"] == 120.0     # sobreejecutado
    assert por["Ventas"]["desvio"] == -200.0 and por["Ventas"]["ejecucion_pct"] == 60.0
    assert r["total_presupuestado"] == 1500.0 and r["total_ejecutado"] == 1500.0
    assert r["desvio"] == 0.0 and r["ejecucion_pct"] == 100.0


def test_presupuesto_area_directa_filtra(monkeypatch):
    monkeypatch.setattr(cos, "supabase_admin", _pre_db())
    r = cos.generate_presupuesto(3, 2026, None, "A")
    assert {a["area"] for a in r["por_area"]} == {"Tec"}


# ── R16 capacitación por área ─────────────────────────────────────────────────────

def _cap_db():
    return _FakeDB({
        "empleado_capacitacion": [
            {"estado": "completado", "fecha_asignacion": "2026-03-02", "capacitaciones": {"duracion_horas": 4},
             "empleados": {"area_id": "A", "areas": {"nombre": "Tec"}}},
            {"estado": "pendiente", "fecha_asignacion": "2026-03-05", "capacitaciones": {"duracion_horas": 2},
             "empleados": {"area_id": "A", "areas": {"nombre": "Tec"}}},
            {"estado": "en_curso", "fecha_asignacion": "2026-03-06", "capacitaciones": {"duracion_horas": 3},
             "empleados": {"area_id": "B", "areas": {"nombre": "Ventas"}}},
        ],
    })


def test_capacitacion_conteo_y_horas(monkeypatch):
    monkeypatch.setattr(cap, "supabase_admin", _cap_db())
    r = cap.generate_capacitacion(3, 2026, None, None)
    por = {a["area"]: a for a in r["por_area"]}
    assert por["Tec"]["asignaciones"] == 2 and por["Tec"]["completadas"] == 1 and por["Tec"]["pendientes"] == 1
    assert por["Tec"]["horas_totales"] == 6.0
    assert por["Ventas"]["en_curso"] == 1 and por["Ventas"]["horas_totales"] == 3.0
    assert r["total_asignaciones"] == 3


def test_capacitacion_filtro_area_excluye_otra(monkeypatch):
    monkeypatch.setattr(cap, "supabase_admin", _cap_db())
    r = cap.generate_capacitacion(3, 2026, None, "A")
    assert {a["area"] for a in r["por_area"]} == {"Tec"}


# ── R17 auditoría / trazabilidad ──────────────────────────────────────────────────

def test_auditoria_proyecta_columnas_y_recorta_periodo():
    captured: dict = {}

    class _FakeRepo:
        def listar(self, **kw):
            captured.update(kw)
            ev = SimpleNamespace(created_at=datetime(2026, 3, 10, 14, 30), usuario_nombre="Ana G",
                                 entidad="empleados", evento="alta_empleado", accion="INSERT")
            return [ev], 1

    r = aud.generate_auditoria(3, 2026, empresa_id="EMP-1", repo=_FakeRepo())
    assert captured["empresa_id"] == "EMP-1"
    assert captured["fecha_desde"] == date(2026, 3, 1) and captured["fecha_hasta"] == date(2026, 3, 31)
    e0 = r["eventos"][0]
    assert e0 == {"fecha": "10/03/2026 14:30", "usuario": "Ana G", "entidad": "empleados",
                  "evento": "alta_empleado", "accion": "INSERT"}
    assert "datos_anteriores" not in e0 and "datos_nuevos" not in e0     # JSONB crudo excluido
    assert r["total_eventos"] == 1


def test_auditoria_usuario_sin_nombre_no_rompe():
    class _FakeRepo:
        def listar(self, **kw):
            ev = SimpleNamespace(created_at=datetime(2026, 3, 1, 9, 0), usuario_nombre=None,
                                 entidad="vacaciones", evento="baja", accion="DELETE")
            return [ev], 1

    r = aud.generate_auditoria(3, 2026, empresa_id=None, repo=_FakeRepo())
    assert r["eventos"][0]["usuario"] == "—"


# ── Router: empresa del BODY, no del header ───────────────────────────────────────

async def test_router_usa_empresa_del_body_sesion4():
    captured: dict = {}

    class _Svc:
        def generar(self, **kw):
            captured.update(kw)
            return SimpleNamespace(id="r1")

    # Request real y no SimpleNamespace: generar_reporte está decorado con el rate
    # limiter, que exige un starlette Request de verdad para poder leer la IP.
    req = Request({"type": "http", "path": "/api/reportes/generar", "headers": [],
                   "client": ("9.0.0.2", 1)})
    req.state.user = {"email": "u@x.com"}
    req.state.empresa_id = "HEADER-EMP"
    body = ReporteGenerarRequest(tipo="auditoria", mes=3, anio=2026,
                                 empresa_id="11111111-1111-1111-1111-111111111111")
    await generar_reporte(req, body, _Svc())
    assert str(captured["empresa_id"]) == "11111111-1111-1111-1111-111111111111"
    assert "HEADER-EMP" not in {str(v) for v in captured.values()}


def test_schema_acepta_reportes_sesion4():
    for t in ("presupuesto", "capacitacion", "auditoria"):
        assert ReporteGenerarRequest(tipo=t).tipo == t
