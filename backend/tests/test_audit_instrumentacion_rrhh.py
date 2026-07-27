"""
Tests de instrumentación de audit (T18.4c): empleados · costos · empresa.

Repos fake + AuditService fake inyectados por constructor (sin DB). Foco: tras la
mutación exitosa el service llama a audit.registrar una vez con el evento/accion/entidad
correctos; empleado.update/deactivate LEEN el estado anterior (read-before); empresa
audita solo el toggle dedicado.
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

from schemas.costo import NominaResponse, PresupuestoResponse
from schemas.empleado import EmpleadoResponse, EmpleadoUpdate
from schemas.empresa import EmpresaResponse
from services.costo_service import CostoService
from services.empleado_service import EmpleadoService
from services.empresa_service import EmpresaService


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


def _empleado(**over) -> EmpleadoResponse:
    base = dict(
        id="emp1", nombre="Ana", apellido="Lopez", email_corporativo="a@x.com",
        empresa_id="e1", area_id="ar1", roles=["Dev"], cargo="Dev", modalidad_trabajo="remoto",
        tipo_contrato="indefinido", fecha_ingreso=date(2025, 1, 1), estado="activo",
        created_at=datetime(2026, 1, 1, 9, 0),
    )
    base.update(over)
    return EmpleadoResponse(**base)


class _FakeEmpRepo:
    def __init__(self) -> None:
        self.prior = _empleado(cargo="Dev")
        self.updated = _empleado(cargo="Lead")
        self.find_by_id_calls = 0

    def find_by_legajo(self, *a, **k):
        return None

    def find_by_id(self, _id, _empresa=None):
        self.find_by_id_calls += 1
        return self.prior

    def save(self, _data, _empresa):
        return self.prior

    def update(self, _id, _data, _empresa=None):
        return self.updated

    def soft_delete(self, _id, _empresa=None):
        return True


class _AreaRepoPermisivo:
    """area_repo fake permisivo: este test es de AUDITORÍA, no del gate de área (ese vive en
    test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


class TestEmpleadoAudit:
    def test_create_registra_alta(self) -> None:
        audit = _FakeAudit()
        svc = EmpleadoService(repo=_FakeEmpRepo(), audit=audit, area_repo=_AreaRepoPermisivo())
        from schemas.empleado import EmpleadoCreate
        svc.create_empleado(
            EmpleadoCreate(nombre="Ana", apellido="Lopez", email_corporativo="a@x.com",
                           area_id=uuid4(), roles=["Dev"], modalidad_trabajo="remoto",
                           tipo_contrato="indefinido", fecha_ingreso=date(2025, 1, 1),
                           empresa_id=uuid4()),
            created_by="u1", empresa_id=uuid4(),
        )
        assert len(audit.calls) == 1
        c = audit.calls[0]
        assert (c["evento"], c["accion"], c["entidad"]) == ("alta_empleado", "INSERT", "empleado")
        assert c["usuario_id"] == "u1"

    def test_update_lee_prior_y_diff(self) -> None:
        audit = _FakeAudit()
        repo = _FakeEmpRepo()
        svc = EmpleadoService(repo=repo, audit=audit)
        svc.update_empleado(uuid4(), EmpleadoUpdate(cargo="Lead"), empresa_id=None, usuario_id="u1")
        assert repo.find_by_id_calls == 1  # read-before ejecutado
        c = audit.calls[0]
        assert c["evento"] == "update_empleado" and c["accion"] == "UPDATE"
        # diff: cargo Dev→Lead capturado
        assert c["datos_anteriores"]["cargo"] == "Dev"
        assert c["datos_nuevos"]["cargo"] == "Lead"

    def test_deactivate_lee_prior_y_registra_baja(self) -> None:
        audit = _FakeAudit()
        repo = _FakeEmpRepo()
        svc = EmpleadoService(repo=repo, audit=audit)
        svc.deactivate_empleado(uuid4(), empresa_id=None, usuario_id="u1")
        assert repo.find_by_id_calls == 1  # read-before antes del soft_delete
        c = audit.calls[0]
        assert c["evento"] == "baja_empleado" and c["accion"] == "DELETE"
        assert c["datos_nuevos"] is None
        assert c["datos_anteriores"]["estado"] == "activo"


class TestCostoAudit:
    def test_cargar_nomina_usa_empresa_del_registro(self) -> None:
        audit = _FakeAudit()
        nomina = NominaResponse(id="n1", empleado_id="emp1", empresa_id="e9",
                                empleado_nombre="Ana", area_nombre="Dev", mes=6, anio=2026,
                                monto_bruto=100.0, monto_neto=80.0, total=100.0)

        class _Repo:
            def save_nomina(self, _d):
                return nomina

        from schemas.costo import NominaCreate
        svc = CostoService(nomina_repo=_Repo(), audit=audit)
        svc.cargar_nomina(NominaCreate(empleado_id="emp1", mes=6, anio=2026,
                                       monto_bruto=100.0, monto_neto=80.0),
                          empresa_id=None, usuario_id="u1")
        c = audit.calls[0]
        assert c["evento"] == "carga_nomina" and c["entidad"] == "nomina"
        assert c["empresa_id"] == "e9"  # del registro, no del header (None)

    def test_set_presupuesto_usa_empresa_del_header(self) -> None:
        audit = _FakeAudit()
        pres = PresupuestoResponse(id="p1", area_id="ar1", area_nombre="Dev",
                                   mes=6, anio=2026, presupuesto=500.0)

        class _Repo:
            def save_presupuesto(self, _d):
                return pres

        from schemas.costo import PresupuestoCreate
        svc = CostoService(presupuesto_repo=_Repo(), audit=audit)
        svc.set_presupuesto_area(PresupuestoCreate(area_id="ar1", mes=6, anio=2026, presupuesto=500.0),
                                 empresa_id=None, usuario_id="u1")
        c = audit.calls[0]
        assert c["evento"] == "set_presupuesto"
        assert c["empresa_id"] is None  # header consolidado → None (sin lookup)


class TestEmpresaAudit:
    def _empresa(self, activa: bool) -> EmpresaResponse:
        return EmpresaResponse(id="e1", nombre="Karstec", activa=activa,
                               created_at=datetime(2026, 1, 1, 9, 0))

    def test_toggle_registra_evento(self) -> None:
        audit = _FakeAudit()
        emp = self._empresa(activa=False)

        class _Repo:
            def update(self, _id, _data):
                return emp

        svc = EmpresaService(repo=_Repo(), audit=audit)
        svc.toggle_activa("e1", False, usuario_id="u1")
        c = audit.calls[0]
        assert c["evento"] == "toggle_empresa_activa" and c["accion"] == "UPDATE"
        assert c["registro_id"] == "e1" and c["empresa_id"] == "e1"
        assert c["datos_nuevos"] == {"activa": False}

    def test_update_generico_no_audita(self) -> None:
        # El PUT genérico (update_empresa) NO debe auditar — solo el toggle.
        audit = _FakeAudit()
        emp = self._empresa(activa=True)

        class _Repo:
            def update(self, _id, _data):
                return emp

        from schemas.empresa import EmpresaUpdate
        svc = EmpresaService(repo=_Repo(), audit=audit)
        svc.update_empresa("e1", EmpresaUpdate(nombre="Nuevo"))
        assert audit.calls == []  # ningún evento de audit
