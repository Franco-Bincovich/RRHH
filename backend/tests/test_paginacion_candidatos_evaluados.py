"""
Sesión 5 de paginación: candidatos (plano, con agrupamiento adentro) y evaluados (tres filtros
que se mudaron del cliente al WHERE).

## 🔴 ACÁ EL DOBLE SÍ ORDENA, RECORTA Y FILTRA — Y ES LA EXCEPCIÓN, NO EL DESCUIDO

La regla del repo dice que un fake que ordena deja pasar un repo que se olvidó del `.order()`
(caso #3: sacarle el `.order(..., desc=True)` real dejaba todo en verde). Acá el doble se
comporta como una base de verdad, a propósito, porque lo que este archivo verifica **no se puede
verificar de otra forma**: que cada fila aparezca exactamente una vez recorriendo TRES páginas
exige que el recorte y el orden pasen de verdad. Con un doble que no recorta, las tres páginas
devuelven lo mismo y la aserción "cada fila una vez" no puede fallar nunca.

**Lo que esa decisión deja descubierto está cubierto en otro lado, y hay que saber cuál:**
  · que el `.order(...)` y el desempate `.order("id")` VIAJEN en la query lo verifica
    `tests/test_paginacion_orden.py`, que barre los siete repos paginados por AST.
  · que el `.range(...)` viaje lo verifica el mismo barrido.
  · que los filtros vayan al WHERE y no a una lista lo verifican `test_candidatos_sin_vacante`
    (candidatos) y `test_filtro_proyecto` (evaluados), los dos falseando el cliente.
Sin esos tres, este archivo sería un verde falso: probaría la aritmética del doble.

## LA PREGUNTA OBLIGATORIA

¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?
  · **Conteo por grupo estable:** que `claves_de_grupo` mirara el conjunto RECORTADO en vez del
    filtrado. El doble recorta SÓLO cuando se le pidió `.range()`, y esa query no lo pide — así
    que si alguien le pasara la paginación, el conteo cambiaría entre páginas y el test rojea.
  · **Sector en la página 3:** que el `.eq("sector", ...)` no filtrara. El doble lo aplica de
    verdad, así que un repo que se olvidara del filtro devolvería la página 1 completa y la
    aserción "vino Zurita y nadie más" rojea.
  · **Cada fila una vez:** que el `.range()` no recortara, o que el orden no fuera total. Las
    filas están construidas CON EMPATES en la columna de orden justamente para eso.
"""
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EMPRESA = UUID("11111111-1111-1111-1111-111111111111")


class _Tabla:
    """Doble de una tabla de PostgREST: filtra, ordena, recorta y cuenta.

    El `count` sale del conjunto FILTRADO y ANTES del recorte, que es lo que hace `count="exact"`
    de verdad. Devolverlo después del `.range()` daría siempre `page_size` y la barra de
    paginación diría "1 de 1" con mil filas atrás.
    """

    def __init__(self, filas: list) -> None:
        self._filas = [dict(f) for f in filas]
        self._contar = False
        self._orden: list = []
        self._rango = None

    def select(self, columnas="*", **k):
        self._contar = k.get("count") == "exact"
        self._columnas = None if columnas == "*" else [c.strip() for c in columnas.split(",")]
        return self

    def eq(self, col, val):
        self._filas = [f for f in self._filas if str(f.get(col)) == str(val)]
        return self

    def is_(self, col, _null):
        self._filas = [f for f in self._filas if f.get(col) is None]
        return self

    def in_(self, col, valores):
        # `is not None` explícito: un NULL no satisface un IN en SQL, cualquiera sea la lista.
        self._filas = [f for f in self._filas
                       if f.get(col) is not None and f.get(col) in valores]
        return self

    @property
    def not_(self):
        return _Negado(self)

    def order(self, col, **k):
        self._orden.append((col, bool(k.get("desc", False))))
        return self

    def range(self, desde, hasta):
        self._rango = (desde, hasta)
        return self

    def execute(self):
        for col, desc in reversed(self._orden):
            self._filas.sort(key=lambda f: (f.get(col) is None, f.get(col)), reverse=desc)
        total = len(self._filas)
        filas = self._filas
        if self._rango:
            filas = filas[self._rango[0]:self._rango[1] + 1]
        if getattr(self, "_columnas", None):
            filas = [{c: f.get(c) for c in self._columnas} for f in filas]
        return type("R", (), {"data": [dict(f) for f in filas],
                              "count": total if self._contar else None})()


