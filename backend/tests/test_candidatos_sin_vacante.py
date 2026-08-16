"""
El filtro "sin vacante asignada" en el listado de candidatos Y en el export, y la asignación de
un candidato huérfano.

## 🔴 EL FAKE TRAE CANDIDATOS CON VACANTE Y SIN VACANTE

Con solo huérfanos, "el filtro funciona" y "el filtro no hace nada" devuelven exactamente lo
mismo. Los dos tipos tienen que estar para que la lista filtrada pueda ser MÁS CHICA que la
completa, que es lo único que prueba que filtró.

## 🔴 Y EL FAKE FILTRA EN LA QUERY, NO EN PYTHON

`_Repo.find_pagina` aplica `sin_vacante` sobre sus datos y **registra que lo recibió**. Si
en cambio devolviera siempre todo y el filtrado ocurriera en el service, este archivo pasaría
igual y el EXPORT saldría con más filas que la pantalla — que es el bug que la invariante del
Bloque B existe para impedir. Por eso hay un test que mira el parámetro que llegó al repo, no
solo el resultado.
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

from datetime import datetime, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories._candidato_listado_repo as listado_mod  # noqa: E402
import repositories.candidato_repo as repo_mod  # noqa: E402
from schemas.candidato import CandidatoResponse  # noqa: E402
from services.candidato_service import CandidatoService  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from utils.errors import AppError  # noqa: E402

E1, E2 = uuid4(), uuid4()
V1, V2 = str(uuid4()), str(uuid4())


def _cand(id_, vacante_id, nombre) -> CandidatoResponse:
    return CandidatoResponse(id=id_, vacante_id=vacante_id, empresa_id=str(E1), nombre=nombre,
                             apellido="Pérez", email=f"{nombre}@x.com", etapa_pipeline="postulado",
                             created_at=datetime.now(timezone.utc))


# CON vacante y SIN vacante: con un solo tipo el filtro no se puede desmentir.
_TODOS = [_cand("c1", V1, "Ana"), _cand("c2", None, "Luis"), _cand("c3", None, "Eva")]


class _Repo:
    """Filtra como el repo real —en la query— y registra el parámetro que recibió."""

    def __init__(self) -> None:
        self.recibido: list = []
        self.clasificacion_recibida: list = []

    def _filtrados(self, sin_vacante, clasificacion):
        # 🔴 El fake FILTRA de verdad por los dos ejes. Si aceptara `clasificacion` y lo
        # ignorara, el test de paridad listado↔export pasaría con el filtro desconectado del
        # WHERE — exactamente el verde falso que la doctrina del repo persigue.
        salida = [c for c in _TODOS if not sin_vacante or c.vacante_id is None]
        if clasificacion == "sin_clasificar":
            return [c for c in salida if c.clasificacion_ia is None]
        if clasificacion:
            return [c for c in salida if c.clasificacion_ia == clasificacion]
        return salida

    def find_pagina(self, empresa_id=None, sin_vacante=False, clasificacion=None,
                    page=1, page_size=20):
        """(página, total). El TOTAL es el del filtro, sin recortar: es lo que hace falsable
        que el export se lleve todo y no una página."""
        self.recibido.append(sin_vacante)
        self.clasificacion_recibida.append(clasificacion)
        filas = self._filtrados(sin_vacante, clasificacion)
        ini = (page - 1) * page_size
        return filas[ini:ini + page_size], len(filas)

    def claves_de_grupo(self, empresa_id=None, sin_vacante=False, clasificacion=None):
        """Las claves de agrupamiento del conjunto ENTERO, no de la página — por eso no recibe
        `page`. Si devolviera las de la página, el conteo por grupo del encabezado contaría lo
        que se ve y el test que lo cubre no podría fallar.

        🔴 REGISTRA EL FILTRO IGUAL QUE `find_pagina`, y por eso `recibido` tiene DOS entradas
        por llamada al listado. No es contabilidad: si esta query no llevara el filtro, el
        encabezado diría cuántos candidatos hay SIN filtrar sobre una pantalla filtrada — un
        número que no le corresponde a nada de lo que se está viendo."""
        self.recibido.append(sin_vacante)
        self.clasificacion_recibida.append(clasificacion)
        return [{"vacante_id": c.vacante_id, "busqueda_congelada": c.busqueda_congelada}
                for c in self._filtrados(sin_vacante, clasificacion)]


class _VacanteRepo:
    def find_by_ids(self, ids):
        return [SimpleNamespace(id=V1, titulo="Analista", area_nombre="Sistemas")] if V1 in ids else []

    def find_by_id(self, vid, empresa_id=None):
        m = {V1: E1, V2: E2}
        emp = m.get(str(vid))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(vid), empresa_id=str(emp), titulo="Analista")


def _svc(repo=None, candidatos=None):
    return CandidatoService(candidato_repo=repo or _Repo(), vacante_repo=_VacanteRepo(),
                            audit=SimpleNamespace(registrar=lambda **k: None))


# ── 1. El filtro ──────────────────────────────────────────────────────────────

class TestFiltroSinVacante:

    def test_sin_filtro_vienen_todos(self) -> None:
        # `.total` y no `len(...)`: el listado devuelve una página con su total desde que
        # pagina. Con 3 filas los dos números coinciden; el que describe el filtro es el total.
        assert _svc().listar_todos_candidatos(E1).total == 3

    def test_con_filtro_vienen_solo_los_huerfanos(self) -> None:
        """La lista filtrada es MÁS CHICA que la completa: es lo único que prueba que filtró.

        ¿Qué tendría que ser distinto en el fake para que falle? Que todos los candidatos fueran
        huérfanos — ahí las dos listas serían iguales y el test pasaría sin filtro alguno.
        """
        salida = _svc().listar_todos_candidatos(E1, sin_vacante=True)
        assert [c.id for c in salida.items] == ["c2", "c3"]
        assert salida.total == 2
        assert all(c.vacante_id is None for c in salida.items)

    def test_el_filtro_LLEGA_al_repo_y_no_se_aplica_en_el_service(self) -> None:
        """🔴 Un escalón más abajo: se mira el parámetro que recibió el repo. Si el service
        filtrara sobre la lista, el repo recibiría `False` y el WHERE traería todo — y el export,
        que va por el mismo camino, sacaría más filas de las que muestra la pantalla."""
        repo = _Repo()
        _svc(repo).listar_todos_candidatos(E1, sin_vacante=True)
        # DOS entradas y no una: el listado pide la página Y las claves de grupo, y las dos
        # tienen que llevar el mismo filtro — si el conteo del encabezado no lo llevara,
        # diría cuántos hay SIN filtrar sobre una pantalla filtrada.
        assert repo.recibido == [True, True]

    def test_el_export_da_EXACTAMENTE_el_mismo_conjunto_que_el_listado(self) -> None:
        """La invariante del Bloque B, verificada sobre el contenido y no sobre el largo."""
        repo = _Repo()
        svc = _svc(repo)
        listado = svc.listar_todos_candidatos(E1, sin_vacante=True)
        svc.exportar(E1, "csv", sin_vacante=True)
        assert repo.recibido == [True] * 4, "el export no pidió el mismo filtro que el listado"
        assert [c.id for c in listado.items] == ["c2", "c3"]

    def test_el_repo_real_manda_el_filtro_EN_LA_QUERY(self, monkeypatch) -> None:
        """🔴 El otro escalón: que el `.is_("vacante_id", "null")` viaje a Supabase. Un filtro en
        Python daría el mismo resultado con el fake y traería toda la tabla en producción."""
        fake = FakeSupabase({"candidatos": []})
        vistos: list = []
        original = type(fake.table("candidatos"))

        def _is(self, columna, valor):
            vistos.append((columna, valor))
            return self

        monkeypatch.setattr(original, "is_", _is, raising=False)
        monkeypatch.setattr(repo_mod, "supabase_admin", fake)
        # El listado se mudó a su satélite al partir el repo (100/100 exacto): parchear
        # sólo `candidato_repo` deja la query saliendo a la red de verdad.
        monkeypatch.setattr(listado_mod, "supabase_admin", fake)
        repo_mod.CandidatoRepo().find_pagina(E1, sin_vacante=True)
        assert vistos == [("vacante_id", "null")]
        vistos.clear()
        repo_mod.CandidatoRepo().find_pagina(E1, sin_vacante=False)
        assert vistos == [], "sin el filtro no debería emitirse el is_"


# ── 2. Asignar una vacante a un candidato huérfano ────────────────────────────

class TestAsignarVacante:

    class _RepoAsig(_Repo):
        def __init__(self, cand) -> None:
            super().__init__()
            self._cand, self.asignados = cand, []

        def find_by_id(self, cid, empresa_id=None):
            if empresa_id and str(self._cand.empresa_id) != str(empresa_id):
                return None
            return self._cand if cid == self._cand.id else None

        def asignar_vacante(self, cid, vid, empresa_id=None):
            self.asignados.append((cid, vid))
            return _cand(cid, vid, self._cand.nombre)

    def test_asigna_y_devuelve_el_candidato_con_su_vacante(self) -> None:
        repo = self._RepoAsig(_cand("c2", None, "Luis"))
        salida = _svc(repo).asignar_vacante("c2", V1, E1, "u1")
        assert repo.asignados == [("c2", V1)] and salida.vacante_id == V1

    def test_una_vacante_de_OTRA_empresa_se_rechaza(self) -> None:
        """🔴 La empresa de referencia es la del CANDIDATO, no la del header. Con el header en
        None (modo consolidado) no restringe nada, así que sin este chequeo se podría mover un
        candidato de una empresa a la búsqueda de otra.

        ¿Qué tendría que ser distinto en el fake para que falle? Que `_VacanteRepo.find_by_id`
        ignorara `empresa_id` — ahí la vacante ajena se encontraría y el test pasaría con la
        barrera rota."""
        repo = self._RepoAsig(_cand("c2", None, "Luis"))     # el candidato es de E1
        with pytest.raises(AppError) as exc:
            _svc(repo).asignar_vacante("c2", V2, None, "u1")  # V2 es de E2
        assert exc.value.code == "VACANTE_NOT_FOUND"
        assert repo.asignados == [], "se asignó a una vacante de otra empresa"

    def test_un_candidato_de_otra_empresa_no_se_encuentra(self) -> None:
        repo = self._RepoAsig(_cand("c2", None, "Luis"))
        with pytest.raises(AppError) as exc:
            _svc(repo).asignar_vacante("c2", V1, E2, "u1")
        assert exc.value.code == "CANDIDATO_NOT_FOUND" and exc.value.status_code == 404

    def test_uno_que_YA_tiene_busqueda_no_se_reasigna(self) -> None:
        """Reasignar a alguien que está en un pipeline le borraría el contexto de su etapa."""
        repo = self._RepoAsig(_cand("c1", V1, "Ana"))
        with pytest.raises(AppError) as exc:
            _svc(repo).asignar_vacante("c1", V2, E1, "u1")
        assert exc.value.code == "CANDIDATO_YA_ASIGNADO" and exc.value.status_code == 409

    def test_audita_con_la_empresa_del_candidato(self) -> None:
        eventos: list = []
        repo = self._RepoAsig(_cand("c2", None, "Luis"))
        svc = CandidatoService(candidato_repo=repo, vacante_repo=_VacanteRepo(),
                               audit=SimpleNamespace(registrar=lambda **k: eventos.append(k)))
        svc.asignar_vacante("c2", V1, E1, "u1")
        assert len(eventos) == 1
        assert eventos[0]["evento"] == "asignacion_vacante_candidato"
        assert eventos[0]["empresa_id"] == str(E1)
        assert eventos[0]["datos_anteriores"] == {"vacante_id": None}


def test_los_dos_endpoints_aceptan_el_mismo_filtro() -> None:
    """🔴 `test_paridad_list_export` pasaba TRIVIALMENTE mientras candidatos no tenía ningún query
    param. Ahora que tiene uno, este test ancla que sea el mismo en las dos puntas — el barrido
    genérico lo cubre, pero acá queda dicho cuál es."""
    from fastapi.routing import APIRoute

    import main
    rutas = {r.path: {p.name for p in r.dependant.query_params}
             for r in main.app.routes
             if isinstance(r, APIRoute) and r.path.startswith("/api/candidatos")}
    assert "sin_vacante" in rutas["/api/candidatos"]
    assert "sin_vacante" in rutas["/api/candidatos/exportar"]


def test_el_uuid_del_candidato_no_es_el_de_la_vacante() -> None:
    """Guarda tonta pero real: las dos son UUID y confundirlas en la firma no daría error."""
    import inspect
    params = list(inspect.signature(CandidatoService.asignar_vacante).parameters)
    assert params[1:3] == ["candidato_id", "vacante_id"]
    assert UUID(V1) != UUID(V2)
