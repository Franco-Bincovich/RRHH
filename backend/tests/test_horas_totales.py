"""
Los totales de la pantalla de horas salen del CONJUNTO, no de la página.

🔴 EL BUG QUE ESTO CIERRA. `HorasTab` paginaba de a 20 y calculaba el pie con dos `.reduce()`
sobre las filas visibles: con 400 cargas la pantalla decía "9 h" y el número cambiaba al pasar de
página. Nada lo delataba — un total plausible es indistinguible de uno correcto.

🔴 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR:

  · **La página tiene que ser MÁS CHICA que el conjunto.** Si el fake devolviera las 5 filas
    tanto en `find_by_proyecto` como en el agregado, sumar la página daría el mismo número que
    sumar todo y el test pasaría con el bug puesto. Por eso son 5 cargas y `page_size=2`: el
    total correcto (35 h) NO es el de ninguna página (12, 15 y 8).

  · **Los dos caminos tienen que venir de fuentes DISTINTAS**, como en la realidad: la página la
    da `HorasRepo.find_by_proyecto` (paginada) y los totales `totales_de_proyecto` (agregado sin
    paginar). Un fake que sirviera los dos desde la misma lista ya recortada volvería a esconder
    el bug.

  · **Tiene que haber una carga SIN `valor_hora_snapshot`**, que es el caso real de las cargas
    del link público: aporta horas pero no costo. Sin ella, `total_horas` y `total_costo` serían
    proporcionales y un error en el guard de None pasaría desapercibido.
"""
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from schemas.horas import HoraResponse

PROYECTO = str(uuid4())

# 5 cargas: 12 + 15 + 8 = 35 h en total, repartidas en 3 páginas de 2. Ninguna página suma 35.
CARGAS = [
    {"horas": 8.0, "valor_hora_snapshot": 100.0},
    {"horas": 4.0, "valor_hora_snapshot": 100.0},
    {"horas": 10.0, "valor_hora_snapshot": 50.0},
    {"horas": 5.0, "valor_hora_snapshot": 50.0},
    # 🔑 Carga del link público: sin snapshot. Suma horas, NO suma costo.
    {"horas": 8.0, "valor_hora_snapshot": None},
]
TOTAL_HORAS = 35.0
TOTAL_COSTO = 8 * 100 + 4 * 100 + 10 * 50 + 5 * 50   # 1950.0 — la quinta aporta 0


def _hora(i: int, f: dict) -> "HoraResponse":
    """Fila mapeada como la devuelve el repo real: `costo` YA calculado, None sin snapshot."""
    vh = f["valor_hora_snapshot"]
    return HoraResponse(
        id=uuid4(), fecha=date(2026, 3, 1 + i), horas=f["horas"],
        valor_hora_snapshot=vh, costo=(f["horas"] * vh if vh is not None else None),
        created_at=datetime(2026, 3, 1, 12, 0, 0),
    )


class _FakeHorasRepo:
    """Devuelve SOLO la página pedida, como el repo real."""

    def find_by_proyecto(self, _pid, page=1, page_size=20):
        ini = (page - 1) * page_size
        items = [_hora(ini + n, f) for n, f in enumerate(CARGAS[ini:ini + page_size])]
        return items, len(CARGAS)


class _FakeProyectosRepo:
    def find_by_id(self, _id, _empresa=None):
        return SimpleNamespace(id=PROYECTO)


@pytest.fixture
def svc(monkeypatch):
    import services.horas_service as mod

    # El agregado ve TODAS las cargas — nunca la página. Es la asimetría que hace falsable el test.
    monkeypatch.setattr(
        mod, "totales_de_proyecto",
        lambda _pid: (TOTAL_HORAS, float(TOTAL_COSTO)),
    )
    return mod.HorasService(repo=_FakeHorasRepo(), proyectos_repo=_FakeProyectosRepo())


class TestElTotalNoSaleDeLaPagina:
    def test_total_horas_es_el_del_proyecto_y_no_el_de_la_pagina(self, svc) -> None:
        """🔴 Si el service volviera a sumar `rows`, esto daría 12.0 (la página 1) en vez de 35."""
        r = svc.get_by_proyecto(PROYECTO, page=1, page_size=2)
        assert len(r.items) == 2, "la página tiene que ser más chica que el conjunto"
        assert r.total_horas == TOTAL_HORAS

    def test_el_total_es_identico_en_las_tres_paginas(self, svc) -> None:
        """La prueba de que es un total y no un subtotal: navegar no lo mueve."""
        vistos = [(svc.get_by_proyecto(PROYECTO, page=p, page_size=2).total_horas,
                   svc.get_by_proyecto(PROYECTO, page=p, page_size=2).total_costo)
                  for p in (1, 2, 3)]
        assert vistos == [(TOTAL_HORAS, TOTAL_COSTO)] * 3

    def test_ninguna_pagina_suma_el_total(self, svc) -> None:
        """Contracara: si alguna página sumara 35 por casualidad, los tests de arriba pasarían
        con el bug puesto. Se verifica que el dato elegido no permite ese empate."""
        for p in (1, 2, 3):
            pagina = svc.get_by_proyecto(PROYECTO, page=p, page_size=2)
            assert sum(h.horas for h in pagina.items) != TOTAL_HORAS

    def test_la_carga_sin_snapshot_suma_horas_pero_no_costo(self, svc) -> None:
        """Las cargas del link público no tienen con qué costearse: aportan 0 al costo.
        35 h contra $1.950 sólo cierra si la quinta carga sumó horas y no plata."""
        r = svc.get_by_proyecto(PROYECTO, page=1, page_size=2)
        assert (r.total_horas, r.total_costo) == (35.0, 1950.0)


class TestElAgregadoDelRepo:
    """`totales_de_proyecto` de verdad, contra un cliente de Supabase falso."""

    def _con_filas(self, monkeypatch, filas):
        import repositories._proyectos_enrich as mod

        class _Q:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def execute(self):
                return SimpleNamespace(data=filas)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.totales_de_proyecto

    def test_suma_todas_las_filas(self, monkeypatch) -> None:
        fn = self._con_filas(monkeypatch, CARGAS)
        assert fn(PROYECTO) == (TOTAL_HORAS, float(TOTAL_COSTO))

    def test_sin_cargas_da_cero_y_no_revienta(self, monkeypatch) -> None:
        """Un proyecto recién creado. `sum([])` es 0, pero el redondeo también tiene que aguantar."""
        fn = self._con_filas(monkeypatch, [])
        assert fn(PROYECTO) == (0.0, 0.0)

    def test_snapshot_nulo_no_revienta(self, monkeypatch) -> None:
        """`float(None)` levanta TypeError. Desde la migración 103 la columna es NULLABLE."""
        fn = self._con_filas(monkeypatch, [{"horas": 3.0, "valor_hora_snapshot": None}])
        assert fn(PROYECTO) == (3.0, 0.0)