class _Negado:
    """`q.not_.is_(col, "null")` — el único uso de `not_` en los repos tocados."""

    def __init__(self, tabla: _Tabla) -> None:
        self._t = tabla

    def is_(self, col, _null):
        self._t._filas = [f for f in self._t._filas if f.get(col) is not None]
        return self._t


def _cliente(filas: list):
    """Un cliente cuya `table()` devuelve SIEMPRE la misma tabla, resembrada en cada llamada.

    Resembrar importa: el listado hace DOS queries (la página y las claves de grupo) y cada una
    tiene que arrancar del catálogo entero. Si compartieran el estado filtrado, la segunda vería
    lo que dejó la primera y el conteo por grupo saldría del recorte — que es exactamente el bug
    que este archivo verifica que no ocurra, tapado por el doble.
    """
    return type("C", (), {"table": staticmethod(lambda _t: _Tabla(filas))})()


# ══════════════════════════════════════════════════════════════════════════════
# CANDIDATOS — plano, con el agrupamiento adentro de la página
# ══════════════════════════════════════════════════════════════════════════════

# 50 candidatos repartidos en 3 búsquedas, DESPAREJO a propósito (28 / 15 / 7): con un reparto
# parejo, 50/3 daría grupos de ~17 y un conteo tomado de la página (20) se confundiría con uno
# tomado del filtro. Y TODOS con el MISMO `created_at`: el empate en la columna de orden es el
# caso real (entran por lote desde la casilla) y es lo que obliga al desempate por id.
_V1, _V2 = uuid4(), uuid4()
_MISMO_INSTANTE = "2026-08-01T09:00:00"


def _candidatos() -> list:
    filas = []
    for i in range(50):
        vacante = _V1 if i < 28 else (_V2 if i < 43 else None)
        filas.append({
            "id": f"{i:08d}-0000-0000-0000-000000000000",
            "empresa_id": str(EMPRESA), "vacante_id": str(vacante) if vacante else None,
            "nombre": f"Cand{i}", "apellido": "Prueba", "email": f"c{i}@x.com",
            "telefono": None, "cargo_anterior": None, "empresa_anterior": None,
            "etapa_pipeline": "nuevo", "score_ia": None,
            "busqueda_congelada": None if vacante else "Búsqueda vieja",
            "cv_storage_path": None, "screening_warning": None,
            "clasificacion_ia": None, "clasificacion_motivo": None,
            "clasificacion_origen": None, "created_at": _MISMO_INSTANTE,
        })
    return filas


class _VacanteRepoFake:
    """Resuelve los títulos vivos. Devuelve sólo los ids que le piden: si devolviera los dos
    siempre, un service que pidiera los ids equivocados igual armaría los nombres bien."""

    TITULOS = {str(_V1): "Analista SSR", str(_V2): "Dev Backend"}

    def __init__(self) -> None:
        self.pedidos: list = []

    def find_by_ids(self, ids):
        from types import SimpleNamespace
        self.pedidos.append(sorted(str(i) for i in ids))
        return [SimpleNamespace(id=str(i), titulo=self.TITULOS[str(i)], area_nombre=None)
                for i in ids if str(i) in self.TITULOS]


@pytest.fixture
def svc_candidatos(monkeypatch):
    import repositories._candidato_listado_repo as listado_mod
    from repositories.candidato_repo import CandidatoRepo
    from services.candidato_service import CandidatoService

    monkeypatch.setattr(listado_mod, "supabase_admin", _cliente(_candidatos()))
    vac = _VacanteRepoFake()
    return CandidatoService(candidato_repo=CandidatoRepo(), vacante_repo=vac), vac


