"""
Los mappers de `ev_*` CON FILAS: `_ev_instancias_row.enrich_rows` / `.resultados` y
`_ev_plantillas_row.enrich`. Molde: `test_ausencia_row.py`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS NO PUEDAN FALLAR?

**Que las listas estuvieran vacías.** `enrich_rows` y `enrich` abren con `if not rows: return []`,
así que con `[]` no se ejecuta un solo lookup ni un solo `model_validate`. Medido instrumentando
la suite el 9/8/2026: los tres se llamaban **siempre con listas vacías**.
(`resultados` es la excepción: no tiene early-return —es un `sorted([...])` sobre una
comprensión—, así que con `[]` sí "corre", pero sin ejecutar el cuerpo de la comprensión. El
efecto práctico es el mismo y por eso está acá.)

## ⚠️ ESTE MÓDULO ESTÁ CONGELADO — los tests FIJAN el comportamiento, no lo corrigen

`ev_ciclos` / `ev_plantillas` / `ev_instancias` tienen sus routers montados y sus tablas **vacías
en producción**; el módulo se limpia en el cutover a AWS. Por eso `test_pendiente_conocido_*` de
abajo **documenta un bug real y NO lo arregla**: cuando se decida arreglarlo, ese test tiene que
ROMPERSE y moverse al que verifique lo contrario — no borrarse.

## Por qué varias filas con valores distintos

Con una sola fila, un mapper que emitiera constantes o leyera siempre el primer resultado de cada
lookup pasaría igual. Acá hay instancias de **2 empresas**, con y sin evaluador, con y sin área, y
plantillas con y sin `area_id`. Cada aserción compara el contenido de SU fila.
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

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories._ev_instancias_row as inst_mod  # noqa: E402
import repositories._ev_plantillas_row as plant_mod  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

E1, E2 = str(uuid4()), str(uuid4())
C1 = str(uuid4())
P1, P2, V1 = str(uuid4()), str(uuid4()), str(uuid4())
PL1, PL2, A1 = str(uuid4()), str(uuid4()), str(uuid4())
K1, K2 = str(uuid4()), str(uuid4())
I1, I2 = str(uuid4()), str(uuid4())

_CATALOGO = {
    "empresas": [{"id": E1, "nombre": "Karstec"}, {"id": E2, "nombre": "Dosuba"}],
    "empleados": [{"id": P1, "nombre": "Ana", "apellido": "Pérez", "areas": {"nombre": "Sistemas"}},
                  {"id": P2, "nombre": "Luis", "apellido": "Gómez", "areas": None},
                  {"id": V1, "nombre": "Eva", "apellido": "Luna"}],
    "ev_ciclos": [{"id": C1, "nombre": "Ciclo 2026", "plantilla_id": PL1}],
    "areas": [{"id": A1, "nombre": "Sistemas"}],
}

# I1: con evaluador y con área. I2: SIN evaluador y SIN área, y de otra empresa.
_INSTANCIAS = [
    {"id": I1, "empresa_id": E1, "ciclo_id": C1, "empleado_id": P1, "evaluador_id": V1,
     "estado": "pendiente", "puntaje_global": None, "fecha_evaluacion": None},
    {"id": I2, "empresa_id": E2, "ciclo_id": C1, "empleado_id": P2, "evaluador_id": None,
     "estado": "cerrada", "puntaje_global": 4.5, "fecha_evaluacion": None},
]


@pytest.fixture
def base_inst(monkeypatch) -> FakeSupabase:
    fake = FakeSupabase(_CATALOGO)
    monkeypatch.setattr(inst_mod, "supabase_admin", fake)
    return fake


@pytest.fixture
def base_plant(monkeypatch) -> FakeSupabase:
    fake = FakeSupabase(_CATALOGO)
    monkeypatch.setattr(plant_mod, "supabase_admin", fake)
    return fake


def _filas() -> list:
    """Copias frescas: `enrich_rows` MUTA las filas que recibe (les mete `_emp`, `_ciclo`, …)."""
    return [dict(r) for r in _INSTANCIAS]


# ── _ev_instancias_row.enrich_rows ────────────────────────────────────────────

class TestEnrichRowsConFilas:

    def test_devuelve_una_respuesta_por_fila_sin_reventar(self, base_inst) -> None:
        assert [str(i.id) for i in inst_mod.enrich_rows(_filas())] == [I1, I2]

    def test_resuelve_empleado_ciclo_y_area_de_CADA_fila(self, base_inst) -> None:
        a, b = inst_mod.enrich_rows(_filas())
        assert (a.empleado_nombre, a.empleado_area) == ("Ana Pérez", "Sistemas")
        assert a.ciclo_nombre == "Ciclo 2026"
        # El empleado sin área no hereda la del anterior.
        assert (b.empleado_nombre, b.empleado_area) == ("Luis Gómez", None)

    def test_el_evaluador_solo_donde_lo_hay(self, base_inst) -> None:
        """El campo opcional en null: I2 no tiene evaluador y tiene que salir None, no ''."""
        a, b = inst_mod.enrich_rows(_filas())
        assert a.evaluador_nombre == "Eva Luna"
        assert b.evaluador_nombre is None

    def test_los_lookups_son_batch(self, base_inst) -> None:
        """Cuatro dimensiones: empleados (×2, una para evaluados y otra para evaluadores),
        ciclos y empresas. Nunca uno por fila."""
        inst_mod.enrich_rows(_filas())
        assert sorted(t for t, _, _ in base_inst.consultas) == \
               ["empleados", "empleados", "empresas", "ev_ciclos"]

    def test_pendiente_conocido_empresa_nombre_siempre_sale_None(self, base_inst) -> None:
        """🔴 BUG REAL, FIJADO Y NO ARREGLADO — módulo congelado (ver el encabezado).

        `enrich_rows` consulta `empresas` con `select("id,nombre")` y después arma el mapa con
        `e.get("empresa_nombre")` — una clave que la fila NO tiene. El resultado es que
        `empresa_nombre` sale **None para toda instancia**, siempre: la query se hace, los datos
        vuelven, y se descartan leyendo la clave equivocada. Es la misma familia que el `_TA` de
        `_ausencia_row`: código que nunca se ejecutó bajo test.

        No falla hoy porque `ev_instancias` tiene 0 filas en producción. Cuando se arregle (o se
        borre el módulo en el cutover), este test tiene que ROMPERSE y moverse al que verifique
        que el nombre se resuelve — no borrarse.
        """
        a, b = inst_mod.enrich_rows(_filas())
        assert (a.empresa_nombre, b.empresa_nombre) == (None, None), \
            "¿Se arregló el mapa de empresas? Mové este test al que verifica lo contrario."
        # La evidencia de que el dato SÍ estaba disponible: la consulta se hizo y trajo los nombres.
        assert [t for t, _, _ in base_inst.consultas].count("empresas") == 1


# ── _ev_instancias_row.resultados ─────────────────────────────────────────────

class TestResultadosConFilas:
    """⚠️ Sin early-return: es un `sorted([...])` sobre una comprensión. Igual estaba sin
    ejercitar, y el orden es lógica de verdad —lo pone el criterio, no la fila—."""

    def _raw(self) -> list:
        return [
            {"id": str(uuid4()), "criterio_id": K2,
             "ev_criterios": {"nombre": "Trabajo en equipo", "peso": 2, "orden": 2}, "puntaje": 4},
            {"id": str(uuid4()), "criterio_id": K1,
             "ev_criterios": {"nombre": "Comunicación", "peso": 1, "orden": 1}, "puntaje": 5},
        ]

    def test_ordena_por_el_orden_del_criterio_no_por_la_fila(self) -> None:
        """Las filas llegan 2,1 y tienen que salir 1,2. Con una sola fila el sort no prueba nada."""
        salida = inst_mod.resultados(self._raw())
        assert [r.criterio_orden for r in salida] == [1, 2]
        assert [r.criterio_nombre for r in salida] == ["Comunicación", "Trabajo en equipo"]
        assert [r.criterio_peso for r in salida] == [1.0, 2.0]

    def test_sin_criterio_embebido_cae_a_los_defaults(self) -> None:
        """El campo opcional en null: `ev_criterios` puede venir None y no puede reventar."""
        salida = inst_mod.resultados([{"id": str(uuid4()), "criterio_id": K1,
                                       "ev_criterios": None, "puntaje": None}])
        assert (salida[0].criterio_nombre, salida[0].criterio_peso, salida[0].criterio_orden) == \
               ("", 1.0, 1)

    def test_lista_vacia_da_lista_vacia(self) -> None:
        assert inst_mod.resultados([]) == []


# ── _ev_plantillas_row.enrich ─────────────────────────────────────────────────

class TestPlantillasEnrichConFilas:

    def _filas(self) -> list:
        return [
            {"id": PL1, "empresa_id": E1, "nombre": "Perfil líder", "tipo_escala": "numerica",
             "area_id": A1, "descripcion": None, "escala_min": 1, "escala_max": 5,
             "opciones_cualitativas": None, "activa": True, "created_at": None,
             # A propósito desordenados: el mapper tiene que ordenarlos por `orden`.
             "ev_criterios": [
                 {"id": K2, "plantilla_id": PL1, "empresa_id": E1, "nombre": "Segundo",
                  "peso": 2, "orden": 2},
                 {"id": K1, "plantilla_id": PL1, "empresa_id": E1, "nombre": "Primero",
                  "peso": 1, "orden": 1}]},
            {"id": PL2, "empresa_id": E2, "nombre": "General", "tipo_escala": "cualitativa",
             "area_id": None, "descripcion": None, "escala_min": None, "escala_max": None,
             "opciones_cualitativas": None, "activa": True, "created_at": None},
        ]

    def test_resuelve_empresa_y_area_de_CADA_fila(self, base_plant) -> None:
        a, b = plant_mod.enrich(self._filas())
        assert (a.empresa_nombre, a.area_nombre) == ("Karstec", "Sistemas")
        # El campo opcional en null: sin área, `area_nombre` es None y no hereda el anterior.
        assert (b.empresa_nombre, b.area_id, b.area_nombre) == ("Dosuba", None, None)

    def test_los_criterios_salen_ordenados(self, base_plant) -> None:
        a, b = plant_mod.enrich(self._filas())
        assert [c.nombre for c in a.criterios] == ["Primero", "Segundo"]
        assert b.criterios == []

    def test_sin_plantillas_por_area_no_consulta_areas(self, base_plant) -> None:
        """La rama `if area_ids`: el módulo lo declara en su docstring."""
        plant_mod.enrich([self._filas()[1]])
        assert "areas" not in [t for t, _, _ in base_plant.consultas]


# ── las guardas ───────────────────────────────────────────────────────────────

def test_la_lista_vacia_no_prueba_nada(base_inst, base_plant) -> None:
    """🔴 POR QUÉ ESTOS CUERPOS ESTUVIERON SIN PROBAR: con `[]` no se ejecuta ni una línea."""
    assert inst_mod.enrich_rows([]) == []
    assert plant_mod.enrich([]) == []
    assert base_inst.consultas == [] and base_plant.consultas == [], \
        "con lista vacía no consultan nada: no prueban nada"


def test_los_corto_circuitos_siguen_en_la_primera_linea() -> None:
    """Si se movieran, la guarda de arriba dejaría de significar lo que dice."""
    assert guarda_de(inst_mod.enrich_rows) == "rows"
    assert guarda_de(plant_mod.enrich) == "rows"
    assert guarda_de(inst_mod.resultados) is None, \
        "`resultados` ganó un early-return: sumalo a la guarda de arriba"
