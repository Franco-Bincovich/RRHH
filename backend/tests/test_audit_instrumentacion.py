"""
Tests de instrumentación de audit (T18.4b): vacaciones · ausencias · offboarding.

Se inyectan repos fake + un AuditService fake (los services aceptan `audit=` y `repo=`
por constructor) para no tocar DB. El foco: tras una mutación exitosa el service llama
a audit.registrar UNA vez con el evento/accion/entidad correctos, y los routers ya
threadean usuario_id. Mockeo total — sin Supabase.
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

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from schemas.ausencias import AusenciaResponse
from schemas.vacaciones import SolicitudVacacionesResponse
from services.ausencias_service import AusenciasService
from services.vacaciones_service import VacacionesService


class _FakeAudit:
    """Captura las llamadas a registrar() como lista de payloads (kwargs)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _SinPeriodos:
    """periodo_repo fake sin cierres: el check de B3.2 no bloquea nada."""

    def find_cerrados(self, _empresa, _modulo):
        return []


EMPRESA_TEST = uuid4()


class _EmpleadoRepoDeEmpresa:
    """empleado_repo fake que HONRA empresa_id (no lo acepta y lo ignora): devuelve None si el
    empleado no es de esa empresa, como el _with_empresa real. Necesario desde el gate de
    empresa ∩ ownership en get_by_empleado/get_saldo."""

    def __init__(self, empleado_id, empresa_id) -> None:
        self._id, self._empresa = str(empleado_id), empresa_id

    def find_by_id(self, id, empresa_id=None):
        if str(id) != self._id or (empresa_id and str(empresa_id) != str(self._empresa)):
            return None
        return SimpleNamespace(id=self._id, empresa_id=str(self._empresa))


class _SinOwnership:
    """ownership_repo fake: con rol admin_rrhh nunca se consulta (ids_empleados_visibles corta
    antes), pero se inyecta para no instanciar el repo real contra Supabase."""

    def find_by_user_id(self, _uid):
        return None

    def ids_subordinados(self, _emp_id):
        return []


def _vacacion(cancelada: bool) -> SolicitudVacacionesResponse:
    return SolicitudVacacionesResponse(
        id="v1", empresa_id="e1", empleado_id="emp1",
        fecha_desde=date(2026, 7, 1), fecha_hasta=date(2026, 7, 5), dias=5,
        tipo="vacaciones", cancelada=cancelada, estado="", created_at=datetime(2026, 6, 1, 9, 0),
    )


def _ausencia(**over) -> AusenciaResponse:
    base = dict(
        id="a1", empresa_id="e1", empleado_id="emp1", tipo_id="t1",
        fecha_desde=date(2026, 7, 1), fecha_hasta=date(2026, 7, 2), dias=2,
        justificada=False, motivo=None, created_at=datetime(2026, 6, 1, 9, 0),
    )
    base.update(over)
    return AusenciaResponse(**base)


class _FakeVacRepo:
    def __init__(self) -> None:
        self.prior = _vacacion(cancelada=False)
        self.updated = _vacacion(cancelada=True)

    def find_by_id(self, _id, _empresa=None):
        # HONRA _empresa (ver nota en test_escrituras_ownership): los tests llaman con None.
        if _empresa and str(self.prior.empresa_id) != str(_empresa):
            return None
        return self.prior

    def cancel(self, _id, _empresa=None):
        return self.updated


class _FakeAusRepo:
    def __init__(self) -> None:
        self.row = _ausencia()
        self.updated = _ausencia(justificada=True)

    def find_empresa_for_empleado(self, _emp):
        return "e1"

    def find_by_id(self, _id, _empresa=None):
        # HONRA _empresa (ver nota en test_escrituras_ownership): los tests llaman con None.
        if _empresa and str(self.row.empresa_id) != str(_empresa):
            return None
        return self.row

    def save(self, *a, **k):
        return self.row

    def update(self, _id, _empresa, _payload):
        return self.updated

    def delete(self, _id, _empresa=None):
        return True