class TestConteoPorGrupoEstable:

    def test_el_conteo_de_cada_grupo_NO_CAMBIA_al_pasar_de_pagina(self, svc_candidatos) -> None:
        """🔴 EL TEST QUE SOSTIENE LA FEATURE. El encabezado de cada búsqueda dice cuántos
        candidatos tiene en TODO el filtro. Si saliera de la página, "Analista SSR (28)" pasaría
        a decir 20, después 8, después 0 — un número que cambia sin que cambie nada."""
        svc, _ = svc_candidatos
        conteos = [svc.listar_todos_candidatos(EMPRESA, page=p, page_size=20).conteo_por_grupo
                   for p in (1, 2, 3)]

        assert conteos[0] == {"Analista SSR": 28, "Dev Backend": 15, "Búsqueda vieja": 7}
        assert conteos[1] == conteos[0]
        assert conteos[2] == conteos[0]

    def test_y_la_suma_del_conteo_es_el_total(self, svc_candidatos) -> None:
        """Contracara: si un grupo se perdiera en el camino, los conteos seguirían siendo
        estables entre páginas y el test de arriba pasaría igual."""
        svc, _ = svc_candidatos
        pagina = svc.listar_todos_candidatos(EMPRESA, page=1, page_size=20)

        assert sum(pagina.conteo_por_grupo.values()) == pagina.total == 50

    def test_el_grupo_de_una_pagina_donde_NO_aparece_igual_se_cuenta(self, svc_candidatos) -> None:
        """La página 3 trae 10 filas y ningún candidato de 'Analista SSR' (se agotó en la 2).
        Su conteo tiene que seguir estando: el encabezado de una búsqueda no depende de que
        alguno de sus candidatos haya caído en la página que se está mirando."""
        svc, _ = svc_candidatos
        p3 = svc.listar_todos_candidatos(EMPRESA, page=3, page_size=20)

        assert all(c.grupo_nombre != "Analista SSR" for c in p3.items)
        assert p3.conteo_por_grupo["Analista SSR"] == 28

    def test_una_sola_query_de_vacantes_para_la_pagina_Y_el_conteo(self, svc_candidatos) -> None:
        """El conteo por grupo necesita los títulos vivos igual que la página. Pedirlos dos
        veces sería el N+1 que este service ya evitaba, con otra cara."""
        svc, vac = svc_candidatos
        svc.listar_todos_candidatos(EMPRESA, page=3, page_size=20)

        assert len(vac.pedidos) == 1
        # Y pide los DOS, no sólo el de la página: en la 3 no hay ninguno de _V1, pero su
        # conteo lo necesita para nombrarse.
        assert vac.pedidos[0] == sorted([str(_V1), str(_V2)])


class TestCadaFilaExactamenteUnaVez:

    def test_recorriendo_las_tres_paginas_no_falta_ni_se_repite_nadie(self, svc_candidatos) -> None:
        """🔴 CON LAS 50 FILAS EMPATADAS EN `created_at`. Sin el desempate por `id`, Postgres
        puede devolver los empates en otro orden en cada OFFSET: alguien sale dos veces y otro
        no sale nunca, sin ningún error visible."""
        svc, _ = svc_candidatos
        vistos = [c.id for p in (1, 2, 3)
                  for c in svc.listar_todos_candidatos(EMPRESA, page=p, page_size=20).items]

        assert len(vistos) == 50
        assert len(set(vistos)) == 50, "hay filas repetidas entre páginas"

    def test_los_tamanos_de_pagina_son_los_esperados(self, svc_candidatos) -> None:
        """Guarda contra el falso verde del test de arriba: si el doble no recortara, las tres
        páginas traerían 50 cada una y el `set` de 50 pasaría igual."""
        svc, _ = svc_candidatos
        largos = [len(svc.listar_todos_candidatos(EMPRESA, page=p, page_size=20).items)
                  for p in (1, 2, 3)]

        assert largos == [20, 20, 10]

    def test_total_pages_coherente(self, svc_candidatos) -> None:
        svc, _ = svc_candidatos
        p1 = svc.listar_todos_candidatos(EMPRESA, page=1, page_size=20)

        assert (p1.total, p1.page, p1.page_size, p1.total_pages) == (50, 1, 20, 3)


