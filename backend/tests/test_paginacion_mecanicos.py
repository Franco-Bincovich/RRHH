"""
Los CUATRO listados que empezaron a paginar en la sesión 2: inventario/ítems,
inventario/asignaciones, capacitaciones/asignaciones y proyectos.

## 🚨 LAS TRES PREGUNTAS PREVIAS, CONTESTADAS ANTES DE ESCRIBIR NADA

**1. ¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?**

  · **EL ALMACÉN TIENE 137 FILAS, no 20.** Con menos que `page_size` hay una sola página y
    ningún test de paginación puede fallar: el recorte no recorta, el total coincide con el
    largo, y las tres mutaciones obligatorias pasarían en verde.

  · **HAY EMPATES QUE CRUZAN EL CORTE DE PÁGINA.** 40 filas comparten la clave de orden y caen a
    caballo del límite de la página 1 (posiciones 10..49 con `page_size=25`). Sin empates el
    `.order("id")` es decorativo y sacárselo no rompe nada.

  · **LOS EMPATADOS LLEGAN EN OTRO ORDEN EN CADA CONSULTA**, que es la libertad que se toma
    Postgres cuando el `ORDER BY` no es total. `_Tabla` invierte la base en las llamadas pares.
    Es lo que convierte "sin desempate" en un fallo observable y no en una teoría.

  · **EL `count` ES EL DEL FILTRO Y EL `.range()` RECORTA DESPUÉS**, en ese orden, que es el de
    PostgREST. Un fake que contara la página no podría desmentir un `total` mal calculado ni un
    export que se lleva 25 filas de 137.

  · **LOS FILTROS FILTRAN DE VERDAD** (`eq`, `in_`, `is_`): si el almacén devolviera lo mismo con
    y sin filtro, "el total respeta el filtro" sería indistinguible de "el total es fijo".

**2. ¿El fake ES lo que estoy probando?** No. Lo falseado es el CLIENTE DE SUPABASE, un escalón
por debajo de los repos. Los cuatro repos, sus cuatro services, los wrappers Pydantic y el helper
`_paginacion` son los REALES.

**3. ¿El test replica adentro lo que dice verificar?** No hay ningún número copiado del código de
producción: el total esperado sale de contar el almacén, y el recorte se compara contra el
`page_size` que el propio test pidió. El molde del fake es `tests/test_paginacion_orden.py`.
"""
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import List

import pytest

from schemas.proyectos import CosteoResumen, ProyectoResponse

TOTAL = 137
PAGE_SIZE = 25
EMPRESA = "11111111-1111-1111-1111-111111111111"
# 40 filas con la MISMA clave de orden, en las posiciones 10..49: cruzan el corte de la página 1
# (25) y el de la página 2 (50). Un bloque que entrara en una sola página no mostraría el bug.
EMPATADOS = 40
EMPATE_DESDE = 10


def _idx(i: int) -> int:
    """El índice EFECTIVO de orden: las filas empatadas colapsan todas al mismo."""
    return EMPATE_DESDE if EMPATE_DESDE <= i < EMPATE_DESDE + EMPATADOS else i


def _clave(i: int) -> str:
    """Clave de orden textual (columna `nombre`)."""
    return f"{_idx(i):04d}"


def _clave_fecha(i: int) -> str:
    """La misma clave como FECHA ISO, para las columnas `date`/`timestamp`.

    ISO ordena igual como texto que cronológicamente, así que el fake puede seguir ordenando con
    `str` sin dejar de modelar el orden real. Días consecutivos desde 2026-01-01: con 137 filas
    cruza meses, que es justo lo que un `f"{i:04d}"` no habría podido representar.
    """
    return (date(2026, 1, 1) + timedelta(days=_idx(i))).isoformat()


class _Tabla:
    """Motor mínimo: filtra, ORDENA con las claves pedidas, cuenta el filtro y recién ahí recorta."""

    def __init__(self, filas: List[dict], estado: dict) -> None:
        self._filas, self._estado = list(filas), estado
        self._ordenes: List[tuple] = []
        self._rango = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filas = [r for r in self._filas if str(r.get(col)) == str(val)]
        return self

    def in_(self, col, vals):
        v = {str(x) for x in vals}
        self._filas = [r for r in self._filas if str(r.get(col)) in v]
        return self

    def is_(self, col, _val):
        self._filas = [r for r in self._filas if r.get(col) is None]
        return self

    def order(self, col, desc=False):
        self._ordenes.append((col, desc))
        return self

    def range(self, desde, hasta):
        self._rango = (desde, hasta)
        return self

    def execute(self):
        self._estado["llamadas"] += 1
        filas = list(self._filas)
        # 🔴 LO QUE HACE FALSABLES A ESTOS TESTS: Postgres no promete resolver los empates igual
        # en dos consultas distintas. El fake lo modela devolviendo la base al revés una de cada
        # dos veces; sin esto, un listado sin desempate se vería perfectamente estable.
        if self._estado["llamadas"] % 2 == 0:
            filas.reverse()
        for col, desc in reversed(self._ordenes):
            filas = sorted(filas, key=lambda r, c=col: str(r.get(c, "")), reverse=desc)
        total = len(filas)          # el count es del FILTRO, antes de recortar
        if self._rango is not None:
            filas = filas[self._rango[0]:self._rango[1] + 1]
        return SimpleNamespace(data=filas, count=total)


