"""
Barrera de empresa sobre la entidad PADRE de un adjunto — fakes, sin red.

Dos problemas distintos, ambos cerrados acá:
  (a) POST /api/adjuntos no verificaba que el padre existiera ni fuera de tu empresa: se podía
      colgar un archivo del legajo de un empleado ajeno, y encima quedaba etiquetado con TU
      empresa (así que su dueño real ni lo veía). Ahora hay un despachador por entidad.
  (b) empresa_id NULL: la empresa del adjunto ahora sale del PADRE, no del header, así que deja
      de generarse. Las filas legacy con NULL se bloquean SIEMPRE (antes eran visibles en modo
      consolidado, porque el `empresa_id and ...` short-circuiteaba).

"evaluacion" está mapeado a una Sección pero NO tiene resolver (no hay repo que diga a qué
apunta, y cero callers en repo y front): queda fail-closed con ENTIDAD_INVALIDA. Hay test.

⚠️ Los resolvers de acá HONRAN empresa_id. El _PADRES_OK de test_adjuntos.py es permisivo a
propósito (aquel archivo prueba gating/upload) — no lo calques para probar este eje.
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

from services._adjunto_padres import RESOLVERS, ensure_padre_de_empresa
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PADRE_PROPIO = UUID("11111111-1111-1111-1111-111111111111")
PADRE_AJENO = UUID("22222222-2222-2222-2222-222222222222")
PADRE_INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")

_ENTIDADES = ["empleado", "vacacion", "ausencia", "vacante", "offboarding"]


def _resolver_honesto(entidad: str):
    """Doble del find_by_id real: None si el padre no existe o es de otra empresa.
    offboarding devuelve dict (find_instancia_min); el resto, objeto con .empresa_id."""
    def _r(entidad_id, empresa_id=None):
        emp = {str(PADRE_PROPIO): EMPRESA_A, str(PADRE_AJENO): EMPRESA_B}.get(str(entidad_id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        if entidad == "offboarding":
            return {"id": str(entidad_id), "empresa_id": str(emp)}
        return SimpleNamespace(id=str(entidad_id), empresa_id=str(emp))
    return _r


_RESOLVERS_TEST = {e: _resolver_honesto(e) for e in _ENTIDADES}


def _validar(entidad, padre_id, empresa=EMPRESA_A):
    return ensure_padre_de_empresa(entidad, padre_id, empresa, _RESOLVERS_TEST)


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── (a) barrera sobre el padre, por cada entidad soportada ───────────────────

@pytest.mark.parametrize("entidad", _ENTIDADES)
def test_padre_de_otra_empresa_404(entidad):
    err = _error(lambda: _validar(entidad, PADRE_AJENO))
    assert err.code == "PADRE_NOT_FOUND" and err.status_code == 404


@pytest.mark.parametrize("entidad", _ENTIDADES)
def test_padre_ajeno_indistinguible_del_inexistente(entidad):
    """No confirma la existencia de recursos de otra empresa."""
    ajeno = _error(lambda: _validar(entidad, PADRE_AJENO))
    inexistente = _error(lambda: _validar(entidad, PADRE_INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("entidad", _ENTIDADES)
def test_padre_propio_devuelve_su_empresa(entidad):
    """Devuelve la empresa DEL PADRE — es con la que se etiqueta el adjunto."""
    assert _validar(entidad, PADRE_PROPIO) == str(EMPRESA_A)


@pytest.mark.parametrize("entidad", _ENTIDADES)
def test_consolidado_no_restringe_pero_igual_hereda_del_padre(entidad):
    """En consolidado se puede elegir cualquier padre, pero la empresa sigue saliendo de él:
    por eso el adjunto ya no queda en NULL."""
    assert ensure_padre_de_empresa(entidad, PADRE_AJENO, None, _RESOLVERS_TEST) == str(EMPRESA_B)


def test_evaluacion_no_tiene_resolver_y_queda_fail_closed():
    """Mapeada a Sección pero sin repo que la resuelva y sin callers: no se puede adjuntar."""
    err = _error(lambda: ensure_padre_de_empresa("evaluacion", PADRE_PROPIO, EMPRESA_A))
    assert err.code == "ENTIDAD_INVALIDA" and err.status_code == 400
    assert "evaluacion" not in RESOLVERS


def test_entidad_desconocida_tambien_falla():
    err = _error(lambda: _validar("inventada", PADRE_PROPIO))
    assert err.code == "ENTIDAD_INVALIDA" and err.status_code == 400


def test_los_cinco_resolvers_reales_estan_registrados():
    """Guarda contra sumar una entidad al mapa de secciones y olvidar su resolver."""
    assert sorted(RESOLVERS) == sorted(_ENTIDADES)


# ── (b) empresa_id NULL en el adjunto ────────────────────────────────────────

def _svc_con(adj):
    from services.adjunto_service import AdjuntoService

    class _Repo:
        def find_by_id(self, id):
            return adj

    return AdjuntoService(repo=_Repo(), audit=SimpleNamespace(registrar=lambda **k: None))


def _adjunto(empresa_id):
    return SimpleNamespace(id="a1", entidad="empleado", entidad_id="e1", empresa_id=empresa_id,
                           bucket="documentos", storage_path="p")


@pytest.mark.parametrize("empresa", [EMPRESA_A, None], ids=["modo_empresa", "consolidado"])
def test_adjunto_con_empresa_null_se_bloquea_en_todos_los_modos(empresa):
    """Legacy sin empresa: antes era invisible en modo empresa pero VISIBLE en consolidado."""
    err = _error(lambda: _svc_con(_adjunto(None)).url_descarga("a1", empresa, "admin_rrhh"))
    assert err.code == "ADJUNTO_NOT_FOUND" and err.status_code == 404


def test_adjunto_con_empresa_propia_sigue_accesible():
    assert _svc_con(_adjunto(str(EMPRESA_A))).url_descarga is not None
