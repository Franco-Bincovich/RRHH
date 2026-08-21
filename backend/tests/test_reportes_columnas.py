"""
🔴 Los nombres de columna y los embeds de TODOS los reportes y KPIs, contra el schema real.

POR QUÉ ESTE TEST. Seis de los once reportes de Fase 1 se entregaron como completos y nunca
funcionaron en producción: pedían columnas que no existen (`motivo` por `motivo_egreso`,
`progreso` en una tabla que no la tiene) o embeds ambiguos que PostgREST rechaza con PGRST201.
Los 799 tests pasaban, porque el fake de Supabase implementa `select(*a, **k)` ignorando el
argumento — acepta cualquier spec.

Arreglar las siete instancias no cerraba nada: el próximo reporte nace con el mismo agujero.
Lo que cierra la clase es ESTE test, que ejecuta cada generador contra un fake que SÍ valida el
spec contra `db/schema.sql` (ver tests/_postgrest_schema.py). Es el mismo movimiento que
TestTodosLosExportsChequean en B7: barrer la superficie entera, no tapar el caso.

CADA GENERADOR CORRE DOS VECES, con y sin `area_id`. No es redundancia: el filtro de área
cambia el spec (arma joins `!inner` y embeds distintos con f-strings), así que una sola pasada
deja la mitad de las queries sin mirar. El bug de ausentismo vivía justo ahí.
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

import importlib
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests._postgrest_schema import SelectInvalidoError, cargar_schema

SCHEMA = cargar_schema()

# Módulos con acceso directo a Supabase que hay que interceptar. `supabase_admin` se importa
# al namespace de cada módulo, así que el parche va módulo por módulo — no en el cliente.
# `_reporte_auditoria` no aparece porque no toca Supabase directo: va por AuditRepo, y por eso
# el que se parchea es el repo.
MODULOS = [
    "repositories.audit_repo",
    # Desde la migración 085 el ausentismo lee su base de días hábiles de parametros_empresa,
    # así que este repo también toca Supabase durante un generador y su select entra al barrido.
    "repositories.configuracion_repo",
    "services.reportes._reporte_ausentismo",
    "services.reportes._reporte_capacitacion",
    "services.reportes._reporte_costos",
    "services.reportes._reporte_distribucion",
    "services.reportes._reporte_dotacion",
    "services.reportes._reporte_movimientos",
    "services.reportes._reporte_seleccion",
    # R11 se mudó de _reporte_vacaciones a _reporte_saldos al pasar a calcularse con el núcleo
    # compartido. La entrada NUEVA no es opcional: sin ella el generador quedaba hablando con la
    # base REAL durante el test (el fallo fue un getaddrinfo, no una aserción) y sus tres selects
    # —empleados, solicitudes y pendientes— no los validaba nadie.
    "services.reportes._reporte_saldos",
    "services.reportes._reporte_vacaciones",
    "services._dashboard_headcount",
    "services._dashboard_kpis",
    # 🔴 Los cuatro KPIs que faltaban de §6 (21/8/2026). `calcular_extras` dejó de tener todas
    # sus queries adentro: cada KPI nuevo vive en su módulo y trae su propio `supabase_admin`,
    # así que sin estas entradas `TestKPIsNoSeTraganElError` los ve fallar contra la base real
    # y —peor— sus selects no los validaría nadie contra `db/schema.sql`.
    "services._dashboard_antiguedad",
    "services._dashboard_atencion_calculadas",
    "services._dashboard_operacion",
    # Las recategorizaciones del mes no tienen query propia: van por su repo, que además resuelve
    # los tres nombres en otro módulo. Los dos entran, por la misma razón que `audit_repo`.
    "repositories._recategorizacion_row",
    "repositories.recategorizacion_repo",
]

MES, ANIO = 7, 2026


def _generadores():
    """(id, callable) por generador, en las dos variantes: consolidado y con área."""
    import services.reporte_generators as g
    from services._dashboard_headcount import calcular_headcount
    from services._dashboard_kpis import calcular_extras

    eid, aid = uuid4(), uuid4()
    con_periodo = [
        ("ausentismo", g.generate_ausentismo), ("auditoria", g.generate_auditoria),
        ("capacitacion", g.generate_capacitacion), ("costos", g.generate_costos),
        ("headcount", g.generate_headcount), ("rotacion", g.generate_rotacion),
        ("altas_bajas", g.generate_altas_bajas), ("presupuesto", g.generate_presupuesto),
        ("saldos_vacaciones", g.generate_saldos_vacaciones),
        ("listado_vac_aus", g.generate_listado_vac_aus),
    ]
    casos = []
    for nombre, fn in con_periodo:
        casos.append((f"{nombre}:consolidado", lambda f=fn: f(MES, ANIO, None, None)))
        casos.append((f"{nombre}:con_area", lambda f=fn: f(MES, ANIO, eid, aid)))
    for nombre, fn in [("vacantes", g.generate_vacantes), ("onboarding", g.generate_onboarding)]:
        casos.append((f"{nombre}:consolidado", lambda f=fn: f(None, None)))
        casos.append((f"{nombre}:con_area", lambda f=fn: f(eid, aid)))
    casos.append(("distribucion:consolidado", lambda: g.generate_distribucion(None, None)))
    casos.append(("distribucion:con_area", lambda: g.generate_distribucion(eid, aid)))
    casos.append(("kpis_extra", lambda: calcular_extras(date(ANIO, MES, 15), eid)))
    casos.append(("kpi_headcount", lambda: calcular_headcount(eid)))
    return casos


# Única tabla que el fake NO devuelve vacía, y por un motivo distinto al resto: la fila de
# parametros_empresa no es un dato REPORTADO, es una PRECONDICIÓN del cálculo — sin ella el
# generador de ausentismo no puede correr y el barrido moriría con un error de configuración
# en vez de decir algo sobre los nombres de columnas, que es lo que vino a verificar.
# Los valores son los que siembra la migración 085.
_PRECONDICIONES = {
    "parametros_empresa": {
        "base_dias_habiles": 22, "corte_antiguedad_mes": 10,
        "periodo_vacacional_desde_mes": 10, "periodo_vacacional_hasta_mes": 4,
        "primer_anio_mes_corte": 7, "primer_anio_dias": 5, "vencimiento_anios": 4,
        # Los agregó la migración 114. Van acá aunque ningún reporte los use: la fila entera
        # tiene que poder validar como `ParametrosResponse`, y si falta un campo obligatorio el
        # KPI de ausentismo muere con un error de Pydantic — que este barrido reporta como
        # "columna inexistente" y manda a buscar el bug al lado equivocado.
        "periodo_prueba_dias": 90, "dias_aviso_evento": 7,
    },
}


class _Query:
    """Query de Supabase que valida el spec y devuelve vacío. Los filtros son no-ops: acá lo
    que se verifica son los NOMBRES, que es lo único que el fake común no puede ver."""

    def __init__(self, tabla: str) -> None:
        self._tabla = tabla

    def select(self, spec: str = "*", **kwargs):
        SCHEMA.validar_select(self._tabla, spec)
        return self

    def __getattr__(self, _nombre):
        return lambda *a, **k: self

    def execute(self):
        fila = _PRECONDICIONES.get(self._tabla)
        return SimpleNamespace(data=fila if fila else [], count=0)


class _Cliente:
    def table(self, nombre: str) -> _Query:
        return _Query(nombre)


@pytest.fixture(autouse=True)
def _validar_specs(monkeypatch):
    """Parchea con `raising=True` a propósito: si un módulo de la lista dejara de importar
    `supabase_admin`, el parche fallaría ruidosamente en vez de dejar ese módulo hablando con
    la base real y el barrido cubriendo menos de lo que dice."""
    for modulo in MODULOS:
        monkeypatch.setattr(importlib.import_module(modulo), "supabase_admin", _Cliente())


# ─── El barrido ───────────────────────────────────────────────────────────────


class TestTodosLosGeneradores:
    def test_el_barrido_no_esta_vacio(self) -> None:
        """Guarda contra el falso verde: con la lista vacía todo lo de abajo pasaría sin
        haber ejecutado un solo generador."""
        assert len(_generadores()) >= 26

    @pytest.mark.parametrize("nombre,fn", _generadores(), ids=lambda v: v if isinstance(v, str) else "")
    def test_las_columnas_y_embeds_existen(self, nombre: str, fn) -> None:
        try:
            fn()
        except SelectInvalidoError as exc:
            pytest.fail(f"{nombre} → {exc}")


class TestKPIsNoSeTraganElError:
    """El dashboard atrapa el fallo de cada KPI para no caerse entero (fail-safe por KPI). Eso
    es correcto en producción y venenoso acá: un spec roto quedaría anotado en `errores` y el
    test pasaría igual. Por eso se mira `errores`, no la excepción."""

    def test_ningun_kpi_queda_marcado_como_fallido(self) -> None:
        from services._dashboard_kpis import calcular_extras
        assert calcular_extras(date(ANIO, MES, 15), uuid4()).errores == []


# ─── El validador detecta lo que tiene que detectar ───────────────────────────


class TestElValidadorSirve:
    """Un validador que no rechaza nada da verde para todo. Estos casos son los DOS bugs
    reales encontrados, escritos como estaban antes del fix."""

    def test_rechaza_columna_inexistente(self) -> None:
        """Era `motivo` en offboarding_instancias; la columna es `motivo_egreso`."""
        with pytest.raises(SelectInvalidoError, match="motivo"):
            SCHEMA.validar_select("offboarding_instancias", "motivo")

    def test_acepta_el_nombre_correcto(self) -> None:
        SCHEMA.validar_select("offboarding_instancias", "motivo_egreso")

    def test_rechaza_columna_que_es_de_otra_tabla(self) -> None:
        """Era `progreso` en onboarding_instancias, donde se calcula, no se guarda."""
        with pytest.raises(SelectInvalidoError, match="progreso"):
            SCHEMA.validar_select("onboarding_instancias", "id, progreso")

    def test_rechaza_embed_ambiguo(self) -> None:
        """`areas` desde `empleados`: dos relaciones (area_id y responsable_id) → PGRST201."""
        with pytest.raises(SelectInvalidoError, match="AMBIGUO"):
            SCHEMA.validar_select("empleados", "area_id, areas(nombre)")

    def test_acepta_el_embed_con_la_fk_nombrada(self) -> None:
        SCHEMA.validar_select("empleados", "area_id, areas!empleados_area_id_fkey(nombre)")

    def test_rechaza_una_fk_que_no_existe(self) -> None:
        with pytest.raises(SelectInvalidoError, match="no es ni una constraint"):
            SCHEMA.validar_select("empleados", "areas!fk_inventada(nombre)")

    def test_valida_tambien_adentro_del_embed(self) -> None:
        """La columna mal escrita puede estar anidada — ahí es aún más difícil de ver."""
        with pytest.raises(SelectInvalidoError, match="nombre_del_area"):
            SCHEMA.validar_select("empleados", "areas!empleados_area_id_fkey(nombre_del_area)")

    def test_un_solo_camino_no_necesita_hint(self) -> None:
        """No hay que exigir la FK siempre: `vacantes → areas` tiene un solo camino y anda."""
        SCHEMA.validar_select("vacantes", "id, titulo, areas(nombre)")

    def test_entiende_la_forma_alias_columna(self) -> None:
        """`manager:manager_id(...)` es un embed por COLUMNA, no por tabla (empleado_row)."""
        SCHEMA.validar_select("empleados", "*, manager:manager_id(nombre, apellido)")


class TestElSchemaSeParseoBien:
    """Si el parseo saliera vacío, todo lo de arriba pasaría sin validar nada."""

    def test_hay_tablas(self) -> None:
        assert len(SCHEMA.columnas) >= 40

    def test_hay_relaciones(self) -> None:
        assert len(SCHEMA.relaciones) >= 100

    def test_las_columnas_conocidas_estan(self) -> None:
        assert {"id", "empresa_id", "area_id", "manager_id"} <= SCHEMA.columnas["empleados"]

    def test_detecta_las_dos_relaciones_empleados_areas(self) -> None:
        """La ambigüedad que rompió cuatro reportes depende de encontrar ESTAS dos."""
        assert {r.constraint for r in SCHEMA.entre("empleados", "areas")} == {
            "empleados_area_id_fkey", "fk_areas_responsable",
        }
