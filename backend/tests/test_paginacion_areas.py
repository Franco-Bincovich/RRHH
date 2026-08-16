"""
Áreas: paginación y —lo que define esta sesión— la BÚSQUEDA server-side.

## 🚨 LAS TRES PREGUNTAS PREVIAS, CONTESTADAS ANTES DE ESCRIBIR NADA

**1. ¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?**

  · **137 FILAS Y EL TÉRMINO BUSCADO FUERA DE LA PRIMERA PÁGINA.** Es LA condición del archivo.
    El área que se busca (`Zulu`) queda en la posición 120 del orden por nombre, o sea en la
    página 5 con `page_size=25`. Con un almacén de 20 filas —o con el término en la página 1—
    un buscador que filtre en memoria sobre la página encuentra igual, y el test que sostiene
    toda la sesión pasaría con el bug puesto.

  · **EL `.ilike()` FILTRA DE VERDAD Y ANTES DE CONTAR.** Si el fake ignorara el `search`, el
    total seguiría siendo 137 con y sin búsqueda y "el export respeta el filtro" sería
    indistinguible de "el export trae todo".

  · **40 EMPATES QUE CRUZAN EL CORTE.** `nombre` no es único —las áreas son POR empresa y dos
    sociedades tienen cada una su "Sistemas"— así que sin `.order("id")` las homónimas se
    reordenan entre consultas. Los empatados llegan al revés en las llamadas pares, que es la
    libertad real de Postgres sin ORDER BY total.

  · **EL `count` ES DEL FILTRO Y EL `.range()` RECORTA DESPUÉS** (el orden de PostgREST).

**2. ¿El fake ES lo que estoy probando?** No: lo falseado es el CLIENTE DE SUPABASE, un escalón
por debajo del repo. `AreaRepo`, `AreaService`, el wrapper Pydantic y `_paginacion` son reales.

**3. ¿El test replica adentro lo que dice verificar?** El total esperado sale de contar el
almacén y la posición del término buscado se verifica con una guarda, no se afirma de memoria.
"""
from datetime import datetime
from types import SimpleNamespace
from typing import List

import pytest

TOTAL = 137
PAGE_SIZE = 25
EMPRESA = "11111111-1111-1111-1111-111111111111"
EMPATADOS = 40
EMPATE_DESDE = 10
# El área que se busca. Su nombre la manda al final del orden alfabético — página 5 de 6.
BUSCADA = "Zulu Auditoría"
POS_BUSCADA = 120


def _nombre(i: int) -> str:
    if i == POS_BUSCADA:
        return BUSCADA
    if EMPATE_DESDE <= i < EMPATE_DESDE + EMPATADOS:
        return f"Ape{EMPATE_DESDE:04d}"   # homónimas: el caso real de "Sistemas" en dos empresas
    return f"Ape{i:04d}"


def _filas():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empresa_id": EMPRESA,
             "nombre": _nombre(i), "descripcion": None, "responsable_id": None,
             "activo": True, "created_at": datetime(2026, 1, 1).isoformat()}
            for i in range(TOTAL)]


class _Tabla:
    """Motor mínimo: filtra (incluido `ilike`), ordena, cuenta el filtro y recién ahí recorta."""

    def __init__(self, filas: List[dict], estado: dict, tabla: str) -> None:
        self._filas, self._estado, self._tabla = list(filas), estado, tabla
        self._ordenes: List[tuple] = []
        self._rango = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) == str(val)]
        return self

    def neq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) != str(val)]
        return self

    def ilike(self, col, patron):
        # `%texto%` → contiene, sin distinguir mayúsculas. Es lo que hace PostgREST.
        aguja = patron.strip("%").lower()
        self._filas = [r for r in self._filas if aguja in str(r.get(col, "")).lower()]
        return self

    def order(self, col, desc=False):
        self._ordenes.append((col, desc))
        return self

    def range(self, desde, hasta):
        self._rango = (desde, hasta)
        return self

    def execute(self):
        # 🔴 EL CONTADOR ES POR TABLA, Y NO ES UN DETALLE. Con un contador compartido, la consulta
        # de `empleados` que hace el conteo por área metía un `execute()` en el medio de cada
        # `get_pagina`, así que la de `areas` caía SIEMPRE en la misma paridad y no se reordenaba
        # nunca. El fake se veía correcto —la guarda aislada pasaba— pero por el camino real los
        # empates llegaban siempre igual, y sacarle el `.order("id")` al repo NO rompía nada.
        # Lo cazó la mutación obligatoria, no la lectura del fake.
        self._estado[self._tabla] = self._estado.get(self._tabla, 0) + 1
        filas = list(self._filas)
        if self._estado[self._tabla] % 2 == 0:
            filas.reverse()
        for col, desc in reversed(self._ordenes):
            filas = sorted(filas, key=lambda r, c=col: str(r.get(c, "")), reverse=desc)
        total = len(filas)
        if self._rango is not None:
            filas = filas[self._rango[0]:self._rango[1] + 1]
        return SimpleNamespace(data=filas, count=total)


