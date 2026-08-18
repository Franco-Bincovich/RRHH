"""
Filtro por proyecto en empleados, vacaciones, ausencias y evaluaciones.

La resolución es la misma en los cuatro: proyecto → `proyecto_asignaciones` → empleados. Lo
que cambia es dónde se aplica, y eso es lo que separa los bloques de este archivo.

🔴 EL BLOQUE QUE MÁS IMPORTA ES TestTresEjes. En vacaciones y ausencias el filtro convive con
el ownership de `mandos_medios` y con el filtro de área, y los tres tienen que componerse por
INTERSECCIÓN. Un bug ahí no rompe nada visible: devuelve filas de empleados que ese rol no
debería ver. Por eso se prueba cada eje vacío por separado (fail-closed) además de la
composición: son tres formas distintas de que el resultado tenga que ser vacío, y cualquiera
de las tres devolviendo "sin filtro" abre datos ajenos.
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

from uuid import uuid4

import pytest
from types import SimpleNamespace

import repositories._scope_filtros as scope
from services._ownership_filter import resolver_filtro_empleados

PROY_A, PROY_B, PROY_VACIO = uuid4(), uuid4(), uuid4()
AREA = uuid4()

# proyecto → empleados asignados
ASIGNACIONES = {
    str(PROY_A): ["jefe", "sub", "ajeno"],
    str(PROY_B): ["ajeno"],
    str(PROY_VACIO): [],
}


class _Query:
    def __init__(self, tabla, contador):
        self.tabla, self.contador, self.filtros = tabla, contador, {}

    def select(self, *_a, **_k): return self

    def eq(self, col, val):
        self.filtros[col] = val
        return self

    def execute(self):
        self.contador[self.tabla] = self.contador.get(self.tabla, 0) + 1
        pid = self.filtros.get("proyecto_id")
        return type("R", (), {"data": [{"empleado_id": e} for e in ASIGNACIONES.get(pid, [])]})()


@pytest.fixture
def cliente(monkeypatch):
    contador: dict = {}
    monkeypatch.setattr(scope, "supabase_admin",
                        type("C", (), {"table": staticmethod(lambda t: _Query(t, contador))})())
    return contador


# ─── La resolución ────────────────────────────────────────────────────────────


class TestEmpleadosDeProyecto:
    def test_devuelve_los_asignados(self, cliente) -> None:
        assert sorted(scope.empleados_de_proyecto(PROY_A)) == ["ajeno", "jefe", "sub"]

    def test_no_devuelve_los_de_otro_proyecto(self, cliente) -> None:
        assert scope.empleados_de_proyecto(PROY_B) == ["ajeno"]

    def test_proyecto_sin_asignados_da_lista_vacia(self, cliente) -> None:
        assert scope.empleados_de_proyecto(PROY_VACIO) == []

    def test_una_sola_query(self, cliente) -> None:
        scope.empleados_de_proyecto(PROY_A)
        assert cliente == {"proyecto_asignaciones": 1}

    def test_no_repite_ids(self, cliente) -> None:
        ids = scope.empleados_de_proyecto(PROY_A)
        assert len(ids) == len(set(ids))


# ─── Los tres ejes en vacaciones / ausencias ──────────────────────────────────


class _Own:
    """Mando 'jefe' con un subordinado. 'ajeno' NO es suyo."""

    def find_by_user_id(self, user_id):
        return {"id": "jefe"} if user_id == "jefe" else None

    def ids_subordinados(self, empleado_id):
        return ["sub"] if empleado_id == "jefe" else []

    def ids_empleados_por_area(self, empresa_id, area_id):
        return ["jefe", "ajeno"] if area_id else []


def _resolver(rol="mandos_medios", area_id=None, proyecto_ids=None):
    return resolver_filtro_empleados("jefe", rol, None, area_id, _Own(), proyecto_ids)


class TestTresEjes:
    """ownership ∩ área ∩ proyecto. Cada uno acota; ninguno reemplaza a otro."""

    def test_solo_ownership(self) -> None:
        ids, vacio = _resolver()
        assert vacio is False and sorted(ids) == ["jefe", "sub"]

    def test_ownership_interseca_proyecto(self) -> None:
        """'ajeno' está en el proyecto pero NO es subordinado: no puede entrar."""
        ids, vacio = _resolver(proyecto_ids=["jefe", "sub", "ajeno"])
        assert vacio is False and sorted(ids) == ["jefe", "sub"]

    def test_el_proyecto_acota_dentro_del_ownership(self) -> None:
        """'sub' es subordinado pero no está en el proyecto: tampoco entra."""
        ids, vacio = _resolver(proyecto_ids=["jefe", "ajeno"])
        assert vacio is False and ids == ["jefe"]

    def test_los_tres_ejes_juntos(self) -> None:
        """ownership {jefe,sub} ∩ área {jefe,ajeno} ∩ proyecto {jefe,sub,ajeno} = {jefe}."""
        ids, vacio = _resolver(area_id=AREA, proyecto_ids=["jefe", "sub", "ajeno"])
        assert vacio is False and ids == ["jefe"]

    def test_admin_con_proyecto_no_gana_ownership_pero_si_acota(self) -> None:
        """Un admin no tiene restricción de ownership, pero el proyecto igual lo acota."""
        ids, vacio = _resolver(rol="admin_rrhh", proyecto_ids=["ajeno"])
        assert vacio is False and ids == ["ajeno"]

    def test_admin_sin_filtros_ve_todo(self) -> None:
        assert _resolver(rol="admin_rrhh") == (None, False)


class TestFailClosedPorEje:
    """🔴 Tres formas distintas de tener que dar vacío. Si alguna devolviera (None, False)
    —'sin restricción'— el listado mostraría empleados ajenos sin ningún error."""

    def test_ownership_vacio(self) -> None:
        """Un mando sin subordinados."""
        class _SinSubs(_Own):
            def ids_subordinados(self, empleado_id): return []
            def find_by_user_id(self, user_id): return None
        assert resolver_filtro_empleados("nadie", "mandos_medios", None, None, _SinSubs()) == (None, True)

    def test_area_vacia(self) -> None:
        class _SinArea(_Own):
            def ids_empleados_por_area(self, empresa_id, area_id): return []
        assert resolver_filtro_empleados("jefe", "mandos_medios", None, AREA, _SinArea()) == (None, True)

    def test_proyecto_vacio(self) -> None:
        """Proyecto sin asignados: [] es 'nadie', NO 'sin filtro'."""
        assert _resolver(proyecto_ids=[]) == (None, True)

    def test_interseccion_vacia(self) -> None:
        """Cada eje tiene gente, pero no comparten a nadie: ownership {jefe,sub} ∩ proyecto
        {otro-mas} = ∅. Vacío, no 'sin filtro'."""
        assert _resolver(proyecto_ids=["otro-mas"]) == (None, True)

    def test_proyecto_vacio_gana_sobre_admin(self) -> None:
        """Ni siquiera un admin ve todo si el proyecto no tiene a nadie."""
        assert _resolver(rol="admin_rrhh", proyecto_ids=[]) == (None, True)


# ─── Evaluaciones: el evaluado sin empleado ───────────────────────────────────


class TestEvaluadosSinEmpleado:
    """`evaluacion_evaluados.empleado_id` es NULLABLE: 'sin_candidato' es un estado válido
    (el CSV trae solo nombre y no matcheó). En producción hay 1 de 10 así.

    🔴 BAJÓ UN ESCALÓN EL 15/8/2026: estas cuatro definiciones se verificaban contra `_pasa`,
    el predicado de Python del service. Al mudarse los filtros al WHERE ese predicado se borró,
    y las definiciones ahora las sostiene `.in_("empleado_id", ids)`. Se verifican sobre el
    RESULTADO DE LA QUERY, con un doble que aplica la semántica de SQL: un NULL nunca satisface
    un `IN`. Ese detalle es exactamente lo que hace que la regla siga valiendo sin código propio
    — y también lo que la volvería invisible si el doble tratara `None` como un valor más.
    """

    class _Tabla:
        """Doble de la tabla con semántica SQL de `IN` sobre NULL."""

        # Filas completas (el repo las valida contra `EvaluadoResponse`), con `empleado_id`
        # como única diferencia: es la columna que este filtro mira.
        _BASE = {"lote_id": "00000000-0000-0000-0000-0000000000aa",
                 "created_at": "2026-08-15T10:00:00", "perfil": "general",
                 "apellido_evaluado": "Pérez", "nombre_evaluado": "Ana"}
        FILAS = [dict(_BASE, id="00000000-0000-0000-0000-000000000001",
                      empleado_id="00000000-0000-0000-0000-0000000000e1"),
                 dict(_BASE, id="00000000-0000-0000-0000-000000000002",
                      empleado_id="00000000-0000-0000-0000-0000000000e2"),
                 dict(_BASE, id="00000000-0000-0000-0000-000000000003", empleado_id=None)]

        def __init__(self) -> None:
            self.filas, self.conto = list(self.FILAS), False

        def select(self, *_a, **k):
            self.conto = k.get("count") == "exact"
            return self

        def eq(self, *_a):
            return self

        def order(self, *_a, **_k):
            return self

        def range(self, *_a):
            return self

        def in_(self, col, valores):
            # 🔑 `f.get(col) in valores` con f.get(col) = None y valores = [] daría False, pero
            # con valores = [None] daría True — y SQL diría FALSE igual. Por eso el `is not None`
            # explícito: la exclusión del NULL no puede depender de qué contenga la lista.
            self.filas = [f for f in self.filas
                          if f.get(col) is not None and f.get(col) in valores]
            return self

        def execute(self):
            return type("R", (), {"data": list(self.filas),
                                  "count": len(self.filas) if self.conto else None})()

    E1 = "00000000-0000-0000-0000-0000000000e1"

    def _ids(self, monkeypatch, empleado_ids):
        import repositories._evaluacion_evaluados_repo as repo_mod
        tabla = self._Tabla()
        monkeypatch.setattr(repo_mod, "supabase_admin",
                            type("C", (), {"table": staticmethod(lambda _t: tabla)})())
        filas, _total = repo_mod.find_evaluados_pagina("lote-1", empleado_ids=empleado_ids)
        return [str(f.empleado_id)[-2:] if f.empleado_id else None for f in filas]

    def test_sin_empleado_queda_excluido_al_filtrar_por_proyecto(self, monkeypatch) -> None:
        """No se lo puede atribuir a ningún proyecto — igual que el proyecto sin asignados
        de B3 no aparece bajo ninguna área."""
        assert self._ids(monkeypatch, [self.E1]) == ["e1"]

    def test_sin_empleado_aparece_cuando_no_se_filtra_por_proyecto(self, monkeypatch) -> None:
        """Excluirlo siempre sería otro bug: el estado es válido y tiene que verse. `None`
        significa NO EMITIR el filtro, y por eso las tres filas vuelven."""
        assert self._ids(monkeypatch, None) == ["e1", "e2", None]

    def test_con_empleado_de_otro_proyecto_no_entra(self, monkeypatch) -> None:
        assert self._ids(monkeypatch, [self.E1]) == ["e1"]

    def test_proyecto_sin_asignados_no_deja_pasar_a_nadie(self, monkeypatch) -> None:
        """La lista vacía filtra a NADIE, ni siquiera al que no tiene empleado."""
        assert self._ids(monkeypatch, []) == []


# ─── El CABLEADO: que los módulos usen la resolución, no solo que exista ──────
# El resolver puede estar perfecto y el módulo no llamarlo. Es el hueco que la primera
# pasada de mutación dejó vivo en B3 y volvió a aparecer acá: hay que mirar los dos extremos.


class _QueryEmp:
    def __init__(self, registro):
        self.registro = registro

    def select(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def or_(self, *_a, **_k): return self
    def range(self, *_a, **_k): return self
    # No-op encadenable por el mismo motivo que `order`: lo pide el default de estado del
    # listado (`.neq("estado","preingreso")`), y este fake audita el filtro por PROYECTO. El
    # default de estado tiene su propio archivo, tests/test_estado_preingreso_lecturas.py.
    def neq(self, *_a, **_k): return self
    # No-op encadenable a proposito: este fake audita el filtro por proyecto, no el
    # orden. El orden se prueba en tests/test_paginacion_orden.py, con un fake que ordena.
    def order(self, *_a, **_k): return self

    def in_(self, col, ids):
        self.registro["in_"] = (col, list(ids))
        return self

    def execute(self):
        return type("R", (), {"data": [], "count": 0})()


class TestCableadoEmpleados:
    def _find_all(self, monkeypatch, **kw) -> dict:
        import repositories.empleado_repo as repo_mod
        registro: dict = {}
        monkeypatch.setattr(repo_mod, "supabase_admin",
                            type("C", (), {"table": staticmethod(lambda t: _QueryEmp(registro))})())
        repo_mod.EmpleadoRepo().find_all(1, 20, **kw)
        return registro

    def test_con_proyecto_acota_por_id(self, monkeypatch) -> None:
        reg = self._find_all(monkeypatch, proyecto_ids=["e1", "e2"])
        assert reg["in_"] == ("id", ["e1", "e2"])

    def test_sin_proyecto_no_acota(self, monkeypatch) -> None:
        assert "in_" not in self._find_all(monkeypatch)

    def test_proyecto_sin_asignados_acota_a_nadie(self, monkeypatch) -> None:
        """[] tiene que llegar como .in_("id", []) — 'nadie', no 'sin filtro'."""
        assert self._find_all(monkeypatch, proyecto_ids=[])["in_"] == ("id", [])


class TestCableadoEvaluaciones:
    """Que el service RESUELVA el proyecto y le pase los ids AL REPO.

    🔴 CAMBIÓ DE ESCALÓN EL 15/8/2026, por el mismo motivo que la clase de arriba: antes se
    miraba que el proyecto llegara a un predicado de Python que filtraba la lista ya traída.
    Con 1.005 evaluados por lote, filtrar en memoria significa que el filtro sólo encuentra a
    quien ya estaba en la página que se está mirando. Ahora se mira el ARGUMENTO que recibe
    el repo, que es lo que termina en el WHERE.
    """

    class _Repo:
        """Registra los ids de proyecto que le llegan. Devuelve vacío a propósito: lo que se
        afirma es el argumento, no el resultado, y un catálogo de filas no agregaría nada."""

        def __init__(self) -> None:
            self.recibido: list = []

        def find_lote_by_id(self, lote_id):
            return SimpleNamespace(id=lote_id, empresa_id=None)

        def find_evaluados_pagina(self, lote_id, page=1, page_size=20, sector=None,
                                  perfil=None, con_nota=None, empleado_ids=None):
            self.recibido.append(empleado_ids)
            return [], 0

        def find_resultados_por_evaluados(self, ids):
            return []

        def sectores_del_lote(self, lote_id):
            return []

    def _listar(self, monkeypatch, proyecto_id, empleados=("emp-1",)):
        import services.evaluacion_reportes_service as svc_mod
        monkeypatch.setattr(svc_mod, "empleados_de_proyecto", lambda p: list(empleados))
        repo = self._Repo()
        svc_mod.EvaluacionReportesService(repo=repo).listado(uuid4(), None, proyecto_id=proyecto_id)
        return repo.recibido

    def test_con_proyecto_los_ids_LLEGAN_AL_REPO(self, monkeypatch) -> None:
        assert self._listar(monkeypatch, uuid4()) == [["emp-1"]]

    def test_sin_proyecto_el_repo_recibe_None(self, monkeypatch) -> None:
        """`None`, no `[]`: son cosas distintas en el WHERE. `[]` es `.in_("empleado_id", [])`,
        o sea NADIE; `None` es no emitir el filtro. Confundirlos vacía el listado entero."""
        assert self._listar(monkeypatch, None) == [None]

    def test_proyecto_sin_asignados_llega_como_lista_vacia(self, monkeypatch) -> None:
        """Un proyecto real sin nadie asignado tiene que filtrar a NADIE, no a todos."""
        assert self._listar(monkeypatch, uuid4(), empleados=()) == [[]]

    def test_con_proyecto_resuelve_los_empleados(self, monkeypatch) -> None:
        """Y que la resolución se haga UNA vez, con el id que vino del router."""
        import services.evaluacion_reportes_service as svc_mod
        llamado: list = []
        monkeypatch.setattr(svc_mod, "empleados_de_proyecto",
                            lambda p: llamado.append(p) or ["emp-1"])
        pid = uuid4()
        svc_mod.EvaluacionReportesService(repo=self._Repo()).listado(uuid4(), None, proyecto_id=pid)
        assert llamado == [pid]

    def test_sin_proyecto_no_resuelve_nada(self, monkeypatch) -> None:
        import services.evaluacion_reportes_service as svc_mod
        llamado: list = []
        monkeypatch.setattr(svc_mod, "empleados_de_proyecto", lambda p: llamado.append(p) or [])
        svc_mod.EvaluacionReportesService(repo=self._Repo()).listado(uuid4(), None)
        assert llamado == []
