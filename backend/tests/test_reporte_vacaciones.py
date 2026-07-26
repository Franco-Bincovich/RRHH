"""
Tests SINTÉTICOS de los 3 reportes de vacaciones/ausencias (Sesión 3B) — las tablas están vacías
en prod, esta es la única verificación real. El fake de supabase aplica de verdad los
.eq/.gte/.lte (incl. claves anidadas "empleados.area_id"), así que un filtro faltante se detecta.
- R11 saldos: cancelada=false resta, cancelada=true NO; empleado sin asignados → 0 + marca.
- R10 ausentismo: días totales/injustificados y tasa por área; filtro de área excluye la otra;
  vista=injustificado trae solo esa columna; nota de 22 días presente.
- R9 listado: trae vacaciones y ausencias del período con sus campos propios.
- Router: empresa/vista del BODY, nunca del header (patrón 3A).
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

import services.reportes._reporte_ausentismo as aus
import services.reportes._reporte_vacaciones as vac
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


# ── R11 saldos de vacaciones ────────────────────────────────────────────────────

def test_saldos_cancelados_no_restan_y_sin_asignar(monkeypatch):
    monkeypatch.setattr(vac, "supabase_admin", _FakeDB({
        "empleados": [
            {"id": "e1", "estado": "activo", "area_id": "A", "nombre": "Ana", "apellido": "G",
             "dias_vacaciones_asignados": 20, "areas": {"nombre": "Tec"}},
            {"id": "e2", "estado": "activo", "area_id": "A", "nombre": "Beto", "apellido": "R",
             "dias_vacaciones_asignados": None, "areas": {"nombre": "Tec"}},
        ],
        "solicitudes_vacaciones": [
            {"empleado_id": "e1", "dias": 5, "cancelada": False, "fecha_desde": "2026-03-05"},
            {"empleado_id": "e1", "dias": 3, "cancelada": True, "fecha_desde": "2026-03-10"},
        ],
    }))
    r = vac.generate_saldos_vacaciones(3, 2026, empresa_id=None, area_id=None)
    filas = {f["empleado"]: f for f in r["saldos"]}
    assert filas["G, Ana"]["asignados"] == 20
    assert filas["G, Ana"]["tomados"] == 5              # los 3 días cancelados NO restan
    assert filas["G, Ana"]["saldo"] == 15
    assert filas["R, Beto"]["asignados"] == "Sin asignar"
    assert filas["R, Beto"]["tomados"] == 0 and filas["R, Beto"]["saldo"] == 0


# ── R10 ausentismo por área ─────────────────────────────────────────────────────

def _aus_db():
    return _FakeDB({
        "empleados": [
            {"id": "e1", "estado": "activo", "area_id": "A", "areas": {"nombre": "Tec"}},
            {"id": "e2", "estado": "activo", "area_id": "B", "areas": {"nombre": "Ventas"}},
        ],
        "solicitudes_ausencia": [
            {"dias": 11, "justificada": True, "fecha_desde": "2026-03-05", "empleados": {"area_id": "A", "areas": {"nombre": "Tec"}}},
            {"dias": 4, "justificada": False, "fecha_desde": "2026-03-06", "empleados": {"area_id": "A", "areas": {"nombre": "Tec"}}},
            {"dias": 2, "justificada": False, "fecha_desde": "2026-03-07", "empleados": {"area_id": "B", "areas": {"nombre": "Ventas"}}},
        ],
    })


def test_ausentismo_metricas_y_tasa(monkeypatch):
    monkeypatch.setattr(aus, "supabase_admin", _aus_db())
    r = aus.generate_ausentismo(3, 2026, empresa_id=None, area_id=None, vista="ambos")
    por = {f["area"]: f for f in r["ausentismo"]}
    assert por["Tec"]["dias_totales"] == 15 and por["Tec"]["dias_injustificados"] == 4
    assert por["Tec"]["tasa_total_pct"] == round(15 / 22 * 100, 2)          # headcount Tec = 1 → base 22
    assert por["Tec"]["tasa_injustificada_pct"] == round(4 / 22 * 100, 2)
    assert por["Ventas"]["dias_totales"] == 2 and por["Ventas"]["dias_injustificados"] == 2
    assert "22 días hábiles" in r["nota"]


def test_ausentismo_filtro_area_excluye_otra(monkeypatch):
    monkeypatch.setattr(aus, "supabase_admin", _aus_db())
    r = aus.generate_ausentismo(3, 2026, empresa_id=None, area_id="A", vista="ambos")
    assert {f["area"] for f in r["ausentismo"]} == {"Tec"}                  # Ventas excluida por el join


def test_ausentismo_vista_injustificado_solo_esa_columna(monkeypatch):
    monkeypatch.setattr(aus, "supabase_admin", _aus_db())
    r = aus.generate_ausentismo(3, 2026, empresa_id=None, area_id=None, vista="injustificado")
    fila = r["ausentismo"][0]
    assert "dias_injustificados" in fila and "tasa_injustificada_pct" in fila
    assert "dias_totales" not in fila and "tasa_total_pct" not in fila


# ── R9 listado combinado ────────────────────────────────────────────────────────

def test_listado_trae_vacaciones_y_ausencias(monkeypatch):
    monkeypatch.setattr(vac, "supabase_admin", _FakeDB({
        "solicitudes_vacaciones": [
            {"fecha_desde": "2026-03-05", "fecha_hasta": "2026-03-10", "dias": 5, "tipo": "ordinaria",
             "cancelada": False, "empleados": {"nombre": "Ana", "apellido": "G", "area_id": "A", "areas": {"nombre": "Tec"}}},
        ],
        "solicitudes_ausencia": [
            {"fecha_desde": "2026-03-12", "fecha_hasta": "2026-03-12", "dias": 1, "justificada": False,
             "motivo": "trámite", "tipos_ausencia": {"nombre": "Personal"},
             "empleados": {"nombre": "Beto", "apellido": "R", "area_id": "A", "areas": {"nombre": "Tec"}}},
        ],
    }))
    r = vac.generate_listado_vac_aus(3, 2026, empresa_id=None, area_id=None)
    assert r["total_vacaciones"] == 1 and r["total_ausencias"] == 1
    v0 = r["vacaciones"][0]
    assert v0["tipo"] == "ordinaria" and v0["cancelada"] == "No" and v0["fecha_desde"] == "05/03/2026"
    a0 = r["ausencias"][0]
    assert a0["tipo"] == "Personal" and a0["justificada"] == "No" and a0["motivo"] == "trámite"


def test_listado_empty_state_coherente(monkeypatch):
    monkeypatch.setattr(vac, "supabase_admin", _FakeDB({}))
    r = vac.generate_listado_vac_aus(3, 2026, empresa_id=None, area_id=None)
    assert r["total_vacaciones"] == 0 and r["total_ausencias"] == 0
    assert r["vacaciones"] == [] and r["ausencias"] == []


# ── Router: empresa/vista del BODY, no del header ───────────────────────────────

async def test_router_pasa_vista_y_empresa_del_body():
    captured: dict = {}

    class _Svc:
        def generar(self, **kw):
            captured.update(kw)
            return SimpleNamespace(id="r1")

    req = SimpleNamespace(state=SimpleNamespace(user={"email": "u@x.com"}, empresa_id="HEADER-EMP"))
    body = ReporteGenerarRequest(tipo="ausentismo", mes=3, anio=2026,
                                 empresa_id="11111111-1111-1111-1111-111111111111",
                                 area_id="22222222-2222-2222-2222-222222222222", vista="injustificado")
    await generar_reporte(req, body, _Svc())
    assert captured["vista"] == "injustificado"
    assert str(captured["empresa_id"]) == "11111111-1111-1111-1111-111111111111"  # del body
    assert "HEADER-EMP" not in {str(v) for v in captured.values()}                # nunca el header


def test_schema_acepta_los_3_reportes_vac_aus():
    for t in ("saldos_vacaciones", "ausentismo", "listado_vac_aus"):
        assert ReporteGenerarRequest(tipo=t).tipo == t
    assert ReporteGenerarRequest(tipo="ausentismo", vista="total").vista == "total"
