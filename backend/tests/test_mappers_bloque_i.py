"""
Los dos mappers que van a tener datos **en el bloque I**, cuando RRHH cargue vacaciones, ausencias
e inventario de prueba. Molde: `test_ausencia_row.py`.

| Mapper | Tabla | Filas hoy |
|---|---|---|
| `_vacaciones_utils.enriquecer`        | `solicitudes_vacaciones`  | 0 |
| `_inventario_asignacion_row.build` | `inventario_asignaciones` | 0 |

## 🔴 POR QUÉ SE CUBREN AHORA Y NO CUANDO HAYA DATOS

Porque **esa es exactamente la situación en la que estaba `_ausencia_row` cuando se le encontró el
`NameError`**: tabla en 0, cuerpo nunca ejecutado, y una bomba con la mecha puesta en "el día que
carguen el histórico". Esperar a que haya datos significa que el primer usuario que abra la
pantalla es el que descubre el bug.

`_vacaciones_utils.enriquecer` es el caso más parecido de todos: mismo dominio, misma forma
(empresa + empleado + área por lookups batch) y misma tabla vacía. Es el hermano directo del que
falló.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS NO PUEDAN FALLAR?

**Que las listas estuvieran vacías.** Los dos abren con `if not rows: return []`. Cada bloque
tiene su `test_la_lista_vacia_no_prueba_nada` y el anclaje del early-return por AST.

⚠️ `enriquecer` devuelve **dicts**, no schemas: es la capa previa a `build_responses`. Las
aserciones van sobre las claves del dict, que es lo que el módulo realmente produce.
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

import repositories._vacaciones_utils as vac_mod  # noqa: E402
import repositories._inventario_asignacion_row as inv_mod  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

E1, E2 = str(uuid4()), str(uuid4())
P1, P2, P3 = str(uuid4()), str(uuid4()), str(uuid4())
A1, A2 = str(uuid4()), str(uuid4())
IT1, IT2 = str(uuid4()), str(uuid4())

_CATALOGO = {
    "empresas": [{"id": E1, "nombre": "Karstec"}, {"id": E2, "nombre": "Dosuba"}],
    # P3 SIN área: el campo opcional en null.
    "empleados": [{"id": P1, "nombre": "Ana", "apellido": "Pérez", "area_id": A1},
                  {"id": P2, "nombre": "Luis", "apellido": "Gómez", "area_id": A2},
                  {"id": P3, "nombre": "Eva", "apellido": "Luna", "area_id": None}],
    "areas": [{"id": A1, "nombre": "Sistemas"}, {"id": A2, "nombre": "Salud"}],
    # IT2 sin número de serie: el otro opcional en null.
    "inventario_items": [
        {"id": IT1, "nombre": "Notebook", "tipo": "equipo", "numero_serie": "NB-001"},
        {"id": IT2, "nombre": "Monitor", "tipo": "equipo", "numero_serie": None}],
}


# ── 1. _vacaciones_utils.enriquecer ───────────────────────────────────────────

class TestVacacionesEnriquecer:
    """El hermano directo de `_ausencia_row`: mismo dominio, misma forma, misma tabla en 0."""

    @pytest.fixture
    def base(self, monkeypatch) -> FakeSupabase:
        fake = FakeSupabase(dict(_CATALOGO))
        monkeypatch.setattr(vac_mod, "supabase_admin", fake)
        return fake

    def _filas(self) -> list:
        base = {"fecha_desde": "2026-03-01", "fecha_hasta": "2026-03-10", "dias": 10,
                "cancelada": False, "created_at": "2026-02-01T00:00:00+00:00"}
        return [
            {**base, "id": str(uuid4()), "empleado_id": P1, "empresa_id": E1, "tipo": "vacaciones"},
            {**base, "id": str(uuid4()), "empleado_id": P2, "empresa_id": E2, "tipo": "licencia"},
            {**base, "id": str(uuid4()), "empleado_id": P3, "empresa_id": E1, "tipo": "vacaciones"},
        ]

    def test_resuelve_los_cuatro_derivados_de_CADA_fila(self, base) -> None:
        """Tres empleados de dos empresas y dos áreas: un mapper que copiara el primer resultado
        de cada lookup para todas las filas rojearía acá."""
        a, b, c = vac_mod.enriquecer(self._filas())
        assert (a["empresa_nombre"], a["empleado_nombre"], a["area_nombre"]) == \
               ("Karstec", "Ana Pérez", "Sistemas")
        assert (b["empresa_nombre"], b["empleado_nombre"], b["area_nombre"]) == \
               ("Dosuba", "Luis Gómez", "Salud")
        assert c["empresa_nombre"] == "Karstec"

    def test_el_empleado_sin_area_no_hereda_la_del_anterior(self, base) -> None:
        """El opcional en null. Es el modo de falla de un mapper con estado entre iteraciones."""
        _, _, c = vac_mod.enriquecer(self._filas())
        assert (c["area_id"], c["area_nombre"]) == (None, None)
        assert c["empleado_nombre"] == "Eva Luna"

    def test_conserva_las_columnas_originales_de_la_fila(self, base) -> None:
        """`enriquecer` AGREGA derivados, no reemplaza la fila: `build_responses` necesita el
        resto de las columnas para armar el response."""
        a = vac_mod.enriquecer(self._filas())[0]
        assert (a["tipo"], a["dias"], a["cancelada"]) == ("vacaciones", 10, False)

    def test_los_lookups_son_batch_no_uno_por_fila(self, base) -> None:
        """Con 3 filas: empresas, empleados y áreas. Tres consultas, no nueve."""
        vac_mod.enriquecer(self._filas())
        assert sorted(t for t, _, _ in base.consultas) == ["areas", "empleados", "empresas"]

    def test_sin_nadie_con_area_no_consulta_areas(self, base) -> None:
        """La rama `if area_ids:`. Con todos sin área, esa query ni se emite."""
        solo_sin_area = [f for f in self._filas() if f["empleado_id"] == P3]
        vac_mod.enriquecer(solo_sin_area)
        assert "areas" not in [t for t, _, _ in base.consultas]

    def test_la_lista_vacia_no_prueba_nada(self, base) -> None:
        assert vac_mod.enriquecer([]) == []
        assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"

    def test_el_corto_circuito_sigue_en_la_primera_linea(self) -> None:
        assert guarda_de(vac_mod.enriquecer) == "rows"


# ── 2. inventario_asignaciones_repo._build ────────────────────────────────────

class TestInventarioAsignacionesBuild:
    """El hermano de `_inventario_items_row._build`, que SÍ estaba cubierto."""

    @pytest.fixture
    def base(self, monkeypatch) -> FakeSupabase:
        fake = FakeSupabase(dict(_CATALOGO))
        monkeypatch.setattr(inv_mod, "supabase_admin", fake)
        return fake

    def _filas(self) -> list:
        return [
            {"id": str(uuid4()), "item_id": IT1, "empleado_id": P1, "empresa_id": E1,
             "fecha_asignacion": "2026-01-15", "fecha_devolucion": None,
             "observaciones": "Entregada en mano", "created_at": "2026-01-15T00:00:00+00:00"},
            # Devuelta, de otra empresa, con un ítem SIN número de serie.
            {"id": str(uuid4()), "item_id": IT2, "empleado_id": P2, "empresa_id": E2,
             "fecha_asignacion": "2026-02-01", "fecha_devolucion": "2026-03-01",
             "observaciones": None, "created_at": "2026-02-01T00:00:00+00:00"},
        ]

    def test_resuelve_item_empleado_y_empresa_de_CADA_fila(self, base) -> None:
        a, b = inv_mod.build(self._filas())
        assert (a.item_nombre, a.item_tipo, a.item_numero_serie) == \
               ("Notebook", "equipo", "NB-001")
        assert (a.empleado_nombre, a.empresa_nombre) == ("Ana Pérez", "Karstec")
        assert (b.item_nombre, b.empleado_nombre, b.empresa_nombre) == \
               ("Monitor", "Luis Gómez", "Dosuba")

    def test_un_item_sin_numero_de_serie_da_None_no_el_del_anterior(self, base) -> None:
        """El opcional en null, y la trampa: los tres campos del ítem salen del MISMO lookup."""
        _, b = inv_mod.build(self._filas())
        assert b.item_numero_serie is None
        assert b.item_tipo == "equipo"

    def test_un_item_desconocido_no_revienta(self, base) -> None:
        """El `.get(..., {}).get(...)` del módulo: un ítem borrado deja los campos en None."""
        fila = {**self._filas()[0], "item_id": str(uuid4())}
        salida = inv_mod.build([fila])[0]
        assert (salida.item_nombre, salida.item_tipo, salida.item_numero_serie) == \
               (None, None, None)

    def test_los_lookups_son_batch(self, base) -> None:
        """Tres dimensiones: empresas, ítems y empleados. Nunca uno por fila."""
        inv_mod.build(self._filas())
        assert sorted(t for t, _, _ in base.consultas) == \
               ["empleados", "empresas", "inventario_items"]

    def test_la_lista_vacia_no_prueba_nada(self, base) -> None:
        assert inv_mod.build([]) == []
        assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"

    def test_el_corto_circuito_sigue_en_la_primera_linea(self) -> None:
        assert guarda_de(inv_mod.build) == "rows"
