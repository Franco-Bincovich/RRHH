"""
Barrera de empresa sobre COMPLETAR UNA TAREA de onboarding — fakes, sin red.

`PUT /api/onboarding/{instancia_id}/tareas/{tarea_id}/completar` era el único endpoint de
escritura del sistema cuyo router no recibía `Request` (barrido de routers, 23/8/2026): sin
`Request` no hay `empresa_id` que seguir, así que con el header de la empresa A y la instancia
de la B el endpoint devolvía 200 y COMPLETABA la tarea ajena. El molde estaba al lado, en
`iniciar_onboarding` del mismo router.

🔴 SE TESTEAN LAS DOS MITADES, y no es redundancia: un 404 que igual escribió es peor que no
tener barrera, porque la pantalla dice que no pasó nada y la fila quedó cambiada. Por eso cada
test de rechazo mira el status Y el estado de la fila.

El eje bajo prueba es la INSTANCIA, no el empleado (eso lo cubre test_onboarding_empresa_scope).
Por eso el fake de repo modela DOS empresas y devuelve 0 filas cuando no coinciden, que es lo
que hace el `.eq("empresa_id")` real; un fake que aceptara `empresa_id` y lo ignorara daría
verde sin validar nada — es el caso #1 de "un test solo prueba lo que el fake puede desmentir".

⚠️ Y como la barrera vive EN LA QUERY (Forma A), el fake de repo NO PUEDE VERLA: reemplaza al
repo entero, así que borrar el `with_empresa` del UPDATE dejaría estos tests en verde. Por eso
`TestElWhereDelRepoLlevaLaEmpresa` faltea un escalón más abajo —el cliente de Supabase— y
captura los `.eq()`. Molde: tests/test_offboarding_entrevista.py.
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

import inspect
from uuid import UUID, uuid4

import pytest

from services.onboarding_service import OnboardingService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
INST_A = UUID("11111111-1111-1111-1111-111111111111")     # empresa A
INST_B = UUID("22222222-2222-2222-2222-222222222222")     # empresa B
INST_INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
TAREA = UUID("44444444-4444-4444-4444-444444444444")
TAREA_DE_OTRA_INSTANCIA = UUID("55555555-5555-5555-5555-555555555555")


class _OnbRepo:
    """HONRA empresa_id: 0 filas si la instancia es de otra empresa, como el `.eq()` real.

    Guarda el estado de cada tarea para que el test pueda afirmar que un rechazo NO escribió.
    """

    def __init__(self) -> None:
        self.empresa_de = {INST_A: EMPRESA_A, INST_B: EMPRESA_B}
        self.completadas: set = set()

    def completar_tarea(self, instancia_id, tarea_id, empresa_id=None) -> bool:
        inst = UUID(str(instancia_id))
        tarea = UUID(str(tarea_id))
        empresa = self.empresa_de.get(inst)
        if empresa is None:                                   # instancia inexistente
            return False
        if empresa_id and str(empresa) != str(empresa_id):    # instancia de otra empresa
            return False
        if tarea != TAREA:                                    # la tarea no es de esa instancia
            return False
        self.completadas.add((inst, tarea))
        return True


def _svc(repo=None):
    r = repo or _OnbRepo()
    return OnboardingService(repo=r), r


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


class TestLaBarreraDeEmpresa:
    def test_instancia_de_otra_empresa_404_y_la_tarea_no_se_completo(self) -> None:
        """Las dos mitades: el status Y la fila. Un 404 que igual escribió es peor que nada."""
        svc, repo = _svc()
        err = _error(lambda: svc.completar_tarea(INST_B, TAREA, EMPRESA_A))
        assert (err.code, err.status_code) == ("TAREA_NOT_FOUND", 404)
        assert repo.completadas == set()

    def test_la_instancia_ajena_es_indistinguible_de_la_inexistente(self) -> None:
        """Mismo code, mismo mensaje y mismo status: nunca un 403 ni un mensaje propio, que
        confirmarían que la instancia existe y es de otra empresa."""
        svc, _ = _svc()
        ajena = _error(lambda: svc.completar_tarea(INST_B, TAREA, EMPRESA_A))
        inexistente = _error(lambda: svc.completar_tarea(INST_INEXISTENTE, TAREA, EMPRESA_A))
        assert (ajena.code, ajena.message, ajena.status_code) == \
               (inexistente.code, inexistente.message, inexistente.status_code)

    def test_instancia_propia_camino_feliz(self) -> None:
        svc, repo = _svc()
        assert svc.completar_tarea(INST_A, TAREA, EMPRESA_A) is True
        assert repo.completadas == {(INST_A, TAREA)}

    def test_empresa_none_es_consolidado_y_no_restringe(self) -> None:
        """None = 'Todas las empresas': no es un fallo de validación, cualquier instancia pasa."""
        svc, repo = _svc()
        assert svc.completar_tarea(INST_B, TAREA, None) is True
        assert repo.completadas == {(INST_B, TAREA)}

    def test_tarea_ajena_a_la_instancia_propia_sigue_dando_404(self) -> None:
        """El 404 que ya existía no se pierde al agregar la barrera."""
        svc, repo = _svc()
        err = _error(lambda: svc.completar_tarea(INST_A, TAREA_DE_OTRA_INSTANCIA, EMPRESA_A))
        assert (err.code, err.status_code) == ("TAREA_NOT_FOUND", 404)
        assert repo.completadas == set()


class TestElWhereDelRepoLlevaLaEmpresa:
    """El fake de repo de arriba no puede ver esto: reemplaza al repo entero, así que sacarle el
    `with_empresa` al UPDATE lo deja todo en verde. Acá se faltea el cliente de Supabase y se
    verifica que el filtro viaje EN LA QUERY (Forma A), no en una comparación posterior."""

    def _repo_con_espia(self, monkeypatch):
        import repositories.onboarding_repo as mod

        aplicados: list = []

        class _Q:
            def update(self, *a, **k):
                return self

            def eq(self, col, val):
                aplicados.append((col, val))
                return self

            def execute(self):
                return type("R", (), {"data": [{"id": str(INST_A)}]})()

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.OnboardingRepo(), aplicados

    def test_el_update_filtra_por_empresa(self, monkeypatch) -> None:
        repo, aplicados = self._repo_con_espia(monkeypatch)
        repo.completar_tarea(str(INST_A), str(TAREA), EMPRESA_A)
        assert ("empresa_id", str(EMPRESA_A)) in aplicados

    def test_el_update_siempre_filtra_por_instancia_y_tarea(self, monkeypatch) -> None:
        repo, aplicados = self._repo_con_espia(monkeypatch)
        repo.completar_tarea(str(INST_A), str(TAREA), EMPRESA_A)
        assert ("instancia_id", str(INST_A)) in aplicados
        assert ("tarea_id", str(TAREA)) in aplicados

    def test_consolidado_no_agrega_filtro_de_empresa(self, monkeypatch) -> None:
        """None es vista consolidada: no restringe, y tampoco debe filtrar por None."""
        repo, aplicados = self._repo_con_espia(monkeypatch)
        repo.completar_tarea(str(INST_A), str(TAREA), None)
        assert not [c for c, _ in aplicados if c == "empresa_id"]


class TestElRouterPasaLaEmpresa:
    """🔴 El router pasando `empresa_id` NO prueba nada por sí solo (CLAUDE.md), pero su AUSENCIA
    sí prueba el bug: éste era el endpoint donde el parámetro no llegaba ni al handler. Se
    verifica por firma, que es donde estaba el agujero."""

    def test_el_handler_recibe_request(self) -> None:
        from routers.onboarding import completar_tarea

        assert "request" in inspect.signature(completar_tarea).parameters

    def test_el_handler_lee_la_empresa_del_request(self) -> None:
        from routers.onboarding import completar_tarea

        assert "get_empresa_id(request)" in inspect.getsource(completar_tarea)
