"""
`_ausencia_row._build` CON FILAS. El mapper de ausencias no tenía un solo test que lo ejecutara.

## 🔴 EL BUG QUE ESTE ARCHIVO CIERRA, Y POR QUÉ NADIE LO VIO

Al dividir `ausencias_repo` (migración 088) el uso de `_TA` se mudó a este módulo y la constante
quedó atrás, en un `_T, _TA = ...`. `_TA` pasó a ser un **nombre libre**: `_build` levantaba
`NameError: name '_TA' is not defined` con cualquier lista de filas NO vacía.

Nunca falló, por dos razones que se taparon entre sí:
  · `solicitudes_ausencia` tiene **0 filas** en producción, así que el listado siempre devolvía
    `[]` y el cuerpo del mapper jamás se ejecutó;
  · la suite entera llamaba a `_build` **únicamente con listas vacías**, y `if not rows: return []`
    corta en la primera línea. Medido, no supuesto: instrumentando la suite, el largo máximo de
    lista con que se llamó a este mapper era **0**.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS NO PUEDAN FALLAR?

**Que `_FILAS` estuviera vacía.** Es literalmente todo. Con `rows=[]` el `return []` de la primera
línea se lleva puesto el resto de la función y ningún error de adentro puede aparecer — el test
pasaría igual con el bug puesto, que es exactamente lo que venía ocurriendo. Por eso todos los
tests de acá pasan filas de verdad, y `test_la_lista_vacia_no_prueba_nada` deja escrito, en
código, que el caso vacío NO cuenta como cobertura.

Lo segundo que importa: **`_q` está falseado pero DEVUELVE datos**. Un doble que devolviera `[]`
para todo dejaría los cuatro nombres en `None` y las aserciones no distinguirían "el mapper
resolvió el nombre" de "el mapper no hizo nada".
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

import pytest  # noqa: E402

import repositories._ausencia_row as row_mod  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

# Dos empleados de DOS áreas y DOS tipos distintos: con una sola fila, un mapper que asignara
# siempre el primer nombre de cada lookup pasaría igual.
_CATALOGO = {
    "empresas": [{"id": "emp-1", "nombre": "Karstec"}, {"id": "emp-2", "nombre": "Dosuba"}],
    "empleados": [{"id": "p-1", "nombre": "Ana", "apellido": "Pérez", "area_id": "a-1"},
                  {"id": "p-2", "nombre": "Luis", "apellido": "Gómez", "area_id": "a-2"},
                  {"id": "p-3", "nombre": "Sin", "apellido": "Área", "area_id": None}],
    "areas": [{"id": "a-1", "nombre": "Sistemas"}, {"id": "a-2", "nombre": "Salud"}],
    "tipos_ausencia": [{"id": "t-1", "nombre": "Enfermedad"}, {"id": "t-2", "nombre": "Estudio"}],
}


def _fila(id_: str, empresa: str, empleado: str, tipo: str) -> dict:
    return {"id": id_, "empresa_id": empresa, "empleado_id": empleado, "tipo_id": tipo,
            "fecha_desde": "2026-03-01", "fecha_hasta": "2026-03-03", "dias": 3,
            "justificada": True, "motivo": None, "created_at": "2026-02-20T09:00:00+00:00"}


_FILAS = [_fila("au-1", "emp-1", "p-1", "t-1"),
          _fila("au-2", "emp-2", "p-2", "t-2"),
          _fila("au-3", "emp-1", "p-3", "t-1")]


@pytest.fixture
def consultas(monkeypatch) -> list:
    """Falsea `_q` con datos REALES por tabla y registra qué se consultó."""
    pedidos: list = []

    def _q(table: str, cols: str, ids: list) -> list:
        pedidos.append((table, tuple(sorted(ids))))
        return [f for f in _CATALOGO.get(table, []) if f["id"] in ids]

    monkeypatch.setattr(row_mod, "_q", _q)
    return pedidos


# ── el cuerpo del mapper, con filas ───────────────────────────────────────────

class TestBuildConFilas:

    def test_no_revienta_y_devuelve_una_respuesta_por_fila(self, consultas) -> None:
        """El test que habría atrapado el `NameError` de `_TA`.

        ¿Qué tendría que ser distinto para que no pueda fallar? Que `_FILAS` fuera `[]`: el
        `if not rows: return []` corta antes de tocar `_TA`."""
        salida = row_mod._build(_FILAS)
        assert len(salida) == len(_FILAS) == 3

    def test_consulta_la_tabla_de_tipos(self, consultas) -> None:
        """🔴 LA REGRESIÓN, anclada por nombre. `_TA` es `"tipos_ausencia"`: si volviera a quedar
        como nombre libre esto explota, y si alguien lo cambiara por otro literal se ve acá."""
        row_mod._build(_FILAS)
        tablas = [t for t, _ in consultas]
        assert "tipos_ausencia" in tablas
        assert row_mod._TA == "tipos_ausencia"

    def test_resuelve_los_cuatro_nombres(self, consultas) -> None:
        """Empresa, empleado, área y tipo. Con un `_q` que devolviera `[]` los cuatro darían
        `None` y el test no distinguiría "resolvió" de "no hizo nada"."""
        a, b, c = row_mod._build(_FILAS)
        assert (a.empresa_nombre, a.empleado_nombre, a.area_nombre, a.tipo_nombre) == \
               ("Karstec", "Ana Pérez", "Sistemas", "Enfermedad")
        assert (b.empresa_nombre, b.empleado_nombre, b.area_nombre, b.tipo_nombre) == \
               ("Dosuba", "Luis Gómez", "Salud", "Estudio")
        # El empleado sin área no rompe ni hereda el área del anterior.
        assert (c.area_id, c.area_nombre) == (None, None)
        assert c.tipo_nombre == "Enfermedad"

    def test_los_lookups_son_batch_no_uno_por_fila(self, consultas) -> None:
        """La invariante que el módulo declara: un `IN` por dimensión, nunca uno por fila. Con 3
        filas son 4 consultas (empresas, empleados, areas, tipos), no 12."""
        row_mod._build(_FILAS)
        tablas = [t for t, _ in consultas]
        assert sorted(tablas) == ["areas", "empleados", "empresas", "tipos_ausencia"]
        assert len(consultas) == 4

    def test_sin_areas_no_consulta_areas(self, consultas) -> None:
        """La rama `if area_ids else []`: sin nadie con área, la consulta ni se hace."""
        row_mod._build([_fila("au-9", "emp-1", "p-3", "t-1")])
        assert "areas" not in [t for t, _ in consultas]


# ── la guarda contra el falso verde ───────────────────────────────────────────

def test_la_lista_vacia_no_prueba_nada(consultas) -> None:
    """🔴 DEJA ESCRITO POR QUÉ EL BUG SOBREVIVIÓ: con `[]` el mapper NO se ejecuta.

    No es un test del comportamiento vacío (que igual se verifica): es la evidencia de que
    llamar a `_build([])` no cuenta como cobertura. Cero consultas = cero cuerpo ejecutado.
    """
    assert row_mod._build([]) == []
    assert consultas == [], "con lista vacía el mapper no consulta nada: no prueba nada"


def test_el_corto_circuito_sigue_siendo_la_primera_linea() -> None:
    """Si alguien sacara el `if not rows`, el test de arriba dejaría de significar lo que dice.

    ¿Qué tendría que ser distinto para que falle? Que el early-return desapareciera o se moviera
    después de los lookups — ahí `_build([])` sí ejecutaría cuerpo y la guarda de arriba mentiría.
    """
    assert guarda_de(row_mod._build) == "rows"
