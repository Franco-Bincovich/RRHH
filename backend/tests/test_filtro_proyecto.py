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
    (el CSV trae solo nombre y no matcheó). En producción hay 1 de 10 así."""

    def _pasa(self, empleado_id, del_proyecto):
        from schemas.evaluacion_reportes import EvaluadoListadoItem
        from services.evaluacion_reportes_service import _pasa
        item = EvaluadoListadoItem(
            id="x", empleado_id=empleado_id, apellido="P", nombre="A",
            tipos=[], perfil="general", asignado=empleado_id is not None,
        )
        return _pasa(item, None, None, None, del_proyecto)

    def test_sin_empleado_queda_excluido_al_filtrar_por_proyecto(self) -> None:
        """No se lo puede atribuir a ningún proyecto — igual que el proyecto sin asignados
        de B3 no aparece bajo ninguna área."""
        assert self._pasa(None, {"emp-1"}) is False

    def test_sin_empleado_aparece_cuando_no_se_filtra_por_proyecto(self) -> None:
        """Excluirlo siempre sería otro bug: el estado es válido y tiene que verse."""
        assert self._pasa(None, None) is True

    def test_con_empleado_del_proyecto_entra(self) -> None:
        assert self._pasa("emp-1", {"emp-1"}) is True

    def test_con_empleado_de_otro_proyecto_no_entra(self) -> None:
        assert self._pasa("emp-2", {"emp-1"}) is False


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
    """Que el service RESUELVA el proyecto y se lo pase al predicado."""

    def _listar(self, monkeypatch, proyecto_id):
        import services.evaluacion_reportes_service as svc_mod
        visto: dict = {}
        monkeypatch.setattr(svc_mod, "empleados_de_proyecto", lambda p: ["emp-1"])
        monkeypatch.setattr(svc_mod, "_pasa",
                            lambda i, s, p, c, dp=None: visto.setdefault("del_proyecto", dp) or True)
        monkeypatch.setattr(svc_mod.EvaluacionReportesService, "_lote_rows",
                            lambda self, lote_id, empresa_id: ([], []))
        svc_mod.EvaluacionReportesService().listado(uuid4(), None, proyecto_id=proyecto_id)
        return visto

    def test_con_proyecto_resuelve_los_empleados(self, monkeypatch) -> None:
        import services.evaluacion_reportes_service as svc_mod
        llamado: list = []
        monkeypatch.setattr(svc_mod, "empleados_de_proyecto", lambda p: llamado.append(p) or ["emp-1"])
        monkeypatch.setattr(svc_mod.EvaluacionReportesService, "_lote_rows",
                            lambda self, lote_id, empresa_id: ([], []))
        pid = uuid4()
        svc_mod.EvaluacionReportesService().listado(uuid4(), None, proyecto_id=pid)
        assert llamado == [pid]

    def test_sin_proyecto_no_resuelve_nada(self, monkeypatch) -> None:
        import services.evaluacion_reportes_service as svc_mod
        llamado: list = []
        monkeypatch.setattr(svc_mod, "empleados_de_proyecto", lambda p: llamado.append(p) or [])
        monkeypatch.setattr(svc_mod.EvaluacionReportesService, "_lote_rows",
                            lambda self, lote_id, empresa_id: ([], []))
        svc_mod.EvaluacionReportesService().listado(uuid4(), None)
        assert llamado == []
