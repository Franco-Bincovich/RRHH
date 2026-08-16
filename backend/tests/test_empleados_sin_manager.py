"""
Filtro `sin_manager` del listado de empleados — el destino al que linkea la alerta agregada
del dashboard ("N empleados sin superior asignado").

🔑 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR

`TestElPredicadoLoPoneLaQuery` NO usa un repo espía: un espía solo probaría que el parámetro
viaja del router al repo, que es exactamente el falso positivo que la Fase 2 encontró tres
veces. Acá el doble es el CLIENTE de Supabase y captura los `.is_()` / `.not_.is_()` reales,
así que si alguien reemplaza el predicado por un `.eq("manager_id", None)` —que en PostgREST
no matchea nada— el test se pone rojo. Molde: `TestElOrdenLoPoneLaQuery` de
test_historial_salarial.py y `TestElWhereDelRepoLlevaLaEmpresa` de test_offboarding_entrevista.py.

`TestListadoYExportMandanLoMismo` usa un espía a propósito: ahí lo que se verifica es el
recorrido service→repo por los DOS caminos, no la forma del WHERE.

El fake de la query modela DOS empresas y honra el `.eq("empresa_id", ...)`: sin eso, el test
de composición pasaría con la barrera de empresa borrada.
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

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import repositories.empleado_repo as empleado_repo_mod
from repositories.empleado_repo import EmpleadoRepo
from services.empleado_service import EmpleadoService

EMPRESA_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EMPRESA_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
AREA = uuid4()

# Padrón sintético de DOS empresas. Los de A: dos sin superior, uno con.
_FILAS = [
    {"id": "a1", "empresa_id": str(EMPRESA_A), "manager_id": None,  "nombre": "Ana",  "apellido": "Gómez"},
    {"id": "a2", "empresa_id": str(EMPRESA_A), "manager_id": None,  "nombre": "Beto", "apellido": "Ruiz"},
    {"id": "a3", "empresa_id": str(EMPRESA_A), "manager_id": "a1",  "nombre": "Caro", "apellido": "Díaz"},
    {"id": "b1", "empresa_id": str(EMPRESA_B), "manager_id": None,  "nombre": "Dani", "apellido": "Sosa"},
]


class _Not:
    """El `.not_` de postgrest: devuelve un proxy cuyo `.is_()` niega el predicado."""
    def __init__(self, q: "_Query") -> None:
        self._q = q

    def is_(self, col: str, val: str) -> "_Query":
        return self._q._registrar(col, val, negado=True)


class _Query:
    """Fake del query builder. Aplica de verdad `eq` e `is/not.is` sobre las filas."""
    def __init__(self, filas: list, capturado: dict) -> None:
        self._filas, self._cap = filas, capturado
        self._eq: dict = {}
        self._nulos: list = []          # (columna, negado)

    @property
    def not_(self) -> _Not:
        return _Not(self)

    def _registrar(self, col: str, val: str, negado: bool) -> "_Query":
        assert val == "null", f"is_() se usa para nulos; llegó {val!r}"
        self._nulos.append((col, negado))
        self._cap.setdefault("nulos", []).append((col, negado))
        return self

    def is_(self, col: str, val: str) -> "_Query":
        return self._registrar(col, val, negado=False)

    def select(self, *_a, **_k) -> "_Query":
        return self

    def eq(self, col: str, val) -> "_Query":
        self._eq[col] = str(val)
        self._cap.setdefault("eq", {})[col] = str(val)
        return self

    def or_(self, *_a, **_k) -> "_Query":
        return self

    def in_(self, *_a, **_k) -> "_Query":
        return self

    def range(self, *_a, **_k) -> "_Query":
        return self

    def order(self, *_a, **_k):
        # No-op ENCADENABLE y permisivo A PROPOSITO: este fake audita el PREDICADO de la
        # query, no su orden ni su paginacion (`range` ya es no-op por lo mismo). El orden
        # tiene su propio archivo, tests/test_paginacion_orden.py, con un fake que si ordena.
        return self

    def _match(self, fila: dict) -> bool:
        if any(str(fila.get(c)) != v for c, v in self._eq.items()):
            return False
        for col, negado in self._nulos:
            es_nulo = fila.get(col) is None
            if es_nulo is negado:       # negado=True exige NO nulo, y viceversa
                return False
        return True

    def execute(self):
        data = [f for f in self._filas if self._match(f)]
        return SimpleNamespace(data=data, count=len(data))


class _FakeDB:
    def __init__(self, capturado: dict) -> None:
        self._cap = capturado

    def table(self, _name: str) -> _Query:
        return _Query(_FILAS, self._cap)


def _fake_row(r: dict) -> dict:
    """El mapper real construye un EmpleadoResponse; acá alcanza con la fila cruda."""
    return r


@pytest.fixture
def cap(monkeypatch) -> dict:
    capturado: dict = {}
    monkeypatch.setattr(empleado_repo_mod, "supabase_admin", _FakeDB(capturado))
    monkeypatch.setattr(empleado_repo_mod, "row", _fake_row)
    return capturado


class TestElPredicadoLoPoneLaQuery:
    def test_true_pide_manager_id_nulo(self, cap: dict) -> None:
        EmpleadoRepo().find_all(1, 20, sin_manager=True)
        assert cap["nulos"] == [("manager_id", False)]

    def test_false_pide_manager_id_no_nulo(self, cap: dict) -> None:
        """`False` no es 'sin filtro': es el complemento, y va por `.not_.is_()`."""
        EmpleadoRepo().find_all(1, 20, sin_manager=False)
        assert cap["nulos"] == [("manager_id", True)]

    def test_none_no_toca_la_query(self, cap: dict) -> None:
        EmpleadoRepo().find_all(1, 20, sin_manager=None)
        assert "nulos" not in cap

    def test_el_conteo_coincide_con_las_filas_reales(self, cap: dict) -> None:
        """Es el invariante del que depende la alerta: el número del mensaje y las filas del
        listado salen de la MISMA query. Dos de las tres filas de A no tienen superior."""
        items, total = EmpleadoRepo().find_all(1, 20, empresa_id=EMPRESA_A, sin_manager=True)
        assert total == 2 and {i["id"] for i in items} == {"a1", "a2"}

    def test_complemento_y_filtro_particionan_el_padron(self, cap: dict) -> None:
        """sin_manager=True y sin_manager=False son disjuntos y suman el total sin filtro."""
        _, con = EmpleadoRepo().find_all(1, 20, empresa_id=EMPRESA_A, sin_manager=False)
        _, sin = EmpleadoRepo().find_all(1, 20, empresa_id=EMPRESA_A, sin_manager=True)
        _, todos = EmpleadoRepo().find_all(1, 20, empresa_id=EMPRESA_A)
        assert (con, sin, todos) == (1, 2, 3)


class TestNoCuentaFilasDeOtraEmpresa:
    """La empresa va EN EL WHERE (Forma A). Si el `.eq("empresa_id", ...)` se cayera, este
    test daría 3 en vez de 2: la empresa B tiene su propio empleado sin superior."""

    def test_el_filtro_se_compone_con_la_empresa(self, cap: dict) -> None:
        _, total = EmpleadoRepo().find_all(1, 20, empresa_id=EMPRESA_A, sin_manager=True)
        assert total == 2
        assert cap["eq"]["empresa_id"] == str(EMPRESA_A)

    def test_la_otra_empresa_ve_solo_lo_suyo(self, cap: dict) -> None:
        items, total = EmpleadoRepo().find_all(1, 20, empresa_id=EMPRESA_B, sin_manager=True)
        assert total == 1 and items[0]["id"] == "b1"

    def test_consolidado_ve_las_dos(self, cap: dict) -> None:
        """empresa_id=None NO restringe (vista consolidada) — no es un fallo de validación."""
        _, total = EmpleadoRepo().find_all(1, 20, empresa_id=None, sin_manager=True)
        assert total == 3


class _RepoEspia:
    """Registra los argumentos con los que el service llamó al repo."""
    def __init__(self) -> None:
        self.args: dict = {}

    def find_all(self, page, page_size, empresa_id=None, area_id=None, estado=None,
                 search=None, es_lider=None, proyecto_ids=None, sin_manager=None):
        self.args = {"empresa_id": empresa_id, "area_id": area_id, "estado": estado,
                     "search": search, "es_lider": es_lider, "proyecto_ids": proyecto_ids,
                     "sin_manager": sin_manager}
        return [], 0


class TestListadoYExportMandanLoMismo:
    """Invariante 2 del bloque B. `test_paridad_list_export` ya obliga a que el endpoint de
    export DECLARE el Query param; esto verifica que además lo USE."""

    def _listar(self, **kw) -> dict:
        repo = _RepoEspia()
        EmpleadoService(repo=repo).get_empleados(1, 20, **kw)
        return repo.args

    def _exportar(self, **kw) -> dict:
        repo = _RepoEspia()
        EmpleadoService(repo=repo).exportar(**kw)
        return repo.args

    @pytest.mark.parametrize("valor", [True, False])
    def test_viaja_hasta_el_repo_por_los_dos_caminos(self, valor: bool) -> None:
        assert self._listar(sin_manager=valor)["sin_manager"] is valor
        assert self._exportar(sin_manager=valor)["sin_manager"] is valor

    def test_sin_filtro_llega_como_none(self) -> None:
        assert self._listar()["sin_manager"] is None
        assert self._exportar()["sin_manager"] is None

    def test_mismo_conjunto_de_filtros(self) -> None:
        kw = {"sin_manager": True, "area_id": str(AREA), "estado": "activo", "search": "ana"}
        assert self._exportar(**kw) == self._listar(**kw)

    def test_se_compone_con_los_otros_filtros(self) -> None:
        """AND, no reemplazo: sin superior + área + liderazgo llegan los tres juntos."""
        args = self._listar(sin_manager=True, area_id=str(AREA), es_lider=False)
        assert (args["sin_manager"], args["area_id"], args["es_lider"]) == (True, str(AREA), False)
