"""
Tests SINTÉTICOS de los 5 KPIs nuevos del dashboard (Sesión 5). Datos casi vacíos en prod →
esta es la verificación real. El fake de supabase aplica de verdad eq/gte/lte, así que los rangos
de fecha y el filtro de empresa se ejercitan de verdad.
- KPI 23: ausencias que cruzan hoy (fecha_desde ≤ hoy ≤ fecha_hasta).
- KPI 26: % ausentismo del mes con base 22 (reusa _tasa de R10).
- KPI 27: masa salarial mes actual vs anterior + variación %.
- KPI 28: distribución con nulos en "Sin especificar".
- KPI 30: cumpleaños/aniversarios detectados por MES de la fecha.
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

from datetime import date
from types import SimpleNamespace

import services._dashboard_kpis as dk


def _get(row: dict, col: str):
    return row.get(col)


class _Q:
    def __init__(self, rows):
        self._rows, self._eq, self._gte, self._lte = rows, {}, {}, {}

    def select(self, *a, **k):
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


_HOY = date(2026, 3, 15)


# ── KPI 23 — ausencias activas hoy ────────────────────────────────────────────────

def test_ausencias_activas_hoy_cruza(monkeypatch):
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB({
        "solicitudes_ausencia": [
            {"id": "1", "fecha_desde": "2026-03-10", "fecha_hasta": "2026-03-20"},  # cruza hoy (15)
            {"id": "2", "fecha_desde": "2026-03-01", "fecha_hasta": "2026-03-05"},  # ya terminó
            {"id": "3", "fecha_desde": "2026-03-20", "fecha_hasta": "2026-03-25"},  # todavía no empieza
        ],
    }))
    assert dk._ausencias_activas_hoy(_HOY, None) == 1


# ── KPI 26 — % ausentismo del mes (base 22) ───────────────────────────────────────

def test_ausentismo_mes_pct_base_22(monkeypatch):
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB({
        "solicitudes_ausencia": [
            {"dias": 6, "fecha_desde": "2026-03-04"},
            {"dias": 5, "fecha_desde": "2026-03-08"},
            {"dias": 3, "fecha_desde": "2026-02-27"},  # fuera del mes → no cuenta
        ],
        "empleados": [{"id": "e1", "estado": "activo"}, {"id": "e2", "estado": "activo"}],  # headcount = 2 → base 44
    }))
    # (6 + 5) / (22 * 2) * 100 = 25.0
    assert dk._ausentismo_mes_pct(2026, 3, None) == 25.0


# ── KPI 27 — masa salarial mes actual vs anterior + variación ─────────────────────

def test_masa_salarial_variacion(monkeypatch):
    # generate_costos devuelve total_nomina; parcheamos para no depender de su query interna.
    def _fake_costos(mes, anio, empresa_id=None, area_id=None):
        return {"total_nomina": 1200.0 if mes == 3 else 1000.0}

    monkeypatch.setattr(dk, "generate_costos", _fake_costos)
    monkeypatch.setattr(dk, "generate_distribucion", lambda *a, **k: {"por_seniority": [], "por_modalidad": []})
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB({}))
    r = dk.calcular_extras(_HOY, None)
    assert r.masa_salarial_actual == 1200.0 and r.masa_salarial_anterior == 1000.0
    assert r.masa_salarial_variacion_pct == 20.0  # (1200-1000)/1000*100


# ── KPI 28 — distribución con nulos en "Sin especificar" ──────────────────────────

def test_distribucion_nulos_sin_especificar(monkeypatch):
    # Reusa la lógica real de _reporte_distribucion (que agrupa nulos en "Sin especificar").
    monkeypatch.setattr(dk, "generate_costos", lambda *a, **k: {"total_nomina": 0.0})
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB({}))
    import services.reportes._reporte_distribucion as rd
    monkeypatch.setattr(rd, "supabase_admin", _FakeDB({
        "empleados": [
            {"estado": "activo", "seniority": "Senior", "modalidad_contratacion": "Full time", "turno": None},
            {"estado": "activo", "seniority": None, "modalidad_contratacion": None, "turno": None},
        ],
    }))
    r = dk.calcular_extras(_HOY, None)
    seniority = {d.categoria: d.total for d in r.distribucion_seniority}
    assert seniority.get("Senior") == 1 and seniority.get("Sin especificar") == 1


# ── KPI 30 — cumpleaños / aniversarios del mes ────────────────────────────────────

def test_cumpleanos_aniversarios_por_mes(monkeypatch):
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB({
        "empleados": [
            {"estado": "activo", "nombre": "Ana", "apellido": "G", "fecha_nacimiento": "1990-03-08", "fecha_ingreso": "2020-07-01"},
            {"estado": "activo", "nombre": "Beto", "apellido": "R", "fecha_nacimiento": "1985-11-20", "fecha_ingreso": "2019-03-15"},
        ],
    }))
    cumples, aniversarios = dk._cumple_aniversario(_HOY, None)  # hoy es marzo
    assert [c.empleado for c in cumples] == ["Ana G"] and cumples[0].fecha == "08/03"
    assert [a.empleado for a in aniversarios] == ["Beto R"] and aniversarios[0].fecha == "15/03"


# ── empresa del contexto (header) filtra ──────────────────────────────────────────

def test_ausencias_filtra_por_empresa(monkeypatch):
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB({
        "solicitudes_ausencia": [
            {"id": "1", "fecha_desde": "2026-03-10", "fecha_hasta": "2026-03-20", "empresa_id": "EMP-A"},
            {"id": "2", "fecha_desde": "2026-03-10", "fecha_hasta": "2026-03-20", "empresa_id": "EMP-B"},
        ],
    }))
    assert dk._ausencias_activas_hoy(_HOY, "EMP-A") == 1  # solo la de EMP-A
