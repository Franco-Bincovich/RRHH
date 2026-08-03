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


def test_los_literales_de_vacio_del_csv_son_UNA_categoria(monkeypatch):
    """🔴 'SIN DATOS' es lo mismo que vacío, que NULL y que '   '.

    En producción (3/8/2026) `empleados.seniority` tenía 24 filas en NULL y 4 en el literal
    'SIN DATOS', sobre 31 empleados: el 90% de la plantilla sin seniority se mostraba PARTIDO
    en dos categorías, y la card no dejaba ver que era el mismo agujero de datos. El literal no
    lo escribe nuestro código —viene en el CSV de RRHH— y entraba tal cual porque no estaba en
    la lista de textos-vacíos del import.

    Para que falle: sacar 'SIN DATOS' de `_nomina_parsers.VACIOS`, o que `_agrupar` deje de
    consultar esa lista y vuelva a chequear solo NULL/''."""
    def resolver(_table, _gte):
        return [
            {"seniority": "Senior", "tipo_contrato": None, "turno": None},
            {"seniority": "SIN DATOS", "tipo_contrato": None, "turno": None},
            {"seniority": "sin datos", "tipo_contrato": None, "turno": None},  # el case no importa
            {"seniority": None, "tipo_contrato": None, "turno": None},
            {"seniority": "   ", "tipo_contrato": None, "turno": None},
        ]
    monkeypatch.setattr(dist, "supabase_admin", _FakeSupa(resolver))
    por_seniority = {x["categoria"]: x["total"]
                     for x in dist.generate_distribucion(None)["por_seniority"]}
    assert por_seniority == {"Senior": 1, "Sin especificar": 4}
    assert "SIN DATOS" not in por_seniority


def test_el_agrupador_NO_tiene_su_propia_lista_de_vacios():
    """La lista canónica vive en `_nomina_parsers.VACIOS` y el reporte la IMPORTA.

    Es la parte que importa del fix: el import la aplica al ESCRIBIR y el reporte al LEER, pero
    la definición es UNA. Con dos copias, agregar un literal nuevo al CSV arreglaría los datos
    nuevos y dejaría el reporte contando aparte los viejos — que es exactamente el estado del
    que este fix viene a salir.

    Para que falle: copiar el set adentro de `_reporte_distribucion` en vez de importarlo.

    Se compara por IDENTIDAD (`is`), no por contenido ni por texto del módulo: dos sets con los
    mismos elementos hoy son `==` y divergen mañana sin que nada avise, y un `in
    inspect.getsource(...)` matchea también los comentarios —de hecho la primera versión de este
    test se rojeó a sí misma cazando la palabra dentro del docstring de `_agrupar`."""
    from services._nomina_parsers import VACIOS

    assert dist.VACIOS is VACIOS, "el reporte tiene su propia lista de vacíos, no la compartida"
    assert "SIN DATOS" in VACIOS and "NO APLICA" in VACIOS