def _cliente(filas, estado):
    class _C:
        def table(self, _t):
            return _Tabla(filas, estado)
    return _C()


# ── Los cuatro módulos, cada uno con su almacén y su forma de fila ────────────

def _filas_items():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empresa_id": EMPRESA,
             "nombre": _clave(i), "tipo": "notebook", "estado": "disponible",
             "numero_serie": None, "descripcion": None, "costo": None, "notas": None,
             "fecha_alta": date(2026, 1, 1), "created_at": datetime(2026, 1, 1)} for i in range(TOTAL)]


def _filas_inv_asig():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empresa_id": EMPRESA,
             "item_id": "aaaa", "empleado_id": "bbbb", "fecha_devolucion": None,
             "fecha_asignacion": _clave_fecha(i), "estado_devolucion": None, "notas": None,
             "created_at": datetime(2026, 1, 1)} for i in range(TOTAL)]


def _filas_cap_asig():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empresa_id": EMPRESA,
             "capacitacion_id": "cccc", "empleado_id": "bbbb", "estado": "pendiente",
             "created_at": _clave_fecha(i) + "T00:00:00", "fecha_asignacion": None, "fecha_limite": None,
             "fecha_completado": None, "certificado_path": None, "nombre_libre": None}
            for i in range(TOTAL)]


def _filas_proyectos():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empresa_id": EMPRESA,
             "nombre": f"P{i}", "descripcion": None, "estado": "activo",
             "fecha_inicio": None, "fecha_fin": None, "presupuesto": 0,
             "created_at": datetime.fromisoformat(_clave_fecha(i)), "updated_at": None} for i in range(TOTAL)]


def _svc_items(monkeypatch, estado):
    import repositories._inventario_items_row as row_mod
    import repositories.inventario_items_repo as mod
    from services.inventario_items_service import InventarioItemsService
    monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_items(), estado))
    monkeypatch.setattr(row_mod, "supabase_admin", _cliente([], estado), raising=False)
    return InventarioItemsService()


def _svc_inv_asig(monkeypatch, estado):
    import repositories._inventario_asignacion_row as row_mod
    import repositories.inventario_asignaciones_repo as mod
    from services.inventario_asignaciones_service import InventarioAsignacionesService
    monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_inv_asig(), estado))
    monkeypatch.setattr(row_mod, "supabase_admin", _cliente([], estado))
    return InventarioAsignacionesService()


def _svc_cap_asig(monkeypatch, estado):
    import repositories._asignacion_row as row_mod
    import repositories.asignacion_repo as mod
    from services.asignacion_service import AsignacionService
    monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_cap_asig(), estado))
    monkeypatch.setattr(row_mod, "supabase_admin", _cliente([], estado), raising=False)
    return AsignacionService()


def _svc_proyectos(monkeypatch, estado):
    import repositories.proyectos_repo as mod
    from services.proyectos_service import ProyectosService
    monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_proyectos(), estado))
    monkeypatch.setattr(mod, "batch_costos", lambda _ids: {})
    # `enriquecer` real resolvería empresa y costeo con dos queries más; acá se mide la
    # paginación, no el enriquecido. Devuelve ProyectoResponse REALES porque el wrapper valida
    # el tipo de cada item — un SimpleNamespace lo rechaza.
    monkeypatch.setattr(mod, "enriquecer",
                        lambda rows, _c: [ProyectoResponse.model_construct(
                            **r, empresa_nombre="ACME",
                            costeo=CosteoResumen(costo_acumulado=0, presupuesto_restante=0),
                        ) for r in rows])
    return ProyectosService()


MODULOS = [
    ("inventario/items", _svc_items),
    ("inventario/asignaciones", _svc_inv_asig),
    ("capacitaciones/asignaciones", _svc_cap_asig),
    ("proyectos", _svc_proyectos),
]
IDS = [m[0] for m in MODULOS]


@pytest.fixture
def estado():
    return {"llamadas": 0}


