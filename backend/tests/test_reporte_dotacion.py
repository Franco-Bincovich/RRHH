"""
Tests de los generadores de la tanda Dotación con datos SINTÉTICOS (los reales están vacíos):
headcount, rotación (0 egresos), altas/bajas (listado nominal + empty state) y distribución
(agrupación + 'Sin especificar'). Sin red: fake de supabase que resuelve por (tabla, columna gte).
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

import services.reportes._reporte_distribucion as dist
import services.reportes._reporte_dotacion as dot
import services.reportes._reporte_movimientos as mov


class _Q:
    """Query fake encadenable; execute() resuelve por (tabla, última columna .gte)."""
    def __init__(self, table, resolver):
        self._t, self._r, self._gte = table, resolver, None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, col, _v):
        self._gte = col
        return self

    def lte(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        data = self._r(self._t, self._gte)
        return SimpleNamespace(data=data, count=len(data))


class _FakeSupa:
    def __init__(self, resolver):
        self._r = resolver

    def table(self, name):
        return _Q(name, self._r)


def test_headcount_total_y_por_area(monkeypatch):
    def resolver(table, gte):
        if table == "empleados" and gte == "fecha_ingreso":
            return [{"id": 1}]                                   # 1 ingreso
        if table == "empleados" and gte == "updated_at":
            return []                                            # 0 bajas
        if table == "empleados":
            return [{"area_id": "a1"}, {"area_id": "a1"}, {"area_id": "a2"}]  # 3 activos
        if table == "areas":
            return [{"id": "a1", "nombre": "Tec"}, {"id": "a2", "nombre": "Ventas"}]
        return []
    monkeypatch.setattr(dot, "supabase_admin", _FakeSupa(resolver))
    r = dot.generate_headcount(3, 2026)
    assert r["total_empleados"] == 3 and r["ingresos_periodo"] == 1 and r["bajas_periodo"] == 0
    assert r["variacion_neta"] == 1
    assert {x["nombre"]: x["total"] for x in r["por_area"]} == {"Tec": 2, "Ventas": 1}


def test_rotacion_con_cero_egresos_no_rompe(monkeypatch):
    def resolver(table, gte):
        if table == "empleados" and gte == "fecha_ingreso":
            return [{"id": 1}, {"id": 2}]
        if table == "empleados":
            return [{"id": i} for i in range(19)]                # 19 activos
        if table == "offboarding_instancias":
            return []                                            # 0 bajas
        return []
    monkeypatch.setattr(dot, "supabase_admin", _FakeSupa(resolver))
    r = dot.generate_rotacion(3, 2026)
    assert r["bajas_periodo"] == 0 and r["tasa_rotacion_pct"] == 0.0 and r["motivos_egreso"] == {}
    assert r["empleados_activos"] == 19 and r["ingresos_periodo"] == 2


def test_altas_bajas_listado_nominal(monkeypatch):
    def resolver(_table, gte):
        if gte == "fecha_ingreso":
            return [{"nombre": "Ana", "apellido": "García", "fecha_ingreso": "2026-03-05",
                     "areas": {"nombre": "Tec"}}]
        if gte == "fecha_egreso":
            return [{"nombre": "Beto", "apellido": "Ruiz", "fecha_egreso": "2026-03-20",
                     "motivo_baja": "renuncia", "areas": {"nombre": "Ventas"}}]
        return []
    monkeypatch.setattr(mov, "supabase_admin", _FakeSupa(resolver))
    r = mov.generate_altas_bajas(3, 2026)
    assert r["total_altas"] == 1 and r["total_bajas"] == 1
    assert r["altas"][0] == {"empleado": "García, Ana", "area": "Tec", "fecha_ingreso": "2026-03-05"}
    assert r["bajas"][0] == {"empleado": "Ruiz, Beto", "area": "Ventas",
                             "fecha_egreso": "2026-03-20", "motivo": "renuncia"}


def test_altas_bajas_sin_bajas_empty_state(monkeypatch):
    def resolver(_table, gte):
        if gte == "fecha_ingreso":
            return [{"nombre": "Ana", "apellido": "García", "fecha_ingreso": "2026-03-05",
                     "areas": {"nombre": "Tec"}}]
        return []  # bajas vacías
    monkeypatch.setattr(mov, "supabase_admin", _FakeSupa(resolver))
    r = mov.generate_altas_bajas(3, 2026)
    assert r["total_altas"] == 1
    assert r["total_bajas"] == 0 and r["bajas"] == []  # vacío coherente, no error


def test_distribucion_agrupa_y_nulos_van_a_sin_especificar(monkeypatch):
    # `por_modalidad` sale de `tipo_contrato`, NO de la ex `modalidad_contratacion` (mig. 084):
    # esa columna no la escribía nadie, así que el reporte mostraba "Sin especificar" para toda
    # la plantilla teniendo el dato al lado. Si el generador volviera a leerla, estas filas no
    # tendrían la clave y todo caería en "Sin especificar" → este test falla.
    def resolver(_table, _gte):
        return [
            {"seniority": "Senior", "tipo_contrato": "efectivo", "turno": "mañana"},
            {"seniority": "Senior", "tipo_contrato": None, "turno": None},
            {"seniority": None, "tipo_contrato": "efectivo", "turno": "tarde"},
        ]
    monkeypatch.setattr(dist, "supabase_admin", _FakeSupa(resolver))
    r = dist.generate_distribucion(None)
    assert r["total_empleados"] == 3
    assert {x["categoria"]: x["total"] for x in r["por_seniority"]} == {"Senior": 2, "Sin especificar": 1}
    assert {x["categoria"]: x["total"] for x in r["por_modalidad"]} == {"efectivo": 2, "Sin especificar": 1}
    assert {x["categoria"]: x["total"] for x in r["por_turno"]} == {"mañana": 1, "tarde": 1, "Sin especificar": 1}
    assert r["por_seniority"][-1]["categoria"] == "Sin especificar"  # siempre al final
