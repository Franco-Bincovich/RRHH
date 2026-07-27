"""
Barrera de empresa en los 3 endpoints de áreas — fakes, sin red. Primer test del módulo.

Áreas quedó fuera de todas las tandas anteriores porque area_repo.find_by_id no aceptaba
empresa_id; sin ese parámetro tampoco se podía validar el area_id de empleados. Las áreas son
POR EMPRESA (dos empresas pueden tener un "Sistemas" distinto), así que leer/editar/borrar un
área por id crudo cruzaba la frontera.

Ownership NO se testea: Seccion.AREAS no está en MANDOS_MEDIOS_SECCIONES (utils/permisos.py:68),
así que solo llegan admin_rrhh y gerencia_lectura, sin restricción. Agregarlo sería código muerto.

⚠️ El fake HONRA empresa_id (y devuelve None cuando no coincide, como el _with_empresa real).
No calcar los fakes que la aceptan y la ignoran: darían verde sin validar nada.
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

from schemas.area import AreaResponse, AreaUpdate
from services.area_service import AreaService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIA = UUID("11111111-1111-1111-1111-111111111111")
AJENA = UUID("22222222-2222-2222-2222-222222222222")
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")

_EMPRESAS = {str(PROPIA): EMPRESA_A, str(AJENA): EMPRESA_B}


def _area(id_: UUID, empresa_id: UUID) -> AreaResponse:
    return AreaResponse(id=str(id_), empresa_id=str(empresa_id), nombre="Sistemas",
                        descripcion=None, responsable_id=None, responsable_nombre=None,
                        cantidad_empleados=0, created_at="2024-01-01T00:00:00Z")


class _AreaRepo:
    """HONRA empresa_id en find_by_id / update / delete (los tres filtran en el WHERE real)."""

    def __init__(self) -> None:
        self.actualizadas: list = []
        self.borradas: list = []

    def _match(self, id, empresa_id):
        emp = _EMPRESAS.get(str(id))
        return emp if emp and (not empresa_id or str(emp) == str(empresa_id)) else None

    def find_by_id(self, id, empresa_id=None):
        emp = self._match(id, empresa_id)
        return _area(UUID(str(id)), emp) if emp else None

    def update(self, id, data, empresa_id=None):
        emp = self._match(id, empresa_id)
        if not emp:
            return None
        self.actualizadas.append(str(id))
        return _area(UUID(str(id)), emp)

    def delete(self, id, empresa_id=None):
        emp = self._match(id, empresa_id)
        if not emp:
            return False
        self.borradas.append(str(id))
        return True


def _svc(repo=None):
    return AreaService(repo=repo or _AreaRepo())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def _get(svc, area_id, empresa=EMPRESA_A):
    return svc.get_area(area_id, str(empresa) if empresa else None)


def _upd(svc, area_id, empresa=EMPRESA_A):
    return svc.update_area(area_id, AreaUpdate(nombre="Nuevo"), str(empresa) if empresa else None)


def _del(svc, area_id, empresa=EMPRESA_A):
    return svc.delete_area(area_id, str(empresa) if empresa else None)


_OPS = [_get, _upd, _del]
_IDS = ["get_area", "update_area", "delete_area"]


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_area_de_otra_empresa_404(llamar):
    err = _error(lambda: llamar(_svc(), AJENA))
    assert err.code == "AREA_NOT_FOUND" and err.status_code == 404


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_area_ajena_indistinguible_de_inexistente(llamar):
    """No confirma la existencia de áreas de otra empresa: mismo code, mensaje y status."""
    ajena = _error(lambda: llamar(_svc(), AJENA))
    inexistente = _error(lambda: llamar(_svc(), INEXISTENTE))
    assert (ajena.code, ajena.message, ajena.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_area_propia_camino_feliz(llamar):
    assert llamar(_svc(), PROPIA) is not None


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
def test_consolidado_no_restringe(llamar):
    assert llamar(_svc(), AJENA, empresa=None) is not None


def test_ninguna_escritura_ocurre_con_area_ajena():
    """El filtro va en el WHERE del UPDATE: no afecta filas y el service lo traduce a 404."""
    repo = _AreaRepo()
    svc = _svc(repo)
    _error(lambda: _upd(svc, AJENA))
    _error(lambda: _del(svc, AJENA))
    assert repo.actualizadas == [] and repo.borradas == []
