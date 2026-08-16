"""
Filtro por área en proyectos e inventario.

🔴 LA SEMÁNTICA DE PROYECTOS ES LO QUE FIJAN LA MAYORÍA DE ESTOS TESTS. Un proyecto no tiene
área: tiene gente asignada, y esa gente sí. "Proyectos del área X" significa entonces
"proyectos donde trabaja al menos alguien de X", contando asignaciones activas E INACTIVAS.
De ahí salen dos comportamientos que parecen bugs y no lo son, y por eso están acá explícitos:

  · un proyecto SIN empleados asignados no aparece bajo NINGUNA área;
  · un proyecto de la empresa A con gente de la empresa B SÍ aparece bajo un área de B —
    acotar la búsqueda de empleados por la empresa activa lo rompería en silencio, que es
    justo la "corrección por consistencia" contra la que advierte scope_filtros.

Inventario es el caso simple: mismo camino (área → empleados → asignaciones) y la vigencia ya
viene resuelta porque el listado solo muestra asignaciones sin devolver.

Los dobles interceptan el CLIENTE de Supabase, no el repo, porque lo que hay que verificar es
cuántas queries salen y con qué filtros — un doble de repo no podría ver ninguna de las dos.
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

import repositories._scope_filtros as area_scope

AREA_SISTEMAS, AREA_VENTAS = uuid4(), uuid4()
EMPRESA_A, EMPRESA_B = uuid4(), uuid4()

# Padrón: empleado → (área, empresa). "de_b" es de la empresa B pero del área de Sistemas,
# que es el caso multi-empresa que el modelo soporta a propósito.
EMPLEADOS = {
    "ana":  (AREA_SISTEMAS, EMPRESA_A),
    "beto": (AREA_SISTEMAS, EMPRESA_A),
    "caro": (AREA_VENTAS,   EMPRESA_A),
    "de_b": (AREA_SISTEMAS, EMPRESA_B),
}
# Asignaciones a proyectos: (proyecto, empleado, activo).
# "P_HUERFANO" no está: es el proyecto sin nadie asignado.
ASIGNACIONES = [
    ("P_SISTEMAS", "ana", True),
    ("P_VENTAS", "caro", True),
    ("P_MIXTO", "beto", True), ("P_MIXTO", "caro", True),
    ("P_CROSS", "de_b", True),        # proyecto de A con gente de B
    ("P_VIEJO", "ana", False),        # asignación TERMINADA: el proyecto igual cuenta
]


class _Query:
    """Doble del query builder: acumula filtros y devuelve el padrón que corresponda."""

    def __init__(self, tabla: str, contador: dict) -> None:
        self.tabla, self.contador = tabla, contador
        self.filtros: dict = {}
        self.in_ids: tuple | None = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filtros[col] = val
        return self

    def in_(self, col, ids):
        self.in_ids = (col, list(ids))
        return self

    def execute(self):
        self.contador[self.tabla] = self.contador.get(self.tabla, 0) + 1
        return _Res(self._filas())

    def _filas(self) -> list:
        if self.tabla == "empleados":
            area = self.filtros.get("area_id")
            empresa = self.filtros.get("empresa_id")
            return [{"id": e} for e, (a, emp) in EMPLEADOS.items()
                    if str(a) == area and (empresa is None or str(emp) == empresa)]
        if self.tabla == "proyecto_asignaciones":
            _, ids = self.in_ids
            activo = self.filtros.get("activo")
            return [{"proyecto_id": p} for p, e, act in ASIGNACIONES
                    if e in ids and (activo is None or act == activo)]
        return []


class _Res:
    # `count` acompaña a `data` desde que los listados piden `count="exact"`: el repo lo lee de
    # la MISMA respuesta. Default `None` para los caminos que no lo piden (el repo hace `or 0`).
    def __init__(self, data, count=None): self.data, self.count = data, count


@pytest.fixture
def cliente(monkeypatch):
    """Reemplaza supabase_admin dentro de scope_filtros y cuenta las queries por tabla."""
    contador: dict = {}
    monkeypatch.setattr(area_scope, "supabase_admin",
                        type("C", (), {"table": staticmethod(lambda t: _Query(t, contador))})())
    return contador


# ─── Proyectos ────────────────────────────────────────────────────────────────


class TestProyectosPorArea:
    def test_proyecto_con_empleado_del_area_aparece(self, cliente) -> None:
        assert "P_SISTEMAS" in area_scope.proyecto_ids_con_area(AREA_SISTEMAS)

    def test_proyecto_de_otra_area_no_aparece(self, cliente) -> None:
        assert "P_VENTAS" not in area_scope.proyecto_ids_con_area(AREA_SISTEMAS)

    def test_proyecto_mixto_aparece_en_las_dos_areas(self, cliente) -> None:
        """Tiene gente de Sistemas y de Ventas: "al menos uno" lo hace visible en ambas."""
        assert "P_MIXTO" in area_scope.proyecto_ids_con_area(AREA_SISTEMAS)
        assert "P_MIXTO" in area_scope.proyecto_ids_con_area(AREA_VENTAS)

    def test_proyecto_sin_asignados_no_aparece_en_ninguna_area(self, cliente) -> None:
        """EL CASO BORDE. No es un bug: no hay área que pueda reclamarlo. En producción
        hay exactamente uno así (1 de 6 proyectos)."""
        for area in (AREA_SISTEMAS, AREA_VENTAS):
            assert "P_HUERFANO" not in area_scope.proyecto_ids_con_area(area)

    def test_empleado_de_otra_empresa_igual_cuenta(self, cliente) -> None:
        """EL CASO QUE ROMPERÍA acotar por empresa. `de_b` es de la empresa B y está asignado
        a un proyecto: filtrar por su área tiene que encontrarlo."""
        assert "P_CROSS" in area_scope.proyecto_ids_con_area(AREA_SISTEMAS)

    def test_no_acota_la_busqueda_de_empleados_por_empresa(self, cliente) -> None:
        """Guarda contra la 'corrección por consistencia': si alguien agregara el `.eq` de
        empresa, este test cae y el de arriba también."""
        area_scope.proyecto_ids_con_area(AREA_SISTEMAS)
        assert cliente == {"empleados": 1, "proyecto_asignaciones": 1}

    def test_area_sin_empleados_no_consulta_asignaciones(self, cliente) -> None:
        assert area_scope.proyecto_ids_con_area(uuid4()) == []
        assert "proyecto_asignaciones" not in cliente

    def test_asignacion_inactiva_igual_cuenta(self, cliente) -> None:
        """LA DECISIÓN DE PRODUCTO: contamos asignaciones activas E INACTIVAS. Que un proyecto
        haya involucrado a alguien de Sistemas es un hecho histórico que conviene encontrar.
        Si alguien agrega un .eq("activo", True) "para mostrar solo lo vigente", cae acá."""
        assert "P_VIEJO" in area_scope.proyecto_ids_con_area(AREA_SISTEMAS)

    def test_no_repite_ids(self, cliente) -> None:
        ids = area_scope.proyecto_ids_con_area(AREA_SISTEMAS)
        assert len(ids) == len(set(ids))


class TestConteoDeQueries:
    """El filtro no puede escalar con la cantidad de proyectos."""

    def test_dos_queries_fijas(self, cliente) -> None:
        area_scope.proyecto_ids_con_area(AREA_SISTEMAS)
        assert sum(cliente.values()) == 2

    def test_sigue_siendo_dos_con_200_asignaciones(self, cliente, monkeypatch) -> None:
        """Es lo que separa un filtro batch de un N+1: el conteo no se mueve con el volumen."""
        import tests.test_filtro_area as mod
        monkeypatch.setattr(mod, "ASIGNACIONES", ASIGNACIONES + [(f"P{i}", "ana", True) for i in range(200)])
        assert len(area_scope.proyecto_ids_con_area(AREA_SISTEMAS)) > 200
        assert sum(cliente.values()) == 2


# ─── Inventario ───────────────────────────────────────────────────────────────


class TestEmpleadosDeArea:
    """El helper que consume inventario (y del que cuelga proyectos)."""

    def test_devuelve_los_del_area(self, cliente) -> None:
        assert sorted(area_scope.empleados_de_area(AREA_SISTEMAS)) == ["ana", "beto", "de_b"]

    def test_excluye_los_de_otra_area(self, cliente) -> None:
        assert "caro" not in area_scope.empleados_de_area(AREA_SISTEMAS)

    def test_area_vacia_da_lista_vacia(self, cliente) -> None:
        assert area_scope.empleados_de_area(uuid4()) == []

    def test_con_empresa_acota(self, cliente) -> None:
        """En inventario SÍ corresponde acotar: la asignación y el empleado son de la misma
        empresa, y el `.eq` extra es una barandilla barata."""
        assert sorted(area_scope.empleados_de_area(AREA_SISTEMAS, EMPRESA_A)) == ["ana", "beto"]

    def test_una_sola_query(self, cliente) -> None:
        area_scope.empleados_de_area(AREA_SISTEMAS)
        assert cliente == {"empleados": 1}


# ─── El cableado del área en el repo de inventario ────────────────────────────


class _QueryInv:
    """Doble mínimo para ver qué filtros arma inventario_asignaciones_repo.find_all."""

    def __init__(self, tabla, registro):
        self.tabla, self.registro = tabla, registro
        self.registro.setdefault(tabla, {"eq": {}, "in_": None, "is_": None})

    def select(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    # No-op encadenable: este doble audita QUÉ FILTROS arma la query, no cuántas filas devuelve.
    def range(self, *_a, **_k): return self

    def is_(self, col, val):
        self.registro[self.tabla]["is_"] = (col, val)
        return self

    def eq(self, col, val):
        self.registro[self.tabla]["eq"][col] = val
        return self

    def in_(self, col, ids):
        self.registro[self.tabla]["in_"] = (col, list(ids))
        return self

    def execute(self):
        if self.tabla == "empleados":
            return _Res([{"id": "ana"}, {"id": "beto"}])
        return _Res([])


class TestCableadoInventario:
    """`scope_filtros` puede estar perfecto y el repo no usarlo. Esto mira el otro extremo."""

    def _find_all(self, monkeypatch, **kw) -> dict:
        import repositories.inventario_asignaciones_repo as repo_mod
        registro: dict = {}
        monkeypatch.setattr(repo_mod, "supabase_admin",
                            type("C", (), {"table": staticmethod(lambda t: _QueryInv(t, registro))})())
        monkeypatch.setattr(repo_mod, "empleados_de_area", lambda a, e=None: ["ana", "beto"])
        repo_mod.InventarioAsignacionesRepo().find_all(**kw)
        return registro

    def test_con_area_acota_por_empleado(self, monkeypatch) -> None:
        reg = self._find_all(monkeypatch, area_id=AREA_SISTEMAS)
        assert reg["inventario_asignaciones"]["in_"] == ("empleado_id", ["ana", "beto"])

    def test_sin_area_no_acota(self, monkeypatch) -> None:
        reg = self._find_all(monkeypatch)
        assert reg["inventario_asignaciones"]["in_"] is None

    def test_area_sin_empleados_no_consulta_asignaciones(self, monkeypatch) -> None:
        import repositories.inventario_asignaciones_repo as repo_mod
        registro: dict = {}
        monkeypatch.setattr(repo_mod, "supabase_admin",
                            type("C", (), {"table": staticmethod(lambda t: _QueryInv(t, registro))})())
        monkeypatch.setattr(repo_mod, "empleados_de_area", lambda a, e=None: [])
        assert repo_mod.InventarioAsignacionesRepo().find_all(area_id=AREA_SISTEMAS) == ([], 0)
        assert "inventario_asignaciones" not in registro

    def test_conserva_la_vigencia(self, monkeypatch) -> None:
        """El área no puede pisar el filtro de fecha_devolucion IS NULL."""
        reg = self._find_all(monkeypatch, area_id=AREA_SISTEMAS)
        assert reg["inventario_asignaciones"]["is_"] == ("fecha_devolucion", "null")

    def test_se_compone_con_empleado_y_empresa(self, monkeypatch) -> None:
        reg = self._find_all(monkeypatch, empresa_id=EMPRESA_A, empleado_id="ana", area_id=AREA_SISTEMAS)
        eq = reg["inventario_asignaciones"]["eq"]
        assert eq["empleado_id"] == "ana" and eq["empresa_id"] == str(EMPRESA_A)
        assert reg["inventario_asignaciones"]["in_"] is not None
