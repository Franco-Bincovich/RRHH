"""
Los DOS listados que empezaron a paginar en la sesión 3: vacantes y costos/nómina.

## 🚨 LAS TRES PREGUNTAS PREVIAS, CONTESTADAS ANTES DE ESCRIBIR NADA

**1. ¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?**

  · **137 FILAS, no 20.** Con menos que `page_size` hay una sola página: el recorte no recorta,
    el total coincide con el largo, y las tres mutaciones obligatorias pasarían en verde.
  · **40 EMPATES QUE CRUZAN EL CORTE** (posiciones 10..49 con `page_size=25`). Sin empates el
    `.order("id")` es decorativo; con un bloque que entre en una página, tampoco se ve.
  · **LOS EMPATADOS LLEGAN EN OTRO ORDEN EN CADA CONSULTA** — `_Tabla` invierte la base en las
    llamadas pares. Es la libertad que se toma Postgres sin `ORDER BY` total, y es lo que hace
    que "sin desempate" sea un fallo observable.
  · **EL `count` ES DEL FILTRO Y EL `.range()` RECORTA DESPUÉS** (el orden de PostgREST).
  · 🔑 **NÓMINA ORDENA POR UNA COLUMNA DE OTRA TABLA**, así que el fake tiene que soportar
    `order(col, foreign_table=...)` y ordenar POR ESE VALOR — si lo ignorara, el orden que este
    módulo eligió (apellido del empleado) quedaría sin probar y daría igual mandarlo o no.

**2. ¿El fake ES lo que estoy probando?** No: lo falseado es el CLIENTE DE SUPABASE, un escalón
por debajo de los repos. Los repos, los services, los wrappers Pydantic y `_paginacion` son
reales. La sintaxis del `order` por columna embebida se verificó además contra un PostgREST 12.2.3
de verdad; acá se prueba que el repo la EMITA.

**3. ¿El test replica adentro lo que dice verificar?** No hay números copiados del código: el
total sale de contar el almacén y el recorte se compara con el `page_size` que pidió el test.
"""
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import List

import pytest

TOTAL = 137
PAGE_SIZE = 25
EMPRESA = "11111111-1111-1111-1111-111111111111"
EMPATADOS = 40
EMPATE_DESDE = 10


def _idx(i: int) -> int:
    """Índice EFECTIVO de orden: las filas empatadas colapsan todas al mismo."""
    return EMPATE_DESDE if EMPATE_DESDE <= i < EMPATE_DESDE + EMPATADOS else i


def _fecha(i: int) -> str:
    """La clave de orden como fecha ISO (ordena igual como texto que cronológicamente)."""
    return (date(2026, 1, 1) + timedelta(days=_idx(i))).isoformat()


def _apellido(i: int) -> str:
    return f"Ape{_idx(i):04d}"


class _Tabla:
    """Motor mínimo: filtra, ORDENA (incluso por columna embebida), cuenta y recién ahí recorta."""

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

    def order(self, col, desc=False, foreign_table=None, **_k):
        # 🔑 `foreign_table` se GUARDA y se usa: el orden de nómina es por `empleados(apellido)`,
        # y un fake que lo tirara a la basura dejaría sin probar la decisión de este módulo.
        self._ordenes.append((col, desc, foreign_table))
        return self

    def range(self, desde, hasta):
        self._rango = (desde, hasta)
        return self

    @staticmethod
    def _valor(fila, col, foreign):
        """El valor de orden: si viene de un embed, se lee del dict anidado."""
        if foreign:
            return str((fila.get(foreign) or {}).get(col, ""))
        return str(fila.get(col, ""))

    def execute(self):
        self._estado["llamadas"] += 1
        filas = list(self._filas)
        if self._estado["llamadas"] % 2 == 0:
            filas.reverse()
        for col, desc, foreign in reversed(self._ordenes):
            filas = sorted(filas, key=lambda r, c=col, f=foreign: self._valor(r, c, f), reverse=desc)
        total = len(filas)
        if self._rango is not None:
            filas = filas[self._rango[0]:self._rango[1] + 1]
        return SimpleNamespace(data=filas, count=total)


def _cliente(filas, estado):
    class _C:
        def table(self, _t):
            return _Tabla(filas, estado)
    return _C()


# ── vacantes ─────────────────────────────────────────────────────────────────

def _filas_vacantes():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empresa_id": EMPRESA,
             "titulo": f"V{i}", "estado": "nueva", "area_id": "aaaa",
             "created_at": _fecha(i) + "T00:00:00", "codigo": f"VAC-{i:04d}"}
            for i in range(TOTAL)]


