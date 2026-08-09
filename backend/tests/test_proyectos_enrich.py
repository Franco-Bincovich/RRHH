"""
`_proyectos_enrich.enriquecer` (y `batch_costos`) CON FILAS. Molde: `test_ausencia_row.py`.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS NO PUEDAN FALLAR?

**Que `_FILAS` estuviera vacía.** `enriquecer` abre con `if not rows: return []`, así que con `[]`
no se ejecuta ni el lookup de empresas ni una sola línea de la aritmética del costeo. Medido
instrumentando la suite el 9/8/2026, este mapper se llamaba **siempre con listas vacías** — tenía
tests y el cuerpo estaba sin probar. ⚠️ En producción SÍ corre: hay 8 proyectos cargados.

`batch_costos` tiene su propio early-return, sobre `proyecto_ids`, y también se ancla acá.

## El costeo es donde puede mentir sin fallar

Es la parte del mapper que hace cuentas, no que copia campos: `presupuesto - costo` y el
porcentaje. Un error ahí no rompe nada, muestra un número equivocado. Por eso los tres proyectos
del catálogo tienen presupuestos y costos DISTINTOS, e incluyen los dos bordes que cambian de
rama: **presupuesto 0** (que da `pct_consumido = None`, no una división por cero) y **costo mayor
al presupuesto** (que da restante negativo, y no se recorta a cero).

⚠️ `presupuesto` es **NOT NULL DEFAULT 0** en la base (verificado contra el catálogo vivo el
9/8/2026: 8 filas, 0 nulas), así que el `float(r.get("presupuesto") or 0)` del módulo es defensa
que no puede dispararse desde la base. NO se testea el caso `None`: `ProyectoResponse.presupuesto`
es `float` y lo rechazaría, así que un test así estaría fijando una combinación imposible.
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

import repositories._proyectos_enrich as enrich_mod  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

E1, E2 = str(uuid4()), str(uuid4())
P1, P2, P3 = str(uuid4()), str(uuid4()), str(uuid4())

_CATALOGO = {"empresas": [{"id": E1, "nombre": "Karstec"}, {"id": E2, "nombre": "Dosuba"}]}


def _fila(id_, empresa, nombre, presupuesto, descripcion=None) -> dict:
    return {"id": id_, "empresa_id": empresa, "nombre": nombre, "descripcion": descripcion,
            "estado": "activo", "fecha_inicio": None, "fecha_fin": None,
            "presupuesto": presupuesto, "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-02T00:00:00+00:00"}


_FILAS = [_fila(P1, E1, "Migración AWS", 1000.0, descripcion="Cutover"),
          _fila(P2, E2, "Sin presupuesto", 0),          # borde: pct None, no división por cero
          _fila(P3, E1, "Excedido", 100.0)]             # borde: restante negativo
_COSTOS = {P1: 250.0, P3: 175.5}                        # P2 sin costo: cae al 0.0 del `.get`


@pytest.fixture
def base(monkeypatch) -> FakeSupabase:
    fake = FakeSupabase(_CATALOGO)
    monkeypatch.setattr(enrich_mod, "supabase_admin", fake)
    return fake


class TestEnriquecerConFilas:

    def test_devuelve_una_respuesta_por_fila_sin_reventar(self, base) -> None:
        assert [str(p.id) for p in enrich_mod.enriquecer(_FILAS, _COSTOS)] == [P1, P2, P3]

    def test_resuelve_la_empresa_de_CADA_fila(self, base) -> None:
        """Dos empresas distintas: un mapper que copiara la primera para todas rojea acá."""
        a, b, c = enrich_mod.enriquecer(_FILAS, _COSTOS)
        assert (a.empresa_nombre, b.empresa_nombre, c.empresa_nombre) == \
               ("Karstec", "Dosuba", "Karstec")

    def test_el_costeo_sale_del_mapa_de_costos_de_esa_fila(self, base) -> None:
        a, _, c = enrich_mod.enriquecer(_FILAS, _COSTOS)
        assert (a.costeo.costo_acumulado, a.costeo.presupuesto_restante, a.costeo.pct_consumido) \
               == (250.0, 750.0, 25.0)
        assert c.costeo.costo_acumulado == 175.5

    def test_un_proyecto_sin_costo_no_hereda_el_del_anterior(self, base) -> None:
        """P2 no está en `_COSTOS`: tiene que caer al 0.0 del `.get`, no al costo de P1."""
        _, b, _ = enrich_mod.enriquecer(_FILAS, _COSTOS)
        assert b.costeo.costo_acumulado == 0.0

    def test_presupuesto_cero_da_pct_None_y_no_divide_por_cero(self, base) -> None:
        """🔴 El borde que cambia de rama. `pct_consumido` es Optional justamente por esto."""
        _, b, _ = enrich_mod.enriquecer(_FILAS, _COSTOS)
        assert b.costeo.pct_consumido is None
        assert b.costeo.presupuesto_restante == 0.0

    def test_gastar_de_mas_deja_el_restante_negativo(self, base) -> None:
        """No se recorta a cero: un proyecto excedido tiene que verse excedido. Mismo criterio
        que el saldo de vacaciones, que tampoco esconde el negativo."""
        _, _, c = enrich_mod.enriquecer(_FILAS, _COSTOS)
        assert c.costeo.presupuesto_restante == -75.5
        assert c.costeo.pct_consumido == 175.5

    def test_el_lookup_de_empresas_es_uno_solo_y_batch(self, base) -> None:
        enrich_mod.enriquecer(_FILAS, _COSTOS)
        assert [t for t, _, _ in base.consultas] == ["empresas"]
        assert sorted(base.consultas[0][2]) == sorted([E1, E2])


class TestBatchCostos:

    def test_suma_horas_por_valor_hora_y_agrupa_por_proyecto(self, monkeypatch) -> None:
        """Dos filas del MISMO proyecto tienen que sumarse, no pisarse."""
        fake = FakeSupabase({"horas_proyecto": [
            {"id": "h1", "proyecto_id": P1, "horas": 10, "valor_hora_snapshot": 25},
            {"id": "h2", "proyecto_id": P1, "horas": 2, "valor_hora_snapshot": 25},
            {"id": "h3", "proyecto_id": P3, "horas": 1, "valor_hora_snapshot": 100},
        ]})
        # `batch_costos` filtra por `proyecto_id`, no por `id`: el doble honra la columna pedida.
        monkeypatch.setattr(enrich_mod, "supabase_admin", fake)
        assert enrich_mod.batch_costos([P1, P3]) == {P1: 300.0, P3: 100.0}

    def test_sin_ids_no_consulta(self, monkeypatch) -> None:
        fake = FakeSupabase({"horas_proyecto": [{"id": "h1", "proyecto_id": P1, "horas": 1,
                                                 "valor_hora_snapshot": 1}]})
        monkeypatch.setattr(enrich_mod, "supabase_admin", fake)
        assert enrich_mod.batch_costos([]) == {}
        assert fake.consultas == []


def test_la_lista_vacia_no_prueba_nada(base) -> None:
    """🔴 POR QUÉ EL CUERPO ESTUVO SIN PROBAR: con `[]` no se ejecuta ni una línea."""
    assert enrich_mod.enriquecer([], _COSTOS) == []
    assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"


def test_los_dos_corto_circuitos_siguen_en_la_primera_linea() -> None:
    """Los DOS: `enriquecer` sobre `rows` y `batch_costos` sobre `proyecto_ids`. Si alguno se
    moviera, la guarda de arriba dejaría de significar lo que dice."""
    assert guarda_de(enrich_mod.enriquecer) == "rows"
    assert guarda_de(enrich_mod.batch_costos) == "proyecto_ids"