class TestVacacionesAudit:
    def test_cancel_registra_evento(self) -> None:
        audit = _FakeAudit()
        svc = VacacionesService(repo=_FakeVacRepo(), audit=audit, periodo_repo=_SinPeriodos())
        svc.cancel(uuid4(), empresa_id=None, usuario_id="u1", rol="admin_rrhh")
        assert len(audit.calls) == 1
        c = audit.calls[0]
        assert c["evento"] == "cancelacion_vacacion"
        assert c["accion"] == "UPDATE"
        assert c["entidad"] == "vacacion"
        assert c["usuario_id"] == "u1"
        # diff: cancelada False→True quedó capturado
        assert c["datos_anteriores"]["cancelada"] is False
        assert c["datos_nuevos"]["cancelada"] is True


class TestAusenciasAudit:
    def test_create_registra_alta(self) -> None:
        audit = _FakeAudit()
        svc = AusenciasService(repo=_FakeAusRepo(), audit=audit, periodo_repo=_SinPeriodos())
        from schemas.ausencias import AusenciaCreate
        svc.create(
            AusenciaCreate(empleado_id=uuid4(), tipo_id=uuid4(),
                           fecha_desde=date(2026, 7, 1), fecha_hasta=date(2026, 7, 2)),
            created_by="u1", rol="admin_rrhh",
        )
        assert len(audit.calls) == 1
        c = audit.calls[0]
        assert c["evento"] == "alta_ausencia"
        assert c["accion"] == "INSERT"
        assert c["usuario_id"] == "u1"
        assert c["datos_anteriores"] is None

    def test_delete_lee_prior_y_registra_baja(self) -> None:
        audit = _FakeAudit()
        svc = AusenciasService(repo=_FakeAusRepo(), audit=audit, periodo_repo=_SinPeriodos())
        svc.delete(uuid4(), empresa_id=None, usuario_id="u1", rol="admin_rrhh")
        assert len(audit.calls) == 1
        c = audit.calls[0]
        assert c["evento"] == "baja_ausencia"
        assert c["accion"] == "DELETE"
        assert c["datos_nuevos"] is None
        assert c["datos_anteriores"]["empleado_id"] == "emp1"  # subset del prior


class TestVacacionesPorEmpleado:
    def test_get_by_empleado_devuelve_lista_con_total(self) -> None:
        # get_by_empleado ahora exige el gate empresa ∩ ownership (Tanda 1b.2): hay que inyectar
        # el repo de empleados y el de ownership, y find_vacaciones_empleado recibe empresa_id.
        emp_id = uuid4()

        class _Repo:
            def find_vacaciones_empleado(self, _emp, empresa_id=None):
                return [_vacacion(cancelada=False), _vacacion(cancelada=False)]

        svc = VacacionesService(repo=_Repo(), audit=_FakeAudit(),
                                empleado_repo=_EmpleadoRepoDeEmpresa(emp_id, EMPRESA_TEST),
                                ownership_repo=_SinOwnership())
        res = svc.get_by_empleado(emp_id, "u1", "admin_rrhh", EMPRESA_TEST)
        assert res.total == 2
        assert len(res.items) == 2
        assert res.items[0].empleado_id == "emp1"


class TestNoRegistraSiFalla:
    def test_cancel_ya_cancelada_no_registra(self) -> None:
        # Mutación que falla con AppError (ya cancelada) → no se audita.
        from utils.errors import AppError

        audit = _FakeAudit()
        repo = _FakeVacRepo()
        repo.prior = _vacacion(cancelada=True)  # ya cancelada → YA_CANCELADA
        svc = VacacionesService(repo=repo, audit=audit, periodo_repo=_SinPeriodos())
        try:
            svc.cancel(uuid4(), usuario_id="u1")
        except AppError:
            pass
        assert audit.calls == []  # registrar nunca se llamó