class TestFiltroYPaginacionSeComponen:

    def test_el_filtro_acota_el_total_y_el_conteo(self, svc_candidatos) -> None:
        """`sin_vacante` deja 7. El conteo por grupo tiene que hablar del conjunto FILTRADO, no
        del catálogo: si mirara la tabla entera, el encabezado diría 28 sobre una pantalla en la
        que no hay ni un candidato de esa búsqueda."""
        svc, _ = svc_candidatos
        pagina = svc.listar_todos_candidatos(EMPRESA, sin_vacante=True, page=1, page_size=20)

        assert pagina.total == 7
        assert pagina.conteo_por_grupo == {"Búsqueda vieja": 7}


# ══════════════════════════════════════════════════════════════════════════════
# EVALUADOS — los tres filtros que bajaron del cliente al WHERE
# ══════════════════════════════════════════════════════════════════════════════

_LOTE = "22222222-2222-2222-2222-222222222222"

# 50 evaluados ordenados por apellido. UNO SOLO es de "Logística" y su apellido lo manda al
# final: con page_size 20 cae en la página 3. Es el caso exacto que el filtro en el cliente no
# podía resolver — buscaba dentro de las 20 filas que ya estaban a la vista.
_SECTOR_RARO, _APELLIDO_RARO = "Logística", "Zurita"


def _evaluados() -> list:
    filas = []
    for i in range(49):
        filas.append({
            "id": f"{i:08d}-2222-2222-2222-222222222222", "lote_id": _LOTE,
            "created_at": "2026-08-01T09:00:00",
            "empleado_id": f"{i:08d}-3333-3333-3333-333333333333",
            "apellido_evaluado": f"Alvarez{i:02d}", "nombre_evaluado": "Ana",
            "perfil": "general", "sector": "Ventas", "nota_final": 7.0,
            "organismo": None, "gerencia": None,
            "apellido_superior": None, "nombre_superior": None,
        })
    filas.append({
        "id": "99999999-2222-2222-2222-222222222222", "lote_id": _LOTE,
        "created_at": "2026-08-01T09:00:00",
        "empleado_id": "99999999-3333-3333-3333-333333333333",
        "apellido_evaluado": _APELLIDO_RARO, "nombre_evaluado": "Zoe",
        "perfil": "lider", "sector": _SECTOR_RARO, "nota_final": None,
        "organismo": None, "gerencia": None,
        "apellido_superior": None, "nombre_superior": None,
    })
    return filas


@pytest.fixture
def svc_evaluados(monkeypatch):
    import repositories._evaluacion_evaluados_repo as repo_mod
    from services.evaluacion_reportes_service import EvaluacionReportesService

    monkeypatch.setattr(repo_mod, "supabase_admin", _cliente(_evaluados()))

    class _Repo:
        """El repo real para evaluados (que es el que se está probando) y dobles mínimos para
        lo que el service consulta al costado: el lote (barrera de empresa) y los resultados."""

        def find_lote_by_id(self, lote_id):
            from types import SimpleNamespace
            return SimpleNamespace(id=lote_id, empresa_id=EMPRESA)

        def find_evaluados_pagina(self, *a, **k):
            return repo_mod.find_evaluados_pagina(*a, **k)

        def sectores_del_lote(self, lote_id):
            return repo_mod.sectores_del_lote(lote_id)

        def find_resultados_por_evaluados(self, ids):
            return []

    return EvaluacionReportesService(repo=_Repo())