def _svc_vacantes(monkeypatch, estado):
    import repositories._vacante_row as row_mod
    import repositories.vacante_repo as mod
    from services.vacante_service import VacanteService
    monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_vacantes(), estado))
    monkeypatch.setattr(row_mod, "_vrow", lambda r: SimpleNamespace(**r), raising=False)
    return VacanteService(repo=mod.VacanteRepo(), audit=SimpleNamespace(registrar=lambda **k: None))


# ── costos / nómina ──────────────────────────────────────────────────────────

def _filas_nomina():
    return [{"id": f"{i:08d}-0000-0000-0000-000000000000", "empleado_id": f"e{i}",
             "empresa_id": EMPRESA, "mes": 7, "anio": 2026,
             "salario_bruto": 1000.0, "cargas_sociales": 200.0, "total": 1200.0,
             "empleados": {"nombre": "N", "apellido": _apellido(i), "areas": {"nombre": "A"}},
             "empresas": {"nombre": "ACME"}} for i in range(TOTAL)]


def _svc_nomina(monkeypatch, estado):
    import repositories.nomina_repo as mod
    from services.costo_service import CostoService
    monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_nomina(), estado))
    return CostoService(nomina_repo=mod.NominaRepo())


def _pagina_vac(svc, page):
    return svc.get_vacantes(None, None, page, PAGE_SIZE)


def _pagina_nom(svc, page):
    return svc.get_nomina_mes(7, 2026, None, page, PAGE_SIZE)


MODULOS = [("vacantes", _svc_vacantes, _pagina_vac), ("costos/nomina", _svc_nomina, _pagina_nom)]
IDS = [m[0] for m in MODULOS]


@pytest.fixture
def estado():
    return {"llamadas": 0}


@pytest.mark.parametrize("nombre,armar,pagina", MODULOS, ids=IDS)
class TestTodasLasPaginasCubrenElTotalUnaVez:
    def test_cada_fila_aparece_exactamente_una_vez(self, nombre, armar, pagina, monkeypatch, estado) -> None:
        """🔴 Sin `.order("id")` esto ROJEA: las páginas se pisan sobre el bloque de 40 empatados."""
        svc = armar(monkeypatch, estado)
        vistos: List[str] = []
        for p in range(1, TOTAL // PAGE_SIZE + 2):
            vistos += [str(x.id) for x in pagina(svc, p).items]
        repetidos = sorted({i for i in vistos if vistos.count(i) > 1})
        assert not repetidos, f"{nombre}: filas repetidas entre páginas: {repetidos[:5]}…"
        assert len(vistos) == TOTAL and len(set(vistos)) == TOTAL

    def test_el_total_no_cambia_al_pasar_de_pagina(self, nombre, armar, pagina, monkeypatch, estado) -> None:
        svc = armar(monkeypatch, estado)
        assert [pagina(svc, p).total for p in (1, 2, 3, 6)] == [TOTAL] * 4

    def test_la_pagina_recorta_y_el_total_no(self, nombre, armar, pagina, monkeypatch, estado) -> None:
        svc = armar(monkeypatch, estado)
        r = pagina(svc, 1)
        assert len(r.items) == PAGE_SIZE and r.total == TOTAL

    def test_la_ultima_pagina_trae_el_resto(self, nombre, armar, pagina, monkeypatch, estado) -> None:
        svc = armar(monkeypatch, estado)
        r = pagina(svc, 6)   # 137 = 5 × 25 + 12
        assert len(r.items) == TOTAL % PAGE_SIZE and r.total_pages == 6


@pytest.mark.parametrize("nombre,armar,_p", MODULOS, ids=IDS)
class TestElExportSeLlevaTodo:
    def test_el_export_pide_el_tope_y_no_el_page_size_del_listado(
        self, nombre, armar, _p, monkeypatch, estado,
    ) -> None:
        """🔴 Si usara el default del listado, el archivo saldría con 20 de 137 sin ningún error."""
        from services._limite_export import LIMITE_FILAS_EXPORT
        svc = armar(monkeypatch, estado)
        pedidos: List[int] = []
        metodo = "get_vacantes" if nombre == "vacantes" else "get_nomina_mes"
        original = getattr(type(svc), metodo)

        def espia(self, *a, **k):
            pedidos.append(k.get("page_size", a[-1] if a else None))
            return original(self, *a, **k)

        monkeypatch.setattr(type(svc), metodo, espia)
        svc.exportar(**({"formato": "csv"} if nombre == "vacantes"
                        else {"mes": 7, "anio": 2026, "formato": "csv"}))
        assert LIMITE_FILAS_EXPORT in pedidos, f"{nombre}: pidió {pedidos}"


class TestElOrdenDeNominaEsElApellido:
    """El orden de nómina viaja EN LA QUERY y va por el apellido del EMPLEADO, no por el monto."""

    def _espia(self, monkeypatch):
        import repositories.nomina_repo as mod
        ordenes: List[tuple] = []

        class _Q:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def order(self, col, desc=False, foreign_table=None, **_k):
                ordenes.append((col, desc, foreign_table))
                return self

            def range(self, *a, **k):
                return self

            def execute(self):
                return SimpleNamespace(data=[], count=0)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.NominaRepo(), ordenes

    def test_ordena_por_apellido_del_empleado_y_desempata_por_id(self, monkeypatch) -> None:
        repo, ordenes = self._espia(monkeypatch)
        repo.find_pagina(7, 2026, None, 1, 20)
        assert ordenes == [("apellido", False, "empleados"), ("id", False, None)]

    def test_el_apellido_viaja_como_columna_EMBEBIDA(self, monkeypatch) -> None:
        """`foreign_table="empleados"` produce `order=empleados(apellido)`. Sin él, PostgREST
        buscaría una columna `apellido` en `costos_nomina`, que no existe → 400 42703."""
        repo, ordenes = self._espia(monkeypatch)
        repo.find_pagina(7, 2026, None, 1, 20)
        assert ordenes[0][2] == "empleados"

    def test_no_ordena_por_monto(self, monkeypatch) -> None:
        """Decisión de producto: una nómina se lee buscando a alguien. Ordenar por bruto
        descendente pone a quien más cobra arriba de una pantalla que se comparte."""
        repo, ordenes = self._espia(monkeypatch)
        repo.find_pagina(7, 2026, None, 1, 20)
        assert not any(c in ("salario_bruto", "total") for c, _d, _f in ordenes)


class TestElDashboardSigueViendoTodoElPeriodo:
    """🔴 EL RIESGO REAL DE ESTA SESIÓN. `get_nomina_mes` del repo NO pagina porque sus callers
    agregan: el dashboard suma la masa salarial y agrupa por área. Paginarlo en el lugar habría
    dejado a los KPIs calculando sobre 20 filas de 137, sin error y sin aviso."""

    def test_get_nomina_mes_del_repo_trae_el_periodo_entero(self, monkeypatch) -> None:
        import repositories.nomina_repo as mod
        monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_nomina(), {"llamadas": 0}))
        assert len(mod.NominaRepo().get_nomina_mes(7, 2026, None)) == TOTAL

    def test_y_el_listado_del_mismo_repo_si_recorta(self, monkeypatch) -> None:
        """Contracara: si los dos devolvieran lo mismo, el test de arriba no probaría nada."""
        import repositories.nomina_repo as mod
        monkeypatch.setattr(mod, "supabase_admin", _cliente(_filas_nomina(), {"llamadas": 0}))
        filas, total = mod.NominaRepo().find_pagina(7, 2026, None, 1, PAGE_SIZE)
        assert len(filas) == PAGE_SIZE and total == TOTAL