@pytest.mark.parametrize("nombre,armar", MODULOS, ids=IDS)
class TestTodasLasPaginasCubrenElTotalUnaVez:
    def test_cada_fila_aparece_exactamente_una_vez(self, nombre, armar, monkeypatch, estado) -> None:
        """🔴 Sin `.order("id")` en el repo, esto ROJEA: las páginas se pisan entre sí sobre el
        bloque de 40 empatados y algunas filas no salen en ninguna."""
        svc = armar(monkeypatch, estado)
        vistos: List[str] = []
        for page in range(1, TOTAL // PAGE_SIZE + 2):
            vistos += [str(x.id) for x in svc.get_all(page=page, page_size=PAGE_SIZE).items]

        repetidos = sorted({i for i in vistos if vistos.count(i) > 1})
        assert not repetidos, f"{nombre}: filas repetidas entre páginas: {repetidos[:5]}…"
        assert len(vistos) == TOTAL, f"{nombre}: se vieron {len(vistos)} filas de {TOTAL}"
        assert len(set(vistos)) == TOTAL

    def test_el_total_no_cambia_al_pasar_de_pagina(self, nombre, armar, monkeypatch, estado) -> None:
        svc = armar(monkeypatch, estado)
        totales = [svc.get_all(page=p, page_size=PAGE_SIZE).total for p in (1, 2, 3, 6)]
        assert totales == [TOTAL] * 4

    def test_la_pagina_recorta_y_el_total_no(self, nombre, armar, monkeypatch, estado) -> None:
        """Si `total` volviera a ser `len(items)` diría 25 en vez de 137."""
        svc = armar(monkeypatch, estado)
        r = svc.get_all(page=1, page_size=PAGE_SIZE)
        assert len(r.items) == PAGE_SIZE
        assert r.total == TOTAL

    def test_la_ultima_pagina_trae_el_resto(self, nombre, armar, monkeypatch, estado) -> None:
        svc = armar(monkeypatch, estado)
        r = svc.get_all(page=6, page_size=PAGE_SIZE)   # 137 = 5 × 25 + 12
        assert len(r.items) == TOTAL % PAGE_SIZE
        assert r.total_pages == 6


@pytest.mark.parametrize("nombre,armar", MODULOS, ids=IDS)
class TestElExportSeLlevaTodo:
    def test_el_export_no_trae_solo_la_primera_pagina(self, nombre, armar, monkeypatch, estado) -> None:
        """🔴 El export pide `LIMITE_FILAS_EXPORT` filas, no `page_size`. Si usara el default del
        listado, el archivo saldría con 20 de 137 y sin ningún error."""
        from services._limite_export import LIMITE_FILAS_EXPORT
        svc = armar(monkeypatch, estado)
        pedidos: List[int] = []
        original = type(svc).get_all

        def espia(self, *a, **k):
            r = original(self, *a, **k)
            pedidos.append(k.get("page_size", a[-1] if a else None))
            return r

        monkeypatch.setattr(type(svc), "get_all", espia)
        svc.exportar(formato="csv")
        assert LIMITE_FILAS_EXPORT in pedidos, (
            f"{nombre}: el export pidió {pedidos}, no el tope de {LIMITE_FILAS_EXPORT}"
        )

    def test_el_archivo_sale(self, nombre, armar, monkeypatch, estado) -> None:
        svc = armar(monkeypatch, estado)
        assert svc.exportar(formato="csv").content


class TestElAlmacenPuedeDesmentir:
    """Las guardas del fake. Sin ellas, todo lo de arriba pasaría en el vacío."""

    def test_hay_mas_filas_que_una_pagina(self) -> None:
        assert TOTAL > PAGE_SIZE * 4, "con pocas páginas el recorte no se puede observar"

    def test_el_bloque_de_empates_cruza_el_corte_de_pagina(self) -> None:
        """Si entrara entero en una página, sacar el desempate no rompería nada."""
        assert EMPATE_DESDE < PAGE_SIZE < EMPATE_DESDE + EMPATADOS

    def test_las_claves_empatan_de_verdad(self) -> None:
        claves = [_clave(i) for i in range(TOTAL)]
        assert len(claves) - len(set(claves)) == EMPATADOS - 1

    def test_el_fake_desordena_los_empates_entre_consultas(self) -> None:
        """La contracara obligatoria: si dejara de reordenar, los tests de páginas serían
        tautologías. Se pide la misma página dos veces SIN orden y tiene que cambiar."""
        est = {"llamadas": 0}
        filas = _filas_items()
        a = _Tabla(filas, est).range(0, 9).execute().data
        b = _Tabla(filas, est).range(0, 9).execute().data
        assert [r["id"] for r in a] != [r["id"] for r in b]

    def test_el_count_es_del_filtro_y_no_de_la_pagina(self) -> None:
        est = {"llamadas": 0}
        res = _Tabla(_filas_items(), est).range(0, 9).execute()
        assert len(res.data) == 10 and res.count == TOTAL

    def test_los_filtros_filtran(self) -> None:
        """Con un `eq` que no matchea nada, el total tiene que bajar a 0."""
        est = {"llamadas": 0}
        res = _Tabla(_filas_items(), est).eq("empresa_id", "otra").execute()
        assert res.count == 0
