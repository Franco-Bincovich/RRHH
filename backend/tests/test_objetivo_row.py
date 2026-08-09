"""
`_objetivo_row._build` CON FILAS. Molde: `test_ausencia_row.py`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS NO PUEDAN FALLAR?

**Que `_FILAS` estuviera vacía.** Es todo. `_build` abre con `if not rows: return []`, así que
llamarlo con `[]` no ejecuta una sola línea del cuerpo: ni los cuatro lookups, ni el fallback de
responsables, ni el `model_validate`. Medido instrumentando la suite el 9/8/2026, este mapper se
llamaba **siempre con listas vacías** — tenía tests y el cuerpo estaba sin probar. Es el mismo
escondite donde vivió el `NameError` de `_TA` en `_ausencia_row`.

`test_la_lista_vacia_no_prueba_nada` y `test_el_corto_circuito_sigue_siendo_la_primera_linea`
dejan eso escrito en código, para que la guarda no empiece a mentir si alguien mueve el
early-return.

## Por qué el catálogo tiene VARIAS filas con valores distintos

Con una sola fila, un mapper que emitiera constantes —o que leyera siempre el primer resultado de
cada lookup— pasaría igual. Acá hay 3 objetivos de **2 empresas**, con **3 responsables
distintos**, uno **con padre y dos sin**, y uno **sin filas en la puente** (que ejercita el
fallback al dueño). Cada aserción compara el contenido de SU fila, nunca el largo de la lista.
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

import repositories._objetivo_row as row_mod  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

E1, E2 = "e-karstec", "e-dosuba"
U1, U2, U3 = "u-ana", "u-luis", "u-eva"
O1, O2, O3 = "o-padre", "o-hijo", "o-suelto"

_CATALOGO = {
    "empresas": [{"id": E1, "nombre": "Karstec"}, {"id": E2, "nombre": "Dosuba"}],
    "users": [{"id": U1, "nombre": "Ana", "apellido": "Pérez"},
              {"id": U2, "nombre": "Luis", "apellido": "Gómez"},
              {"id": U3, "nombre": "Eva", "apellido": "Luna"}],
    # O1 tiene DOS responsables en la puente; O2 uno solo; O3 NINGUNO (ejercita el fallback).
    "objetivo_responsables": [{"objetivo_id": O1, "user_id": U1}, {"objetivo_id": O1, "user_id": U3},
                              {"objetivo_id": O2, "user_id": U2}],
    "objetivos": [{"id": O1, "titulo": "Cerrar el trimestre"}],
}


def _fila(id_, empresa, responsable, titulo, parent=None) -> dict:
    return {"id": id_, "empresa_id": empresa, "responsable_id": responsable, "titulo": titulo,
            "descripcion": None, "prioridad": "alta", "estado": "en_curso", "fecha_entrega": None,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-02T00:00:00+00:00",
            "parent_id": parent}


_FILAS = [_fila(O1, E1, U1, "Cerrar el trimestre"),
          _fila(O2, E2, U2, "Subobjetivo", parent=O1),
          _fila(O3, E1, U3, "Sin puente")]


@pytest.fixture
def base(monkeypatch) -> FakeSupabase:
    fake = FakeSupabase(_CATALOGO)
    monkeypatch.setattr(row_mod, "supabase_admin", fake)
    return fake


class TestBuildConFilas:

    def test_devuelve_una_respuesta_por_fila_sin_reventar(self, base) -> None:
        """La primera vez que este cuerpo se ejecuta en un test. Ver el encabezado."""
        assert [o.id for o in row_mod._build(_FILAS)] == [O1, O2, O3]

    def test_resuelve_empresa_y_responsable_de_CADA_fila(self, base) -> None:
        """Dos empresas y tres personas distintas: un mapper que emitiera la primera de cada
        lookup para todas las filas rojearía acá."""
        a, b, c = row_mod._build(_FILAS)
        assert (a.empresa_nombre, a.responsable_nombre) == ("Karstec", "Ana Pérez")
        assert (b.empresa_nombre, b.responsable_nombre) == ("Dosuba", "Luis Gómez")
        assert (c.empresa_nombre, c.responsable_nombre) == ("Karstec", "Eva Luna")

    def test_el_titulo_del_padre_solo_donde_hay_padre(self, base) -> None:
        """`parent_titulo` es derivado de OTRA fila. El caso opcional en null son las dos raíces."""
        a, b, c = row_mod._build(_FILAS)
        assert b.parent_titulo == "Cerrar el trimestre" and b.parent_id == O1
        assert (a.parent_id, a.parent_titulo) == (None, None)
        assert (c.parent_id, c.parent_titulo) == (None, None)

    def test_la_lista_de_responsables_sale_de_la_puente(self, base) -> None:
        a, b, _ = row_mod._build(_FILAS)
        assert sorted((r.id, r.nombre) for r in a.responsables) == \
               [(U1, "Ana Pérez"), (U3, "Eva Luna")]
        assert [(r.id, r.nombre) for r in b.responsables] == [(U2, "Luis Gómez")]

    def test_sin_filas_en_la_puente_cae_al_dueño(self, base) -> None:
        """🔴 El fallback que el módulo documenta: una fila anterior al backfill de la 096 no
        puede quedar SIN responsables, porque el dueño siempre lo es. O3 no está en la puente."""
        _, _, c = row_mod._build(_FILAS)
        assert [(r.id, r.nombre) for r in c.responsables] == [(U3, "Eva Luna")]

    def test_los_lookups_son_batch_no_uno_por_fila(self, base) -> None:
        """Con 3 filas: empresas, la puente, users y objetivos. Cuatro consultas, no doce."""
        row_mod._build(_FILAS)
        assert sorted(t for t, _, _ in base.consultas) == \
               ["empresas", "objetivo_responsables", "objetivos", "users"]

    def test_un_solo_lookup_de_personas_para_dueños_y_puente(self, base) -> None:
        """El módulo lo declara: una sola consulta a `users` que cubre las dos necesidades.
        Los 3 ids pedidos son la UNIÓN de dueños y responsables de la puente."""
        row_mod._build(_FILAS)
        pedidos = [ids for t, _, ids in base.consultas if t == "users"]
        assert len(pedidos) == 1
        assert sorted(pedidos[0]) == sorted([U1, U2, U3])

    def test_sin_padres_no_consulta_objetivos(self, base) -> None:
        """La rama `if padre_ids else {}`: sin ningún hijo, esa query ni se emite."""
        row_mod._build([_fila(O3, E1, U3, "Suelto")])
        assert "objetivos" not in [t for t, _, _ in base.consultas]


def test_la_lista_vacia_no_prueba_nada(base) -> None:
    """🔴 POR QUÉ EL CUERPO ESTUVO SIN PROBAR: con `[]` el mapper no ejecuta ni una línea.
    Cero consultas = cero cuerpo. Llamarlo así no cuenta como cobertura."""
    assert row_mod._build([]) == []
    assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"


def test_el_corto_circuito_sigue_siendo_la_primera_linea() -> None:
    """Si alguien moviera el early-return, la guarda de arriba dejaría de significar lo que dice.

    ¿Qué tendría que ser distinto para que falle? Que `if not rows:` desapareciera o quedara
    después de los lookups — ahí `_build([])` sí ejecutaría cuerpo y la guarda mentiría.
    """
    assert guarda_de(row_mod._build) == "rows"