def _cliente(estado):
    class _C:
        def table(self, t):
            # `empleados` es la consulta del conteo por área: vacía, acá no se mide el headcount.
            return _Tabla(_filas() if t == "areas" else [], estado, t)
    return _C()


@pytest.fixture
def svc(monkeypatch):
    import repositories._area_row as row_mod
    import repositories.area_repo as mod
    from services.area_service import AreaService
    estado = {"llamadas": 0}
    monkeypatch.setattr(mod, "supabase_admin", _cliente(estado))
    monkeypatch.setattr(row_mod, "supabase_admin", _cliente(estado))
    return AreaService()


class TestBuscarUnAreaQueEstaEnLaPagina5:
    """🔴 EL TEST QUE SOSTIENE ESTA SESIÓN."""

    def test_la_encuentra_aunque_no_este_en_la_primera_pagina(self, svc) -> None:
        """Con el buscador filtrando en memoria sobre la página, esto devuelve 0 resultados:
        el filtro nunca ve la fila 120 porque la página 1 llega hasta la 24."""
        r = svc.get_pagina(None, "Zulu", 1, PAGE_SIZE)
        assert r.total == 1, f"buscando 'Zulu' el total dio {r.total}, esperaba 1"
        assert [a.nombre for a in r.items] == [BUSCADA]

    def test_el_area_buscada_esta_de_verdad_fuera_de_la_primera_pagina(self, svc) -> None:
        """Guarda del caso: si `Zulu` cayera en la página 1, el test de arriba pasaría con el
        bug puesto. Se verifica pidiendo la página 1 SIN búsqueda."""
        primera = svc.get_pagina(None, None, 1, PAGE_SIZE)
        assert BUSCADA not in [a.nombre for a in primera.items]
        assert primera.total == TOTAL

    def test_la_busqueda_no_distingue_mayusculas(self, svc) -> None:
        assert svc.get_pagina(None, "zulu", 1, PAGE_SIZE).total == 1

    def test_un_termino_que_no_existe_da_cero_y_no_el_total(self, svc) -> None:
        """Contracara: si el `search` se ignorara, esto devolvería 137."""
        assert svc.get_pagina(None, "no-existe-ninguna", 1, PAGE_SIZE).total == 0


class TestElExportRespetaLaBusqueda:
    def test_exportar_con_search_no_trae_todo(self, svc, monkeypatch) -> None:
        """🔴 Es la invariante 1 del bloque B. Antes el buscador era local, el export no lo veía
        y el archivo salía con las 137 mientras la pantalla mostraba 1."""
        pedidos: List[dict] = []
        original = type(svc).get_pagina

        def espia(self, empresa_id=None, search=None, page=1, page_size=20):
            pedidos.append({"search": search, "page_size": page_size})
            return original(self, empresa_id, search, page, page_size)

        monkeypatch.setattr(type(svc), "get_pagina", espia)
        svc.exportar(None, "csv", "Zulu")
        assert pedidos and pedidos[0]["search"] == "Zulu", f"el export pidió {pedidos}"

    def test_el_export_pide_el_tope_y_no_el_page_size_del_listado(self, svc, monkeypatch) -> None:
        from services._limite_export import LIMITE_FILAS_EXPORT
        pedidos: List[int] = []
        original = type(svc).get_pagina

        def espia(self, empresa_id=None, search=None, page=1, page_size=20):
            pedidos.append(page_size)
            return original(self, empresa_id, search, page, page_size)

        monkeypatch.setattr(type(svc), "get_pagina", espia)
        svc.exportar(None, "csv", None)
        assert LIMITE_FILAS_EXPORT in pedidos, f"el export pidió {pedidos}"

    def test_el_archivo_sale(self, svc) -> None:
        assert svc.exportar(None, "csv", "Zulu").content


