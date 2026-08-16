"""
Barrera de empresa en tres endpoints sueltos — fakes, sin red. Un módulo por bloque:

  · horas       GET /proyectos/{proyecto_id}/horas — las horas se alcanzan por proyecto_id, así
                que el gate va sobre el PROYECTO (el mismo patrón que cargar/delete ya usaban en
                ese service; list_horas era el único de los tres sin él).
  · inventario  POST /inventario/asignaciones/{id}/devolver — la asignación lleva empresa_id
                propio; find_by_id pasó a aceptarlo.
  · offboarding PUT /offboarding/{instancia_id}/activos/{activo_id} — FALSO POSITIVO del barrido:
                empresa_id llegaba pero solo alimentaba el payload de auditoría; update_activo
                nunca filtró. Los activos no llevan empresa_id, se alcanzan por instancia_id, así
                que la barrera va sobre la INSTANCIA.

⚠️ Los fakes HONRAN empresa_id. No calcar los que la aceptan y la ignoran.
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

from schemas.inventario import AsignacionResponse, DevolucionRequest
from services.horas_service import HorasService
from services.inventario_asignaciones_service import InventarioAsignacionesService
from services.offboarding_service import OffboardingService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")
AJENO = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── horas ─────────────────────────────────────────────────────────────────────

class _ProyectosRepo:
    def find_by_id(self, id, empresa_id=None):
        emp = {str(PROPIO): EMPRESA_A, str(AJENO): EMPRESA_B}.get(str(id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(id), empresa_id=str(emp))


class _HorasRepo:
    def __init__(self) -> None:
        self.consultado: list = []

    def find_by_proyecto(self, proyecto_id, page, page_size):
        self.consultado.append(str(proyecto_id))
        return [], 0


def _horas_svc(horas_repo=None):
    # `totales` va stubbeado igual que los repos: es la agregación de horas/costo del proyecto,
    # que no es lo que este archivo audita (acá se prueba el SCOPE de empresa). Sin el stub la
    # dependencia real sale a la red y el test se cuelga en vez de fallar.
    return HorasService(repo=horas_repo or _HorasRepo(), proyectos_repo=_ProyectosRepo(),
                        totales=lambda _pid: (0.0, 0.0))


def test_horas_proyecto_ajeno_404_y_no_consulta():
    repo = _HorasRepo()
    err = _error(lambda: _horas_svc(repo).get_by_proyecto(AJENO, 1, 20, EMPRESA_A))
    assert err.code == "PROYECTO_NOT_FOUND" and err.status_code == 404
    assert repo.consultado == []  # cortó antes de leer horas ajenas


def test_horas_proyecto_ajeno_indistinguible_del_inexistente():
    ajeno = _error(lambda: _horas_svc().get_by_proyecto(AJENO, 1, 20, EMPRESA_A))
    inexistente = _error(lambda: _horas_svc().get_by_proyecto(INEXISTENTE, 1, 20, EMPRESA_A))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_horas_proyecto_propio_camino_feliz():
    assert _horas_svc().get_by_proyecto(PROPIO, 1, 20, EMPRESA_A).total == 0


def test_horas_consolidado_no_restringe():
    assert _horas_svc().get_by_proyecto(AJENO, 1, 20, None).total == 0


# ── inventario ────────────────────────────────────────────────────────────────

class _AsigRepo:
    def __init__(self) -> None:
        self.devueltas: list = []

    def find_by_id(self, id, empresa_id=None):
        emp = {str(PROPIO): EMPRESA_A, str(AJENO): EMPRESA_B}.get(str(id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return AsignacionResponse.model_validate({
            "id": str(id), "item_id": str(uuid4()), "empleado_id": str(uuid4()),
            "empresa_id": str(emp), "fecha_asignacion": "2024-01-01", "fecha_devolucion": None,
            "created_at": "2024-01-01T00:00:00Z",
        })

    def devolver(self, id, estado, notas):
        self.devueltas.append(str(id))
        return self.find_by_id(id)


class _ItemsRepo:
    def set_estado(self, item_id, estado):
        return True


def _inv_svc(repo=None):
    return InventarioAsignacionesService(repo=repo or _AsigRepo(), items_repo=_ItemsRepo())


def _devolver(svc, asig_id, empresa=EMPRESA_A):
    return svc.devolver(asig_id, DevolucionRequest(estado_devolucion="ok"), empresa)


def test_inventario_asignacion_ajena_404_y_no_devuelve():
    repo = _AsigRepo()
    err = _error(lambda: _devolver(_inv_svc(repo), AJENO))
    assert err.code == "ASIGNACION_NOT_FOUND" and err.status_code == 404
    assert repo.devueltas == []


def test_inventario_ajena_indistinguible_de_inexistente():
    ajeno = _error(lambda: _devolver(_inv_svc(), AJENO))
    inexistente = _error(lambda: _devolver(_inv_svc(), INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_inventario_asignacion_propia_camino_feliz():
    repo = _AsigRepo()
    _devolver(_inv_svc(repo), PROPIO)
    assert repo.devueltas == [str(PROPIO)]


def test_inventario_consolidado_no_restringe():
    repo = _AsigRepo()
    _devolver(_inv_svc(repo), AJENO, empresa=None)
    assert repo.devueltas == [str(AJENO)]


# ── offboarding activos ───────────────────────────────────────────────────────

class _OffRepo:
    def __init__(self) -> None:
        self.actualizados: list = []

    def find_instancia_min(self, instancia_id, empresa_id=None):
        emp = {str(PROPIO): EMPRESA_A, str(AJENO): EMPRESA_B}.get(str(instancia_id))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return {"id": str(instancia_id), "empresa_id": str(emp)}

    def update_activo(self, instancia_id, activo_id, devuelto):
        self.actualizados.append(str(instancia_id))
        return True


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


def _off_svc(repo=None):
    return OffboardingService(repo=repo or _OffRepo(), audit=_Audit())


def _marcar(svc, instancia_id, empresa=EMPRESA_A):
    return svc.marcar_activo_devuelto(instancia_id, uuid4(), True, "u1", empresa)


def test_offboarding_instancia_ajena_404_y_no_escribe():
    """El agujero real: empresa_id llegaba pero solo iba al payload de audit."""
    repo = _OffRepo()
    err = _error(lambda: _marcar(_off_svc(repo), AJENO))
    assert err.code == "ACTIVO_NOT_FOUND" and err.status_code == 404
    assert repo.actualizados == []


def test_offboarding_ajena_indistinguible_de_inexistente():
    ajeno = _error(lambda: _marcar(_off_svc(), AJENO))
    inexistente = _error(lambda: _marcar(_off_svc(), INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_offboarding_instancia_propia_camino_feliz():
    repo = _OffRepo()
    assert _marcar(_off_svc(repo), PROPIO) is True
    assert repo.actualizados == [str(PROPIO)]


def test_offboarding_consolidado_no_restringe():
    repo = _OffRepo()
    assert _marcar(_off_svc(repo), AJENO, empresa=None) is True
