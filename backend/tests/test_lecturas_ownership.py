"""
Eje de ownership en las lecturas por id de vacaciones y ausencias — fakes, sin red.

GET /vacaciones/{id} y GET /ausencias/{id} validaban empresa pero NO ownership, mientras
cancel/actualizar/eliminar de esos mismos módulos sí: un mandos_medios leía el detalle de una
solicitud de alguien que no gestiona. VACACIONES y AUSENCIAS son las dos únicas secciones donde
mandos_medios entra (MANDOS_MEDIOS_SECCIONES), así que acá el eje NO es código muerto — a
diferencia del resto de los módulos de la Fase 2.

Los dos ejes se prueban por separado:
  - empresa   → en el WHERE del repo (find_by_id(id, empresa_id)), se aplica primero.
  - ownership → puede_gestionar_empleado sobre el empleado_id de la fila ya cargada.

🔴 DESDE EL 2/8/2026 LOS DOS EJES YA NO SE COMPONEN PARA `mandos_medios`: el manager_id REEMPLAZA
al filtro de empresa, así que un mando lee la solicitud de su subordinado aunque sea de otra
empresa del grupo (decisión de producto; el porqué en `services/_alcance_mandos.py`). El eje de
empresa sigue intacto para admin_rrhh y gerencia_lectura, y los tests de abajo lo verifican con
esos roles. Para el mando, el ownership pasa a ser la ÚNICA barrera — por eso se agregó
SOL_AJENA_NO_GESTIONADA: sin ese caso, "soltamos la empresa" y "soltamos todo" se verían igual.
Se reusa el MISMO mecanismo de las escrituras (services/ownership.py), no uno nuevo: en 1b.2 ya
se verificó que delega en ids_empleados_visibles, el conjunto que gobierna también las lecturas.

⚠️ Los fakes de acá HONRAN empresa_id y ownership. Los de test_escrituras_ownership.py:98 y
test_audit_instrumentacion.py:71 aceptan empresa_id y lo ignoran (siguen cubriendo el write
path, que esta sesión no toca) — no los calques.
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

from schemas.ausencias import AusenciaResponse
from schemas.vacaciones import SolicitudVacacionesResponse
from services.ausencias_service import AusenciasService
from services.vacaciones_service import VacacionesService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
MANDO_UID = "user-mando"
MANDO_EMP = UUID("11111111-1111-1111-1111-111111111111")     # el empleado del mando
SUBORDINADO = UUID("22222222-2222-2222-2222-222222222222")   # a cargo del mando
NO_GESTIONADO = UUID("33333333-3333-3333-3333-333333333333")  # misma empresa, fuera de su alcance

SOL_SUBORDINADO = UUID("44444444-4444-4444-4444-444444444444")
SOL_NO_GESTIONADO = UUID("55555555-5555-5555-5555-555555555555")
SOL_AJENA = UUID("66666666-6666-6666-6666-666666666666")      # empresa B, de SU subordinado
SOL_INEXISTENTE = UUID("77777777-7777-7777-7777-777777777777")
# Empresa B Y de alguien que el mando NO gestiona: el control del control. Sin este caso, un
# "soltamos la empresa" y un "soltamos todo" darían exactamente el mismo verde.
SOL_AJENA_NO_GESTIONADA = UUID("99999999-9999-9999-9999-999999999999")

# solicitud_id → (empleado_id, empresa_id)
_SOLICITUDES = {
    str(SOL_SUBORDINADO): (SUBORDINADO, EMPRESA_A),
    str(SOL_NO_GESTIONADO): (NO_GESTIONADO, EMPRESA_A),
    str(SOL_AJENA): (SUBORDINADO, EMPRESA_B),
    str(SOL_AJENA_NO_GESTIONADA): (NO_GESTIONADO, EMPRESA_B),
}


def _vac(id_: UUID, empleado_id: UUID, empresa_id: UUID) -> SolicitudVacacionesResponse:
    ayer = date.today() - timedelta(days=10)
    return SolicitudVacacionesResponse.model_validate({
        "id": str(id_), "empleado_id": str(empleado_id), "empresa_id": str(empresa_id),
        "fecha_desde": str(ayer), "fecha_hasta": str(ayer + timedelta(days=2)), "dias": 3,
        "tipo": "vacaciones", "cancelada": False, "estado": "tomada",
        "created_at": "2024-01-01T00:00:00Z",
    })


def _aus(id_: UUID, empleado_id: UUID, empresa_id: UUID) -> AusenciaResponse:
    ayer = date.today() - timedelta(days=10)
    return AusenciaResponse.model_validate({
        "id": str(id_), "empleado_id": str(empleado_id), "empresa_id": str(empresa_id),
        "fecha_desde": str(ayer), "fecha_hasta": str(ayer), "dias": 1,
        "justificada": True, "tipo_id": "88888888-8888-8888-8888-888888888888",
        "created_at": "2024-01-01T00:00:00Z",
    })


class _Repo:
    """HONRA empresa_id en el WHERE, como el find_by_id real de ambos repos."""

    def __init__(self, builder) -> None:
        self._build = builder

    def find_by_id(self, id, empresa_id=None):
        fila = _SOLICITUDES.get(str(id))
        if not fila:
            return None
        empleado_id, empresa = fila
        if empresa_id and str(empresa) != str(empresa_id):
            return None
        return self._build(UUID(str(id)), empleado_id, empresa)


class _Ownership:
    """El mando MANDO_UID es MANDO_EMP y tiene a SUBORDINADO a cargo. NO_GESTIONADO queda fuera."""

    def find_by_user_id(self, user_id):
        return {"id": str(MANDO_EMP)} if user_id == MANDO_UID else None

    def ids_subordinados(self, emp_id):
        return [str(SUBORDINADO)] if str(emp_id) == str(MANDO_EMP) else []


def _vac_svc():
    return VacacionesService(repo=_Repo(_vac), ownership_repo=_Ownership())


def _aus_svc():
    return AusenciasService(repo=_Repo(_aus), ownership_repo=_Ownership())


def _leer_vac(sol_id, empresa=EMPRESA_A, uid="admin", rol="admin_rrhh"):
    return _vac_svc().get_by_id(sol_id, empresa, uid, rol)


def _leer_aus(sol_id, empresa=EMPRESA_A, uid="admin", rol="admin_rrhh"):
    return _aus_svc().get_by_id(sol_id, empresa, uid, rol)


_LEER = [_leer_vac, _leer_aus]
_IDS = ["vacaciones", "ausencias"]


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── Eje OWNERSHIP (el que faltaba) ───────────────────────────────────────────

@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_mando_no_lee_solicitud_de_empleado_que_no_gestiona(leer):
    """Misma empresa, pero el empleado no es su subordinado → 404, no el detalle."""
    err = _error(lambda: leer(SOL_NO_GESTIONADO, uid=MANDO_UID, rol="mandos_medios"))
    assert err.status_code == 404


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_solicitud_no_gestionada_indistinguible_de_inexistente(leer):
    """No delata que la solicitud existe: mismo code, mensaje y status."""
    fuera = _error(lambda: leer(SOL_NO_GESTIONADO, uid=MANDO_UID, rol="mandos_medios"))
    inexistente = _error(lambda: leer(SOL_INEXISTENTE, uid=MANDO_UID, rol="mandos_medios"))
    assert (fuera.code, fuera.message, fuera.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_mando_lee_solicitud_de_su_subordinado(leer):
    assert leer(SOL_SUBORDINADO, uid=MANDO_UID, rol="mandos_medios") is not None


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
@pytest.mark.parametrize("rol", ["admin_rrhh", "gerencia_lectura"])
def test_admin_y_gerencia_sin_restriccion_de_ownership(leer, rol):
    """ids_empleados_visibles devuelve None para estos roles = sin restringir."""
    assert leer(SOL_NO_GESTIONADO, uid="u", rol=rol) is not None


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_rol_desconocido_fail_closed(leer):
    err = _error(lambda: leer(SOL_SUBORDINADO, uid="u", rol="rol_inventado"))
    assert err.status_code == 404


# ── Eje EMPRESA (no debe romperse al sumar ownership) ────────────────────────

@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_solicitud_de_otra_empresa_404(leer):
    err = _error(lambda: leer(SOL_AJENA, empresa=EMPRESA_A))
    assert err.status_code == 404


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_solicitud_ajena_indistinguible_de_inexistente(leer):
    ajena = _error(lambda: leer(SOL_AJENA, empresa=EMPRESA_A))
    inexistente = _error(lambda: leer(SOL_INEXISTENTE, empresa=EMPRESA_A))
    assert (ajena.code, ajena.message, ajena.status_code) == \
           (inexistente.code, inexistente.message, inexistente.status_code)


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_consolidado_no_restringe(leer):
    assert leer(SOL_AJENA, empresa=None) is not None


# ── La excepción de mandos_medios: el manager_id gana sobre la empresa ───────

@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_mando_LEE_la_solicitud_de_su_subordinado_de_OTRA_empresa(leer):
    """🔴 INVERTIDO (2/8/2026) — antes era `test_empresa_se_evalua_antes_que_ownership`, y
    afirmaba 404 "aunque el rol SÍ gestione a ese empleado". Ese "aunque" es exactamente el caso
    que la decisión de producto habilita: si le reporta, es suyo, sea de la empresa que sea.

    SOL_AJENA es de SUBORDINADO (a cargo del mando) pero de EMPRESA_B, y el header dice EMPRESA_A.
    Para que este test pueda fallar alcanza con que `empresa_efectiva` deje de devolver None para
    mandos_medios: el fake HONRA empresa_id, así que el `find_by_id` volvería None y saldría 404.
    """
    assert leer(SOL_AJENA, empresa=EMPRESA_A, uid=MANDO_UID, rol="mandos_medios") is not None


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_soltar_la_empresa_NO_es_soltar_el_ownership(leer):
    """El control del control. Otra empresa Y fuera de su alcance → sigue siendo 404.

    Es el test que distingue "el manager_id reemplaza a la empresa" de "el mando ve todo": sin él,
    borrar `puede_gestionar_empleado` del service dejaría el archivo entero en verde."""
    err = _error(lambda: leer(SOL_AJENA_NO_GESTIONADA, empresa=EMPRESA_A,
                              uid=MANDO_UID, rol="mandos_medios"))
    assert err.status_code == 404


@pytest.mark.parametrize("leer", _LEER, ids=_IDS)
def test_la_excepcion_NO_alcanza_a_admin_ni_a_gerencia(leer):
    """El eje de empresa sigue rigiendo para los otros dos roles: la excepción es de un rol solo.
    Mismo dato que el test anterior de mando (SOL_AJENA + EMPRESA_A), distinto rol, distinto
    resultado — que es la forma de probar que la condición del `if` es el ROL y no otra cosa."""
    for rol in ("admin_rrhh", "gerencia_lectura"):
        err = _error(lambda: leer(SOL_AJENA, empresa=EMPRESA_A, uid="u", rol=rol))
        assert err.status_code == 404
