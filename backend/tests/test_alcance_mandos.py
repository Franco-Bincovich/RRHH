"""
La excepción de `mandos_medios` a la barrera de empresa — fakes, sin red.
(Decisión de producto 2/8/2026: el manager_id REEMPLAZA al filtro de empresa. Ver
`services/_alcance_mandos.py`, que es donde vive el porqué.)

🔴 EL FAKE MODELA DOS EMPRESAS **Y UN MANAGER QUE LAS CRUZA**, y es lo único que hace que estos
tests puedan fallar. Ningún fake del repo lo hacía antes: los de ownership ponen al mando y a sus
subordinados en la misma empresa, y con ese reparto "solté la empresa" y "no la solté" dan el
MISMO resultado — el test pasaría con el cambio puesto o sacado. Acá el mando es de la empresa B
y tiene UN subordinado en A y otro en B; si el filtro de empresa volviera, el de A desaparecería.

⚠️ `ids_subordinados` del fake es CIEGO A LA EMPRESA, igual que el real
(`EmpleadoOwnershipRepo.ids_subordinados` es un `.eq("manager_id", …)` pelado). Si el fake
filtrara por empresa —que es lo "prolijo" y lo que un lector distraído escribiría— estaría
modelando un repo que no existe, y el test verificaría una implementación imaginaria.

Cuatro cosas se prueban acá, y son cuatro cosas distintas:
  1. `empresa_efectiva` — la decisión por rol, aislada.
  2. LA INVARIANTE — que para un mando el ownership nunca resuelve a "sin restricción". Es de la
     que depende que soltar la empresa no devuelva la tabla entera de todas las empresas.
  3. El guard fail-closed que la verifica en runtime, forzando el caso que hoy es imposible.
  4. 🔴 REPO-LEVEL: que el `.eq("empresa_id")` SALGA DE LA QUERY. Un fake de repo no puede ver
     esto —reemplaza al repo entero, así que su WHERE real nunca corre—, y "el filtro de empresa
     ya no viaja" es literalmente la afirmación de este commit. Molde:
     `test_offboarding_entrevista.py::TestElWhereDelRepoLlevaLaEmpresa`.
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

from services._alcance_mandos import ROL_MANDOS_MEDIOS, alcance_listado, empresa_efectiva

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
AREA = uuid4()

MANDO_UID = "user-mando"
MANDO_EMP = "11111111-1111-1111-1111-111111111111"   # el mando: empresa B
SUB_MISMA = "22222222-2222-2222-2222-222222222222"   # subordinado en la empresa B (la suya)
SUB_CRUZADO = "33333333-3333-3333-3333-333333333333"  # 🔴 subordinado en la empresa A (otra)

_TODOS = [MANDO_EMP, SUB_MISMA, SUB_CRUZADO]


class _Own:
    """Repo de ownership fake. `ids_subordinados` NO filtra por empresa — como el real."""

    def __init__(self, con_empleado: bool = True) -> None:
        self._con_empleado = con_empleado

    def find_by_user_id(self, user_id):
        return {"id": MANDO_EMP} if (self._con_empleado and user_id == MANDO_UID) else None

    def ids_subordinados(self, emp_id):
        return [SUB_MISMA, SUB_CRUZADO] if str(emp_id) == MANDO_EMP else []

    def ids_empleados_por_area(self, empresa_id, area_id):
        # El área devuelve gente de las DOS empresas: si `alcance_listado` acotara el área por
        # empresa para un mando, este conjunto se recortaría y la intersección perdería al cruzado.
        return [SUB_MISMA, SUB_CRUZADO]


# ── 1. empresa_efectiva: la decisión por rol, aislada ─────────────────────────

class TestEmpresaEfectiva:
    def test_mandos_medios_suelta_la_empresa(self) -> None:
        assert empresa_efectiva(EMPRESA_A, ROL_MANDOS_MEDIOS) is None

    @pytest.mark.parametrize("rol", ["admin_rrhh", "gerencia_lectura"])
    def test_los_otros_roles_la_conservan(self, rol: str) -> None:
        """La excepción es de UN rol. Si esto falla, se aflojó la barrera para todo el mundo."""
        assert empresa_efectiva(EMPRESA_A, rol) == EMPRESA_A

    @pytest.mark.parametrize("rol", ["rol_inventado", None, "", "MANDOS_MEDIOS"])
    def test_un_rol_que_no_es_exactamente_el_string_NO_entra_a_la_excepcion(self, rol) -> None:
        """Comparación literal, igual que `puede()` y `ownership`: cualquier otra cosa conserva
        la empresa. Un rol nuevo mal escrito no hereda la excepción por accidente."""
        assert empresa_efectiva(EMPRESA_A, rol) == EMPRESA_A

    def test_consolidado_sigue_siendo_consolidado(self) -> None:
        """None entra y None sale: la excepción no INVENTA una empresa donde no había."""
        assert empresa_efectiva(None, "admin_rrhh") is None


# ── 2. 🔴 LA INVARIANTE ───────────────────────────────────────────────────────

class TestLaInvariante:
    """Para `mandos_medios`, el alcance NUNCA puede ser (empleado_ids=None, vacio=False).

    Es LA aserción de la que depende la seguridad de todo este commit. Hasta el 2/8/2026 un fallo
    ahí quedaba CONTENIDO por el `.eq("empresa_id")` del repo: el mando veía de más, pero dentro de
    su empresa. Sin ese `.eq`, `(None, False)` significa "traé la tabla entera de TODAS las
    empresas". El caso no puede darse hoy (`ids_empleados_visibles` devuelve `None` solo en la rama
    de admin/gerencia), pero eso es una propiedad de otros dos archivos: acá se fija por contrato.
    """

    @pytest.mark.parametrize("area", [None, AREA])
    @pytest.mark.parametrize("empleado", [None, SUB_CRUZADO])
    @pytest.mark.parametrize("proyecto", [None, [SUB_MISMA, SUB_CRUZADO]])
    @pytest.mark.parametrize("empresa", [None, EMPRESA_A, EMPRESA_B])
    def test_nunca_sin_restriccion(self, area, empleado, proyecto, empresa) -> None:
        _, ids, vacio = alcance_listado(
            MANDO_UID, ROL_MANDOS_MEDIOS, empresa, area, empleado, _Own(), proyecto)
        assert not (ids is None and vacio is False), \
            "un mando resolvió a 'sin restricción' y la empresa ya no lo acota: leería TODO"

    def test_mando_sin_empleado_vinculado_es_vacio_no_sin_filtro(self) -> None:
        """El fail-closed del contrato: `[]` del base → `(None, True)`, nunca `(None, False)`."""
        _, ids, vacio = alcance_listado(
            MANDO_UID, ROL_MANDOS_MEDIOS, EMPRESA_A, None, None, _Own(con_empleado=False))
        assert (ids, vacio) == (None, True)

    def test_admin_SI_puede_no_tener_restriccion(self) -> None:
        """El contrapeso: `(None, False)` sigue siendo legítimo para admin —es como ve todo—, y
        para él la empresa del header SÍ sigue viajando. Sin este test, el guard podría estar
        rompiendo el caso normal y nadie se enteraría."""
        empresa, ids, vacio = alcance_listado(
            "u", "admin_rrhh", EMPRESA_A, None, None, _Own())
        assert (ids, vacio) == (None, False)
        assert empresa == EMPRESA_A


# ── 3. El guard fail-closed, forzando el caso imposible ───────────────────────

class TestElGuardFailClosed:
    """Fuerza `(None, False)` para un mando —hoy inalcanzable— y verifica que se corte vacío.

    Es la parte "imposible por construcción": si mañana alguien cambia `ids_empleados_visibles` o
    `_ownership_filter` y rompe la invariante, este guard convierte una FUGA en una pantalla vacía.
    Para que el test falle alcanza con borrar el `if` de `alcance_listado`.
    """

    @staticmethod
    def _forzar(monkeypatch, retorno) -> None:
        import services._alcance_mandos as mod
        monkeypatch.setattr(mod, "resolver_empleado_ids", lambda *a, **k: retorno)

    def test_mando_con_sin_restriccion_se_corta_vacio(self, monkeypatch) -> None:
        self._forzar(monkeypatch, (None, False))
        empresa, ids, vacio = alcance_listado(
            MANDO_UID, ROL_MANDOS_MEDIOS, EMPRESA_A, None, None, _Own())
        assert (ids, vacio) == (None, True), "la invariante se rompió y NO se cortó: fuga"
        assert empresa is None  # la empresa ya se soltó; por eso cortar es obligatorio

    def test_el_guard_no_toca_a_los_demas_roles(self, monkeypatch) -> None:
        """Mismo retorno forzado, rol admin: pasa tal cual. El guard mira el ROL, no el valor."""
        self._forzar(monkeypatch, (None, False))
        _, ids, vacio = alcance_listado("u", "admin_rrhh", EMPRESA_A, None, None, _Own())
        assert (ids, vacio) == (None, False)

    def test_el_guard_no_convierte_una_lista_en_vacio(self, monkeypatch) -> None:
        """Contrapeso: con ids concretos el guard no interviene (si no, el mando no vería nada)."""
        self._forzar(monkeypatch, ([SUB_CRUZADO], False))
        _, ids, vacio = alcance_listado(
            MANDO_UID, ROL_MANDOS_MEDIOS, EMPRESA_A, None, None, _Own())
        assert (ids, vacio) == ([SUB_CRUZADO], False)


# ── 4. 🔴 REPO-LEVEL: que el .eq("empresa_id") SALGA DE LA QUERY ──────────────

class _Query:
    """Espía del query builder: registra los predicados que se le aplican y devuelve 0 filas.

    Devolver `data=[]` es deliberado: `build_responses([])`/`_build([])` cortan antes de los
    lookups de enriquecido, así que el espía no necesita modelar empresas/empleados/áreas. Lo que
    se mide son los PREDICADOS, no las filas."""

    def __init__(self, aplicados: list) -> None:
        self._a = aplicados

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def eq(self, col, val):
        self._a.append((col, str(val)))
        return self

    def in_(self, col, vals):
        self._a.append((col, tuple(str(v) for v in vals)))
        return self

    def gt(self, *a):
        return self

    def gte(self, *a):
        return self

    def lte(self, *a):
        return self

    def range(self, *a):
        return self

    def execute(self):
        return SimpleNamespace(data=[], count=0)


class _Cliente:
    def __init__(self, aplicados: list) -> None:
        self._a = aplicados

    def table(self, _t):
        return _Query(self._a)


def _predicados_vacaciones(monkeypatch, rol: str, empresa) -> list:
    """Corre VacacionesService.get_all con el repo REAL y el cliente de Supabase falseado."""
    import repositories.vacaciones_repo as mod
    from services.vacaciones_service import VacacionesService

    aplicados: list = []
    monkeypatch.setattr(mod, "supabase_admin", _Cliente(aplicados))
    svc = VacacionesService(repo=mod.VacacionesRepo(), ownership_repo=_Own())
    svc.get_all(MANDO_UID if rol == ROL_MANDOS_MEDIOS else "u", rol, empresa)
    return aplicados


def _predicados_ausencias(monkeypatch, rol: str, empresa) -> list:
    import repositories.ausencias_repo as mod
    from services.ausencias_service import AusenciasService

    aplicados: list = []
    monkeypatch.setattr(mod, "supabase_admin", _Cliente(aplicados))
    svc = AusenciasService(repo=mod.AusenciasRepo(), ownership_repo=_Own())
    svc.get_all(MANDO_UID if rol == ROL_MANDOS_MEDIOS else "u", rol, empresa)
    return aplicados


_MODULOS = [_predicados_vacaciones, _predicados_ausencias]
_IDS = ["vacaciones", "ausencias"]


@pytest.mark.parametrize("predicados", _MODULOS, ids=_IDS)
class TestElFiltroDeEmpresaSaleDeLaQuery:
    def test_para_un_mando_no_hay_eq_de_empresa(self, monkeypatch, predicados) -> None:
        """🔴 LA AFIRMACIÓN CENTRAL DEL COMMIT, medida donde de verdad ocurre: el WHERE."""
        aplicados = predicados(monkeypatch, ROL_MANDOS_MEDIOS, EMPRESA_A)
        assert not [c for c, _ in aplicados if c == "empresa_id"], \
            "la query del mando todavía filtra por empresa: el subordinado cruzado no aparecería"

    def test_para_un_mando_el_in_de_empleados_SI_esta(self, monkeypatch, predicados) -> None:
        """Y con los tres ids, el cruzado incluido. Es lo que reemplaza al filtro de empresa:
        sin este `in_`, "sin filtro de empresa" sería "sin filtro"."""
        aplicados = predicados(monkeypatch, ROL_MANDOS_MEDIOS, EMPRESA_A)
        ins = [v for c, v in aplicados if c == "empleado_id"]
        assert len(ins) == 1 and set(ins[0]) == set(_TODOS)

    def test_para_un_admin_el_eq_de_empresa_SIGUE_estando(self, monkeypatch, predicados) -> None:
        """El control del control. Si esto también desapareciera, no habríamos hecho una
        excepción por rol: habríamos borrado la barrera de empresa para todos."""
        aplicados = predicados(monkeypatch, "admin_rrhh", EMPRESA_A)
        assert ("empresa_id", str(EMPRESA_A)) in aplicados

    def test_el_header_rancio_no_cambia_nada_para_un_mando(self, monkeypatch, predicados) -> None:
        """🔴 HEADER RANCIO. Un mando no ve el selector de empresa del sidebar (no tiene permiso
        sobre /empresas), pero `api.ts` sigue mandando el X-Empresa-Id que haya en localStorage.
        Con el filtro soltado, ese valor es inocuo: mande A, mande B o no mande nada, la query es
        la misma. Antes de este commit, un valor rancio le escondía parte de su propio equipo."""
        con_a = predicados(monkeypatch, ROL_MANDOS_MEDIOS, EMPRESA_A)
        con_b = predicados(monkeypatch, ROL_MANDOS_MEDIOS, EMPRESA_B)
        sin_nada = predicados(monkeypatch, ROL_MANDOS_MEDIOS, None)
        assert con_a == con_b == sin_nada
