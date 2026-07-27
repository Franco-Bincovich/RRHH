"""
Tests del gate empresa ∩ ownership en las dos lecturas por empleado de vacaciones — sin red.
Cubre GET /vacaciones/saldo/{empleado_id} (get_saldo) y GET /vacaciones/empleado/{empleado_id}
(get_by_empleado), los dos únicos endpoints del módulo que resolvían por empleado_id crudo.

Son DOS agujeros superpuestos y se prueban por separado, porque se componen y no se sustituyen:
  - empresa   → find_dias_asignados pegaba a `empleados` por id sin filtro, y es la que decide
                el 404: confirmaba existencia cross-empresa y devolvía dias_vacaciones_asignados.
  - ownership → Seccion.VACACIONES es una de las dos donde mandos_medios entra, y ninguno de los
                dos handlers recibía user_id ni rol: un mando leía saldo e historial de cualquier
                empleado de su propia empresa.

⚠️ Los fakes de acá HONRAN los dos filtros. Los preexistentes del módulo NO: el `find_by_id` de
test_escrituras_ownership.py:98 y el de test_audit_instrumentacion.py:71 aceptan empresa_id y
devuelven la fila igual. No los calques — darían verde sin validar nada.
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

from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest

from schemas.empleado import EmpleadoResponse
from schemas.vacaciones import SolicitudVacacionesResponse
from services.vacaciones_service import VacacionesService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")       # empresa A
AJENO = UUID("22222222-2222-2222-2222-222222222222")        # empresa B
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
SUBORDINADO = UUID("44444444-4444-4444-4444-444444444444")  # empresa A, a cargo del mando
MANDO_UID = "user-mando"


def _empleado(id_: UUID, empresa_id: UUID) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": "n@k.com",
        "empresa_id": str(empresa_id), "area_id": "55555555-5555-5555-5555-555555555555",
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


def _solicitud(empleado_id: UUID) -> SolicitudVacacionesResponse:
    ayer = date.today() - timedelta(days=10)
    return SolicitudVacacionesResponse.model_validate({
        "id": str(uuid4()), "empleado_id": str(empleado_id), "empresa_id": str(EMPRESA_A),
        "fecha_desde": str(ayer), "fecha_hasta": str(ayer + timedelta(days=4)), "dias": 5,
        "tipo": "vacaciones", "cancelada": False, "created_at": "2024-01-01T00:00:00Z",
        "estado": "tomada",  # lo recalcula derive_estado; el schema lo exige presente
    })


class _EmpleadoRepo:
    """HONRA empresa_id: None si el empleado es de otra empresa (como _with_empresa)."""

    def __init__(self) -> None:
        self._emp = {
            str(PROPIO): _empleado(PROPIO, EMPRESA_A),
            str(SUBORDINADO): _empleado(SUBORDINADO, EMPRESA_A),
            str(AJENO): _empleado(AJENO, EMPRESA_B),
        }

    def find_by_id(self, id, empresa_id=None):
        emp = self._emp.get(str(id))
        if not emp or (empresa_id and str(emp.empresa_id) != str(empresa_id)):
            return None
        return emp


class _VacRepo:
    """HONRA empresa_id en las dos consultas del saldo/historial."""

    def __init__(self) -> None:
        self.empresas_recibidas: list = []

    def find_dias_asignados(self, empleado_id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        if empresa_id and str(empresa_id) != str(EMPRESA_A):
            return None          # el empleado no es de esa empresa
        return 14

    def find_vacaciones_empleado(self, empleado_id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        if empresa_id and str(empresa_id) != str(EMPRESA_A):
            return []
        return [_solicitud(UUID(str(empleado_id)))]


class _Ownership:
    """EmpleadoOwnershipRepo fake. El mando MANDO_UID es PROPIO y tiene a SUBORDINADO a cargo."""

    def find_by_user_id(self, user_id):
        return {"id": str(PROPIO)} if user_id == MANDO_UID else None

    def ids_subordinados(self, emp_id):
        return [str(SUBORDINADO)] if str(emp_id) == str(PROPIO) else []


def _svc(vac_repo=None, emp_repo=None):
    return VacacionesService(repo=vac_repo or _VacRepo(), empleado_repo=emp_repo or _EmpleadoRepo(),
                             ownership_repo=_Ownership())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


def _saldo(svc, empleado_id, empresa_id=EMPRESA_A, uid="admin", rol="admin_rrhh"):
    return svc.get_saldo(empleado_id, uid, rol, empresa_id)


def _historial(svc, empleado_id, empresa_id=EMPRESA_A, uid="admin", rol="admin_rrhh"):
    return svc.get_by_empleado(empleado_id, uid, rol, empresa_id)


# ── Eje EMPRESA ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_empleado_de_otra_empresa_404(llamar):
    err = _error(lambda: llamar(_svc(), AJENO))
    assert err.code == "EMPLEADO_NOT_FOUND" and err.status_code == 404


@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_empleado_ajeno_indistinguible_del_inexistente(llamar):
    """El 404 del ajeno no puede confirmar que existe en otra empresa."""
    ajeno = _error(lambda: llamar(_svc(), AJENO))
    inexistente = _error(lambda: llamar(_svc(), INEXISTENTE))
    assert (ajeno.code, ajeno.message, ajeno.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


def test_saldo_empleado_propio_camino_feliz():
    out = _saldo(_svc(), PROPIO)
    assert out.asignados == 14 and out.gozados == 5 and out.disponibles == 9


def test_historial_empleado_propio_camino_feliz():
    out = _historial(_svc(), PROPIO)
    assert out.total == 1 and out.items[0].empleado_id == str(PROPIO)


@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_consolidado_no_restringe(llamar):
    """empresa_id None = 'Todas las empresas': el empleado de la otra empresa se lee."""
    assert llamar(_svc(), AJENO, empresa_id=None) is not None


@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_empresa_se_propaga_a_las_consultas(llamar):
    """El filtro no vive solo en el gate: las consultas de datos también lo reciben."""
    vac = _VacRepo()
    llamar(_svc(vac_repo=vac), PROPIO)
    assert vac.empresas_recibidas and all(e == EMPRESA_A for e in vac.empresas_recibidas)


# ── Eje OWNERSHIP ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_mando_no_alcanza_empleado_fuera_de_sus_subordinados(llamar):
    """Mismo empresa, pero fuera del alcance del mando → 404 idéntico al de inexistente."""
    otro = UUID("66666666-6666-6666-6666-666666666666")
    emp_repo = _EmpleadoRepo()
    emp_repo._emp[str(otro)] = _empleado(otro, EMPRESA_A)  # existe y es de SU empresa
    fuera = _error(lambda: llamar(_svc(emp_repo=emp_repo), otro, uid=MANDO_UID, rol="mandos_medios"))
    inexistente = _error(lambda: llamar(_svc(), INEXISTENTE, uid=MANDO_UID, rol="mandos_medios"))
    assert fuera.code == "EMPLEADO_NOT_FOUND" and fuera.status_code == 404
    assert (fuera.code, fuera.message) == (inexistente.code, inexistente.message)


@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_mando_alcanza_a_su_subordinado(llamar):
    assert llamar(_svc(), SUBORDINADO, uid=MANDO_UID, rol="mandos_medios") is not None


@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_mando_alcanza_su_propio_registro(llamar):
    """ids_empleados_visibles incluye el registro del propio mando, no solo subordinados."""
    assert llamar(_svc(), PROPIO, uid=MANDO_UID, rol="mandos_medios") is not None


@pytest.mark.parametrize("rol", ["admin_rrhh", "gerencia_lectura"])
def test_admin_y_gerencia_sin_restriccion_de_ownership(rol):
    """Para estos roles ids_empleados_visibles devuelve None = sin restringir."""
    assert _saldo(_svc(), SUBORDINADO, uid="u", rol=rol) is not None
    assert _historial(_svc(), SUBORDINADO, uid="u", rol=rol) is not None


@pytest.mark.parametrize("llamar", [_saldo, _historial], ids=["saldo", "historial"])
def test_rol_desconocido_fail_closed(llamar):
    """Rol fuera de ROLES_VALIDOS → ids_empleados_visibles devuelve [] → no ve nada."""
    err = _error(lambda: llamar(_svc(), PROPIO, uid="u", rol="rol_inventado"))
    assert err.code == "EMPLEADO_NOT_FOUND" and err.status_code == 404