class TestElAlmacenPuedeDesmentir:
    """Las guardas del fake. Sin ellas, todo lo de arriba pasaría en el vacío."""

    def test_hay_mas_filas_que_una_pagina(self) -> None:
        assert TOTAL > PAGE_SIZE * 4

    def test_el_bloque_de_empates_cruza_el_corte(self) -> None:
        assert EMPATE_DESDE < PAGE_SIZE < EMPATE_DESDE + EMPATADOS

    def test_las_claves_empatan_de_verdad(self) -> None:
        for clave in (_apellido, _fecha):
            vals = [clave(i) for i in range(TOTAL)]
            assert len(vals) - len(set(vals)) == EMPATADOS - 1

    def test_el_fake_desordena_entre_consultas(self) -> None:
        est = {"llamadas": 0}
        filas = _filas_nomina()
        a = _Tabla(filas, est).range(0, 9).execute().data
        b = _Tabla(filas, est).range(0, 9).execute().data
        assert [r["id"] for r in a] != [r["id"] for r in b]

    def test_el_fake_ordena_de_verdad_por_columna_embebida(self) -> None:
        """Si `foreign_table` se ignorara, el orden por apellido quedaría sin probar."""
        est = {"llamadas": 1}   # impar: no invierte, así se mide el orden puro
        filas = _Tabla(_filas_nomina(), est).order("apellido", foreign_table="empleados").execute().data
        apellidos = [f["empleados"]["apellido"] for f in filas]
        assert apellidos == sorted(apellidos)

    def test_el_count_es_del_filtro_y_no_de_la_pagina(self) -> None:
        res = _Tabla(_filas_nomina(), {"llamadas": 0}).range(0, 9).execute()
        assert len(res.data) == 10 and res.count == TOTAL