class TestTodasLasPaginasCubrenElTotalUnaVez:
    def test_cada_fila_aparece_exactamente_una_vez(self, svc) -> None:
        """🔴 Sin `.order("id")` esto ROJEA: las 40 homónimas se pisan entre páginas."""
        vistos: List[str] = []
        for p in range(1, TOTAL // PAGE_SIZE + 2):
            vistos += [str(a.id) for a in svc.get_pagina(None, None, p, PAGE_SIZE).items]
        repetidos = sorted({i for i in vistos if vistos.count(i) > 1})
        assert not repetidos, f"filas repetidas entre páginas: {repetidos[:5]}…"
        assert len(vistos) == TOTAL and len(set(vistos)) == TOTAL

    def test_el_total_no_cambia_al_pasar_de_pagina(self, svc) -> None:
        assert [svc.get_pagina(None, None, p, PAGE_SIZE).total for p in (1, 2, 3, 6)] == [TOTAL] * 4

    def test_la_pagina_recorta_y_el_total_no(self, svc) -> None:
        r = svc.get_pagina(None, None, 1, PAGE_SIZE)
        assert len(r.items) == PAGE_SIZE and r.total == TOTAL


class TestElCatalogoSigueTrayendoTodo:
    """🔴 EL RIESGO REAL DE ESTA SESIÓN. `get_areas` alimenta ~15 selectores del front y la
    resolución nombre→id del import de nómina. Paginarlo habría dejado cada dropdown mostrando
    20 de ~180, sin error — sólo áreas que "no existen"."""

    def test_get_areas_no_pagina(self, svc) -> None:
        assert len(svc.get_areas(None)) == TOTAL

    def test_y_el_listado_del_mismo_service_si_recorta(self, svc) -> None:
        """Contracara: si los dos devolvieran lo mismo, el test de arriba no probaría nada."""
        assert len(svc.get_pagina(None, None, 1, PAGE_SIZE).items) == PAGE_SIZE


class TestElAlmacenPuedeDesmentir:
    """Las guardas del fake. Sin ellas, todo lo de arriba pasaría en el vacío."""

    def test_hay_mas_filas_que_una_pagina(self) -> None:
        assert TOTAL > PAGE_SIZE * 4

    def test_el_area_buscada_esta_lejos_de_la_primera_pagina(self) -> None:
        """Ordenadas por nombre, `Zulu…` va al final: su posición real tiene que superar
        holgadamente `PAGE_SIZE`. Se calcula, no se afirma."""
        ordenadas = sorted(_filas(), key=lambda r: (r["nombre"], r["id"]))
        pos = [r["nombre"] for r in ordenadas].index(BUSCADA)
        assert pos > PAGE_SIZE * 3, f"la buscada quedó en la posición {pos}, muy cerca del inicio"

    def test_el_bloque_de_empates_cruza_el_corte(self) -> None:
        assert EMPATE_DESDE < PAGE_SIZE < EMPATE_DESDE + EMPATADOS

    def test_el_ilike_filtra_de_verdad(self) -> None:
        est = {"llamadas": 1}
        r = _Tabla(_filas(), est, "areas").ilike("nombre", "%Zulu%").execute()
        assert r.count == 1

    def test_el_fake_desordena_entre_consultas(self, monkeypatch) -> None:
        """🔴 LA GUARDA VA POR EL CAMINO REAL (el repo), no por `_Tabla` aislada.

        La versión aislada de este test pasaba mientras el fake NO reordenaba nada por el camino
        real: el conteo por área metía un `execute()` sobre `empleados` entre página y página y
        dejaba la consulta de `areas` siempre en la misma paridad. Una guarda que no recorre el
        mismo camino que los tests que protege no protege nada.
        """
        import repositories._area_row as row_mod
        import repositories.area_repo as mod
        estado = {}
        monkeypatch.setattr(mod, "supabase_admin", _cliente(estado))
        monkeypatch.setattr(row_mod, "supabase_admin", _cliente(estado))
        repo = mod.AreaRepo()
        # Sin ningún orden: dos veces la misma página tienen que dar resultados distintos.
        a = mod._base(None, None, contar=True).range(0, 9).execute().data
        b = mod._base(None, None, contar=True).range(0, 9).execute().data
        assert [r["id"] for r in a] != [r["id"] for r in b]
        # Y con el orden puesto, el repo real tiene que dar SIEMPRE lo mismo.
        p1 = [x.id for x in repo.find_pagina(None, None, 1, PAGE_SIZE)[0]]
        p2 = [x.id for x in repo.find_pagina(None, None, 1, PAGE_SIZE)[0]]
        assert p1 == p2

    def test_el_count_es_del_filtro_y_no_de_la_pagina(self) -> None:
        r = _Tabla(_filas(), {"llamadas": 0}, "areas").range(0, 9).execute()
        assert len(r.data) == 10 and r.count == TOTAL
