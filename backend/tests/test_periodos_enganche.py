"""
Tests del enganche del bloqueo por período en ausencias, vacaciones y costos (overlap).

Repos fake + FakePeriodos + FakeOwnership inyectados por constructor. El bloqueo aplica SOLO a
mandos_medios cuando las FECHAS DEL REGISTRO se solapan con un período cerrado (la fecha de carga
no influye). admin_rrhh / gerencia_lectura nunca se bloquean; costos (admin, rol=None) tampoco.
Períodos y registros son fechas ABSOLUTAS fijas → deterministas para siempre.
Un mando gestiona a _EMP vía el FakeOwnership (subordinado).
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
from uuid import uuid4

import pytest

from schemas.ausencias import AusenciaCreate, AusenciaResponse, AusenciaUpdate
from schemas.costo import NominaCreate, NominaResponse
from schemas.periodo import PeriodoResponse
from schemas.vacaciones import SolicitudVacacionesCreate, SolicitudVacacionesResponse
from services.ausencias_service import AusenciasService
from services.costo_service import CostoService
from services.vacaciones_service import VacacionesService
from utils.errors import AppError

_EMP = uuid4()
_TIPO = uuid4()
# Fechas absolutas: lo que decide es registro↔período, no período↔hoy.
_PERIODO = (date(2026, 3, 1), date(2026, 3, 31))      # marzo 2026 cerrado
_REG_DENTRO = (date(2026, 3, 10), date(2026, 3, 12))  # solapa _PERIODO
_REG_FUERA = (date(2026, 8, 10), date(2026, 8, 12))   # no solapa _PERIODO


def _periodo(modulo=None, desde=None, hasta=None) -> PeriodoResponse:
    """Período CERRADO. Por defecto marzo 2026 (_PERIODO); pasar desde/hasta para variar."""
    return PeriodoResponse(
        id="p1", empresa_id="e1", modulo=modulo,
        desde=desde or _PERIODO[0], hasta=hasta or _PERIODO[1],
        estado="cerrado", cerrado_por="u1", cerrado_at=datetime(2026, 3, 1, 9, 0),
    )


class _FakeAudit:
    def registrar(self, **kwargs) -> None:
        pass


class _FakePeriodos:
    """Solo implementa lo que usa verificar_periodo_abierto: find_cerrados."""

    def __init__(self, cerrados=None) -> None:
        self._c = cerrados or []

    def find_cerrados(self, empresa_id, modulo):
        return [p for p in self._c if p.modulo is None or p.modulo == modulo]


class _FakeOwnership:
    """Un mando cuyo subordinado directo es _EMP → puede_gestionar_empleado(_EMP) = True."""

    def find_by_user_id(self, user_id):
        return {"id": "mando-1"}

    def ids_subordinados(self, emp_id):
        return [str(_EMP)]


def _ausencia(fd, fh) -> AusenciaResponse:
    return AusenciaResponse(
        id="a1", empresa_id="e1", empleado_id=str(_EMP), tipo_id=str(_TIPO),
        fecha_desde=fd, fecha_hasta=fh, dias=1, justificada=True, created_at=datetime(2026, 1, 1, 9, 0),
    )


class _FakeAusRepo:
    def __init__(self, existing=None) -> None:
        self._existing = existing
        self.saved = False
        self.deleted = False

    def find_empresa_for_empleado(self, empleado_id):
        return "e1"

    def find_by_id(self, id, empresa_id=None):
        return self._existing

    def save(self, *a, **k):
        self.saved = True
        return _ausencia(*_REG_FUERA)

    def update(self, id, empresa_id, payload):
        return _ausencia(*_REG_FUERA)

    def delete(self, id, empresa_id=None):
        self.deleted = True
        return True


# ── Ausencias ────────────────────────────────────────────────────────────────

def test_ausencia_crear_en_periodo_cerrado_409():
    # mando + registro cuyas fechas solapan el período cerrado → 409
    svc = AusenciasService(repo=_FakeAusRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    with pytest.raises(AppError) as e:
        svc.create(AusenciaCreate(empleado_id=_EMP, tipo_id=_TIPO, fecha_desde=_REG_DENTRO[0], fecha_hasta=_REG_DENTRO[1]), "u1", rol="mandos_medios")
    assert e.value.code == "PERIODO_CERRADO" and e.value.status_code == 409


def test_ausencia_crear_fuera_ok():
    # mando + registro fuera del período (agosto vs marzo) → no bloquea
    repo = _FakeAusRepo()
    svc = AusenciasService(repo=repo, audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    svc.create(AusenciaCreate(empleado_id=_EMP, tipo_id=_TIPO, fecha_desde=_REG_FUERA[0], fecha_hasta=_REG_FUERA[1]), "u1", rol="mandos_medios")
    assert repo.saved is True


def test_ausencia_crear_admin_no_bloquea():
    # rol NO-mando: el registro SOLAPA (un mando recibiría 409), pero admin_rrhh no se bloquea.
    repo = _FakeAusRepo()
    svc = AusenciasService(repo=repo, audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]))
    svc.create(AusenciaCreate(empleado_id=_EMP, tipo_id=_TIPO, fecha_desde=_REG_DENTRO[0], fecha_hasta=_REG_DENTRO[1]), "u1", rol="admin_rrhh")
    assert repo.saved is True


def test_ausencia_editar_en_periodo_cerrado_409():
    # SACAR de un período cerrado: el registro existente solapa → no se puede editar (1ª llamada)
    repo = _FakeAusRepo(existing=_ausencia(*_REG_DENTRO))
    svc = AusenciasService(repo=repo, audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    with pytest.raises(AppError) as e:
        svc.update(uuid4(), AusenciaUpdate(motivo="x"), rol="mandos_medios")
    assert e.value.code == "PERIODO_CERRADO"


def test_ausencia_editar_metiendo_en_periodo_cerrado_409():
    # METER en un período cerrado: el registro está fuera, pero la edición lo mueve DENTRO (2ª llamada)
    repo = _FakeAusRepo(existing=_ausencia(*_REG_FUERA))
    svc = AusenciasService(repo=repo, audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    with pytest.raises(AppError) as e:
        svc.update(uuid4(), AusenciaUpdate(fecha_desde=_REG_DENTRO[0], fecha_hasta=_REG_DENTRO[1]), rol="mandos_medios")
    assert e.value.code == "PERIODO_CERRADO"


def test_ausencia_borrar_en_periodo_cerrado_409():
    repo = _FakeAusRepo(existing=_ausencia(*_REG_DENTRO))
    svc = AusenciasService(repo=repo, audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    with pytest.raises(AppError) as e:
        svc.delete(uuid4(), rol="mandos_medios")
    assert e.value.code == "PERIODO_CERRADO" and repo.deleted is False


# ── Vacaciones ───────────────────────────────────────────────────────────────

class _FakeVacRepo:
    def find_empresa_for_empleado(self, empleado_id):
        return "e1"

    def find_overlapping(self, *a, **k):
        return []

    def save(self, *a, **k):
        return SolicitudVacacionesResponse(
            id="v1", empresa_id="e1", empleado_id=str(_EMP), fecha_desde=_REG_FUERA[0], fecha_hasta=_REG_FUERA[1],
            dias=1, tipo="vacaciones", cancelada=False, estado="planificada", created_at=datetime(2026, 1, 1, 9, 0),
        )


def test_vacacion_crear_en_periodo_cerrado_409():
    # mando + registro cuyas fechas solapan el período cerrado → 409
    svc = VacacionesService(repo=_FakeVacRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    with pytest.raises(AppError) as e:
        svc.create(SolicitudVacacionesCreate(empleado_id=_EMP, fecha_desde=_REG_DENTRO[0], fecha_hasta=_REG_DENTRO[1]), "u1", rol="mandos_medios")
    assert e.value.code == "PERIODO_CERRADO"


def test_vacacion_crear_fuera_ok():
    # mando + registro fuera del período → no bloquea
    svc = VacacionesService(repo=_FakeVacRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]), ownership_repo=_FakeOwnership())
    out = svc.create(SolicitudVacacionesCreate(empleado_id=_EMP, fecha_desde=_REG_FUERA[0], fecha_hasta=_REG_FUERA[1]), "u1", rol="mandos_medios")
    assert out.id == "v1"


# ── Costos / Nómina ──────────────────────────────────────────────────────────

class _FakeNominaRepo:
    def save_nomina(self, data):
        return NominaResponse(
            id="n1", empleado_id=str(_EMP), empresa_id="e1", empleado_nombre="Ana Lopez",
            area_nombre="Sistemas", mes=data.mes, anio=data.anio, monto_bruto=100.0, monto_neto=80.0, total=100.0,
        )


def test_nomina_admin_no_bloquea_con_periodo_cerrado():
    # El mes 3/2026 expande a [01/03, 31/03] y solapa EXACTO el período cerrado; igual no bloquea,
    # porque el ROL DEL LLAMADOR es admin_rrhh → early return por rol. Antes el enganche pasaba
    # rol=None hardcodeado, así que este test pasaba sin importar quién llamara: era un check que
    # no chequeaba. Ahora el rol viaja de verdad desde el router.
    svc = CostoService(nomina_repo=_FakeNominaRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]))
    data = NominaCreate(empleado_id=str(_EMP), mes=3, anio=2026, monto_bruto=100.0, monto_neto=80.0)
    out = svc.cargar_nomina(data, empresa_id="e1", usuario_id="u1", rol="admin_rrhh")
    assert out.mes == 3


def test_nomina_mando_bloquea_con_periodo_cerrado():
    # El caso que el hardcodeo volvía imposible de alcanzar: un mandos_medios sobre un período
    # cerrado SÍ tiene que frenar. Hoy ese rol no llega a costos, pero el check ya no depende de eso.
    svc = CostoService(nomina_repo=_FakeNominaRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]))
    data = NominaCreate(empleado_id=str(_EMP), mes=3, anio=2026, monto_bruto=100.0, monto_neto=80.0)
    with pytest.raises(AppError) as e:
        svc.cargar_nomina(data, empresa_id="e1", usuario_id="u1", rol="mandos_medios")
    assert e.value.code == "PERIODO_CERRADO"


def test_nomina_mando_fuera_del_periodo_ok():
    # mando + mes que no solapa el período cerrado → no bloquea
    svc = CostoService(nomina_repo=_FakeNominaRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([_periodo()]))
    data = NominaCreate(empleado_id=str(_EMP), mes=8, anio=2026, monto_bruto=100.0, monto_neto=80.0)
    out = svc.cargar_nomina(data, empresa_id="e1", usuario_id="u1", rol="mandos_medios")
    assert out.mes == 8


def test_nomina_cargar_sin_periodo_ok():
    # sin períodos cerrados → carga normal
    svc = CostoService(nomina_repo=_FakeNominaRepo(), audit=_FakeAudit(), periodo_repo=_FakePeriodos([]))
    data = NominaCreate(empleado_id=str(_EMP), mes=4, anio=2026, monto_bruto=100.0, monto_neto=80.0)
    out = svc.cargar_nomina(data, empresa_id="e1", usuario_id="u1")
    assert out.mes == 4