class TestFiltrarPorSectorEncuentraLaPagina3:

    def test_el_unico_de_Logistica_esta_en_la_pagina_3_sin_filtro(self, svc_evaluados) -> None:
        """Primero la premisa. Sin esto, el test de abajo podría pasar porque la persona estaba
        en la página 1 desde el principio y el filtro no hizo nada."""
        p1 = svc_evaluados.listado(UUID(_LOTE), EMPRESA, page=1, page_size=20)
        p3 = svc_evaluados.listado(UUID(_LOTE), EMPRESA, page=3, page_size=20)

        assert all(i.apellido != _APELLIDO_RARO for i in p1.items)
        # Último de la página 3: el apellido lo manda al final del orden alfabético.
        assert p3.items[-1].apellido == _APELLIDO_RARO

    def test_filtrar_por_sector_LO_ENCUENTRA_desde_la_pagina_1(self, svc_evaluados) -> None:
        """🔴 EL TEST QUE SOSTIENE LA FEATURE. Con el filtro en el cliente, pedir 'Logística'
        filtraba las 20 filas de la página 1 —todas de Ventas— y la pantalla quedaba vacía
        sobre un sector que sí tiene gente."""
        pagina = svc_evaluados.listado(UUID(_LOTE), EMPRESA, sector=_SECTOR_RARO,
                                       page=1, page_size=20)

        assert [i.apellido for i in pagina.items] == [_APELLIDO_RARO]
        assert pagina.total == 1
        assert pagina.total_pages == 1

    def test_los_otros_dos_filtros_tambien_van_al_WHERE(self, svc_evaluados) -> None:
        """`perfil` y `con_nota` recorren el mismo camino, y el evaluado raro es el único que
        los satisface: si alguno se aplicara sobre la página, la 1 volvería vacía."""
        por_perfil = svc_evaluados.listado(UUID(_LOTE), EMPRESA, perfil="lider",
                                           page=1, page_size=20)
        sin_nota = svc_evaluados.listado(UUID(_LOTE), EMPRESA, con_nota="no",
                                         page=1, page_size=20)

        assert [i.apellido for i in por_perfil.items] == [_APELLIDO_RARO]
        assert [i.apellido for i in sin_nota.items] == [_APELLIDO_RARO]

    def test_con_nota_si_devuelve_los_OTROS_49(self, svc_evaluados) -> None:
        """La contracara de `con_nota="no"`. Sin ella, un filtro que devolviera siempre la fila
        rara pasaría los dos tests de arriba."""
        pagina = svc_evaluados.listado(UUID(_LOTE), EMPRESA, con_nota="si", page=1, page_size=20)

        assert pagina.total == 49
        assert _APELLIDO_RARO not in [i.apellido for i in pagina.items]

    def test_las_opciones_de_sector_son_las_del_LOTE_no_las_de_la_pagina(self, svc_evaluados) -> None:
        """El desplegable de la página 1 tiene que ofrecer 'Logística' aunque en esa página no
        aparezca nadie de ese sector. Si saliera de `items`, la opción no existiría y filtrar
        por ella sería imposible desde la UI."""
        p1 = svc_evaluados.listado(UUID(_LOTE), EMPRESA, page=1, page_size=20)

        assert all(i.sector != _SECTOR_RARO for i in p1.items)
        assert p1.sectores == ["Logística", "Ventas"]


class TestEvaluadosCadaFilaUnaVez:

    def test_recorriendo_las_tres_paginas_no_falta_ni_se_repite_nadie(self, svc_evaluados) -> None:
        vistos = [i.id for p in (1, 2, 3)
                  for i in svc_evaluados.listado(UUID(_LOTE), EMPRESA, page=p,
                                                 page_size=20).items]

        assert len(vistos) == 50
        assert len(set(vistos)) == 50, "hay filas repetidas entre páginas"

    def test_los_tamanos_de_pagina_son_los_esperados(self, svc_evaluados) -> None:
        """Guarda contra el falso verde: sin recorte serían 50/50/50 y el set pasaría igual."""
        largos = [len(svc_evaluados.listado(UUID(_LOTE), EMPRESA, page=p, page_size=20).items)
                  for p in (1, 2, 3)]

        assert largos == [20, 20, 10]

    def test_el_filtro_y_la_pagina_se_componen_sin_pisarse(self, svc_evaluados) -> None:
        """49 filas de Ventas en páginas de 20: 20 + 20 + 9, y el total dice 49 en las tres."""
        paginas = [svc_evaluados.listado(UUID(_LOTE), EMPRESA, sector="Ventas", page=p,
                                         page_size=20) for p in (1, 2, 3)]

        assert [len(p.items) for p in paginas] == [20, 20, 9]
        assert {p.total for p in paginas} == {49}
        assert len({i.id for p in paginas for i in p.items}) == 49
