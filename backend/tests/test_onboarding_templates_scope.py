"""
Barrera de empresa en los 5 endpoints de escritura de templates de onboarding — fakes, sin red.

Dos de los primeros cuatro eran FALSOS POSITIVOS del barrido de la Fase 2: update_template y
update_tarea recibían empresa_id del router y no lo usaban (update_template solo lo miraba en
el early-return de payload vacío; update_tarea nunca). delete_template y delete_tarea
directamente no lo recibían.

El QUINTO —add_tarea— apareció después, al cablear la visibilidad pública/privada: era el
único que llamaba a `self._repo.get_template` en vez de al gate del service, así que se leía
como cubierto y no lo estaba. Ahora los cinco pasan por `ensure_template_accesible`.

Las tareas se alcanzan por su template: gatear el template cubre la cadena tarea → template →
empresa.

⚠️ El fake HONRA empresa_id. No calcar los que la aceptan y la ignoran.
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

from uuid import UUID, uuid4

import pytest

from schemas.onboarding import TareaCreate, TareaResponse, TareaUpdate, TemplateResponse, TemplateUpdate
from services.onboarding_templates_service import OnboardingTemplatesService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")
AJENO = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
TAREA = UUID("44444444-4444-4444-4444-444444444444")


def _tmpl(id_: UUID, empresa_id: UUID) -> TemplateResponse:
    return TemplateResponse.model_validate({
        "id": str(id_), "nombre": "T", "empresa_id": str(empresa_id),
    })


class _Repo:
    """HONRA empresa_id en get_template.

    ⚠️ PERMISIVO EN VISIBILIDAD A PROPÓSITO: acepta `user_id`/`rol` y no los usa. Este archivo cubre
    UN eje —la empresa— y mezclar el otro haría que un fallo de empresa se pudiera confundir
    con uno de visibilidad. El eje de visibilidad lo cubre
    tests/test_onboarding_template_visibilidad.py, con un fake que sí lo honra. La regla del
    repo pide declarar los fakes permisivos: esto es la declaración.
    """

    def __init__(self) -> None:
        self._t = {str(PROPIO): _tmpl(PROPIO, EMPRESA_A), str(AJENO): _tmpl(AJENO, EMPRESA_B)}
        self.updates: list = []
        self.borrados: list = []
        self.tareas_creadas: list = []
        self.tareas_updated: list = []
        self.tareas_borradas: list = []

    def get_template(self, template_id, empresa_id=None, user_id=None, rol=None):
        t = self._t.get(str(template_id))
        if not t or (empresa_id and str(t.empresa_id) != str(empresa_id)):
            return None
        return t

    def update_template(self, template_id, data, user_id=None, rol=None):
        self.updates.append(str(template_id))
        return self._t[str(template_id)]

    def delete_template(self, template_id):
        self.borrados.append(str(template_id))
        return True

    def add_tarea(self, template_id, data, empresa_id) -> TareaResponse:
        self.tareas_creadas.append(str(template_id))
        return TareaResponse.model_validate({
            "id": str(TAREA), "template_id": str(template_id), "titulo": "X",
            "semana": 1, "orden": 1,
        })

    def update_tarea(self, tarea_id, data) -> TareaResponse:
        self.tareas_updated.append(str(tarea_id))
        return TareaResponse.model_validate({
            "id": str(tarea_id), "template_id": str(PROPIO), "titulo": "X",
            "semana": 1, "orden": 1,
        })

    def delete_tarea(self, tarea_id):
        """Devuelve LA FILA BORRADA, como el repo real (PostgREST la retorna en `.data`).

        🔴 No devuelve `True`: el service audita la baja con esta fila, y un fake que devolviera
        un booleano dejaría el evento sin nada que fotografiar — el título y la descripción que
        alguien escribió a mano son justo lo que desaparece."""
        self.tareas_borradas.append(str(tarea_id))
        return {"id": str(tarea_id), "template_id": str(PROPIO), "titulo": "X",
                "semana": 1, "orden": 1}


def _svc(repo=None):
    return OnboardingTemplatesService(repo=repo or _Repo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def _upd_tmpl(svc, tid, empresa=EMPRESA_A):
    return svc.update_template(tid, TemplateUpdate(nombre="Nuevo"), empresa)


def _del_tmpl(svc, tid, empresa=EMPRESA_A):
    return svc.delete_template(tid, empresa)


def _upd_tarea(svc, tid, empresa=EMPRESA_A):
    return svc.update_tarea(tid, TAREA, TareaUpdate(titulo="Y"), empresa)


def _del_tarea(svc, tid, empresa=EMPRESA_A):
    return svc.delete_tarea(tid, TAREA, empresa)


def _add_tarea(svc, tid, empresa=EMPRESA_A):
    return svc.add_tarea(tid, TareaCreate(titulo="Z", semana=1, orden=1), empresa)


# add_tarea se sumó al barrido cuando dejó de llamar al repo directo y pasó por el mismo gate
# que sus hermanos: los CINCO endpoints de escritura del módulo validan empresa.
_OPS = [_upd_tmpl, _del_tmpl, _upd_tarea, _del_tarea, _add_tarea]
_IDS = ["update_template", "delete_template", "update_tarea", "delete_tarea", "add_tarea"]


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_template_de_otra_empresa_404(llamar):
    err = _error(lambda: llamar(_svc(), AJENO))
    assert err.code == "TEMPLATE_NOT_FOUND" and err.status_code == 404


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_template_ajeno_indistinguible_del_inexistente(llamar):
    ajeno = _error(lambda: llamar(_svc(), AJENO))
    inexistente = _error(lambda: llamar(_svc(), INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_template_propio_camino_feliz(llamar):
    assert llamar(_svc(), PROPIO) is not None


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_consolidado_no_restringe(llamar):
    assert llamar(_svc(), AJENO, empresa=None) is not None


def test_ninguna_escritura_ocurre_con_template_ajeno():
    """El gate corta ANTES de tocar el repo, en las cinco operaciones."""
    repo = _Repo()
    svc = _svc(repo)
    for llamar in _OPS:
        _error(lambda f=llamar: f(svc, AJENO))
    assert repo.updates == [] and repo.borrados == []
    assert repo.tareas_updated == [] and repo.tareas_borradas == []
    assert repo.tareas_creadas == []
