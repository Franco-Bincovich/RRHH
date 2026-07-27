"""
Fix del dashboard caído por embed ambiguo de PostgREST + resiliencia por KPI.
- Embed: generate_costos debe nombrar la FK (empleados!costos_nomina_empleado_id_fkey), no el
  embed ambiguo `empleados(...)` que dispara PGRST201 (costos_nomina tiene 2 FKs a empleados).
- Resiliencia: si un KPI falla, calcular_extras no propaga (lo anota en `errores` y sigue); y
  get_dashboard no hace 500 global si una sección falla.
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
import services.dashboard_service as ds
import services.reportes._reporte_costos as cos
from schemas.dashboard import KPIsExtraResponse


def _boom(*a, **k):
    raise RuntimeError("PGRST201: embed ambiguo")


class _FakeDB:
    """Fake mínimo: cualquier query devuelve vacío (para los KPIs que no son el foco del test)."""
    def table(self, name):
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def lte(self, *a, **k):
        return self

    def execute(self):
        return SimpleNamespace(data=[], count=0)


# ── Fix del embed (reproduce el caso PGRST201) ────────────────────────────────────

class _SelQ:
    """Query fake que captura el string de select por tabla."""
    def __init__(self, table, caps):
        self.table, self.caps = table, caps

    def select(self, sel, *a, **k):
        self.caps[self.table] = sel
        return self

    def eq(self, *a, **k):
        return self

    def execute(self):
        return SimpleNamespace(data=[], count=0)


def test_costos_embed_nombra_la_fk_y_no_es_ambiguo(monkeypatch):
    caps: dict = {}

    class _SelDB:
        def table(self, name):
            return _SelQ(name, caps)

    monkeypatch.setattr(cos, "supabase_admin", _SelDB())

    cos.generate_costos(3, 2026, empresa_id=None, area_id=None)      # rama sin área
    assert "empleados!costos_nomina_empleado_id_fkey" in caps["costos_nomina"]
    assert "empleados(" not in caps["costos_nomina"]                 # embed ambiguo eliminado

    cos.generate_costos(3, 2026, empresa_id=None, area_id="AREA-1")  # rama !inner (con área)
    assert "empleados!costos_nomina_empleado_id_fkey!inner" in caps["costos_nomina"]


# ── Resiliencia por KPI en calcular_extras ────────────────────────────────────────

def test_calcular_extras_un_kpi_roto_no_tumba_el_resto(monkeypatch):
    monkeypatch.setattr(dk, "generate_costos", _boom)  # masa salarial revienta
    monkeypatch.setattr(dk, "generate_distribucion", lambda *a, **k: {"por_seniority": [], "por_modalidad": []})
    monkeypatch.setattr(dk, "supabase_admin", _FakeDB())
    r = dk.calcular_extras(date(2026, 3, 15), None)
    assert "masa_salarial" in r.errores                # el KPI fallido queda marcado
    assert r.masa_salarial_actual == 0.0               # y en estado vacío
    assert r.ausencias_activas_hoy == 0                # los demás se devuelven igual (sin propagar)
    assert r.ausentismo_nota                            # la respuesta es válida, no una excepción


# ── Resiliencia por sección en get_dashboard ──────────────────────────────────────

def test_get_dashboard_seccion_caida_devuelve_200_con_el_resto(monkeypatch):
    svc = ds.DashboardService()
    monkeypatch.setattr(svc, "_calcular_kpis", _boom)            # la sección de KPIs base revienta
    monkeypatch.setattr(svc, "_generar_alertas", lambda *a, **k: [])
    monkeypatch.setattr(ds, "calcular_headcount", lambda *a, **k: [])
    fake_extra = KPIsExtraResponse(
        ausencias_activas_hoy=3, ausentismo_mes_pct=0.0, ausentismo_nota="x",
        masa_salarial_actual=0.0, masa_salarial_anterior=0.0, masa_salarial_variacion_pct=0.0,
        distribucion_seniority=[], distribucion_modalidad=[], cumpleanos_mes=[], aniversarios_mes=[],
    )
    monkeypatch.setattr(ds, "calcular_extras", lambda *a, **k: fake_extra)

    resp = svc.get_dashboard(None)                              # NO debe levantar AppError/500
    assert resp.kpis.empleados_activos == 0                    # sección caída → default vacío
    assert resp.kpis_extra.ausencias_activas_hoy == 3          # las demás secciones, intactas
