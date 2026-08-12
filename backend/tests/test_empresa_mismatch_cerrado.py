"""
El oráculo `EMPRESA_MISMATCH` (422), cerrado en los dos lugares donde quedaba vivo.

QUÉ ERA: estos dos altas no reciben un id en el path — cruzan DOS entidades (empleado × curso,
empleado × ciclo) — así que se escaparon del barrido de la Fase 2, que cerró 92 endpoints. El
segundo lookup no acotaba por empresa y el desajuste salía con status propio: el id de un recurso
de OTRA empresa devolvía **422** mientras que un id inventado devolvía **404**. Esa diferencia
confirma que el recurso ajeno existe, que es exactamente el oráculo de enumeración que la regla
del 404 idéntico prohíbe.

QUÉ SE PRUEBA ACÁ, en dos niveles distintos y los dos necesarios:
  1. **El contrato**: "de otra empresa" y "no existe" devuelven el MISMO status, el MISMO code y
     el MISMO mensaje. Se compara el AppError entero, no solo el 404 — un mensaje distinto
     reabriría el oráculo aunque el status coincidiera.
  2. **Que el filtro viaje EN LA QUERY** (Forma A). Es el escalón que el fake de repo no puede
     ver: comparar en Python después de traer la fila también daría 404, pero con la fila ajena
     ya en memoria. Por eso hay un espía del cliente de Supabase.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Los dos fakes modelan DOS empresas y **honran el `empresa_id` que reciben**: devuelven None
    cuando no coincide, igual que el WHERE real. Un fake que aceptara el parámetro y lo ignorara
    daría verde con el bug puesto — es el caso #1 de CLAUDE.md.
  · El espía de Supabase acumula los `.eq()` de verdad: si alguien saca el filtro de la query y
    lo reimplementa en Python, el contrato sigue en verde pero el espía falla.
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
from uuid import uuid4

import pytest

from schemas.capacitacion import AsignacionCreate
from services.asignacion_service import AsignacionService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())
EMPLEADO_A = uuid4()
CURSO_A, CURSO_B, CURSO_FANTASMA = uuid4(), uuid4(), uuid4()


# ══ 1. Capacitaciones: el curso se busca acotado a la empresa del empleado ══════════════════


class _FakeAsignacionRepo:
    """El empleado es el ancla: de él sale la empresa en la que se escribe."""

    def find_empresa_for_empleado(self, empleado_id):
        return EMPRESA_A if str(empleado_id) == str(EMPLEADO_A) else None

    def save(self, cap_id, emp_id, empresa_id, *_a):
        return SimpleNamespace(id=str(uuid4()), empresa_id=empresa_id)


class _FakeCapacitacionRepo:
    """DOS empresas, y HONRA `empresa_id`: devuelve None cuando el curso existe pero es de otra,
    que es lo que hace el `.eq()` real. Sin esto el test no podría distinguir el fix del bug."""

    def __init__(self) -> None:
        self.recibido: list = []

    def find_empresa_for(self, id, empresa_id=None):
        self.recibido.append((str(id), empresa_id))
        de = {str(CURSO_A): EMPRESA_A, str(CURSO_B): EMPRESA_B}.get(str(id))
        if de is None or (empresa_id and de != empresa_id):
            return None
        return de


def _svc_capacitaciones():
    caps = _FakeCapacitacionRepo()
    return AsignacionService(repo=_FakeAsignacionRepo(), cap_repo=caps), caps


def _asignar(curso):
    svc, caps = _svc_capacitaciones()
    with pytest.raises(AppError) as exc:
        svc.create(AsignacionCreate(capacitacion_id=curso, empleado_id=EMPLEADO_A), "tester")
    return exc.value, caps


class TestCursoDeOtraEmpresa:
    def test_ya_no_devuelve_422(self) -> None:
        """El 422 era el oráculo entero: bastaba mirar el status para saber que el curso existe."""
        err, _ = _asignar(CURSO_B)
        assert err.status_code == 404 and err.code != "EMPRESA_MISMATCH"

    def test_es_INDISTINGUIBLE_de_un_curso_inexistente(self) -> None:
        """El corazón del fix. Status, code y mensaje idénticos: no queda ni un bit que
        diferencie "existe pero es ajeno" de "no existe"."""
        ajeno, _ = _asignar(CURSO_B)
        fantasma, _ = _asignar(CURSO_FANTASMA)
        assert (ajeno.status_code, ajeno.code, ajeno.message) == (
            fantasma.status_code, fantasma.code, fantasma.message)

    def test_el_curso_de_la_empresa_propia_sigue_asignandose(self) -> None:
        """El control del control: si el filtro rechazara todo, los tres tests de arriba
        pasarían igual y no habría feature."""
        svc, _ = _svc_capacitaciones()
        assert svc.create(AsignacionCreate(capacitacion_id=CURSO_A, empleado_id=EMPLEADO_A), "t")

    def test_el_service_le_PASA_la_empresa_al_repo(self) -> None:
        """Si el service dejara de pasarla, el repo volvería al lookup global y el desajuste
        habría que detectarlo después — que es de dónde venimos."""
        _, caps = _asignar(CURSO_B)
        assert caps.recibido == [(str(CURSO_B), EMPRESA_A)]


class TestElWhereDelCursoLlevaLaEmpresa:
    """Un escalón más abajo: que el filtro esté en la QUERY y no en un `if` de Python. El fake
    de repo de arriba no puede ver la diferencia — las dos formas devuelven 404."""

    def _repo_con_espia(self, monkeypatch):
        import repositories.capacitacion_repo as mod
        eqs: list = []

        class _Q:
            def select(self, *a, **k):
                return self

            def eq(self, col, val):
                eqs.append((col, val))
                return self

            def maybe_single(self):
                return self

            def execute(self):
                return SimpleNamespace(data=None)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.CapacitacionRepo(), eqs

    def test_la_empresa_viaja_en_el_where(self, monkeypatch) -> None:
        repo, eqs = self._repo_con_espia(monkeypatch)
        repo.find_empresa_for(str(CURSO_B), EMPRESA_A)
        assert ("empresa_id", EMPRESA_A) in eqs

    def test_sin_empresa_el_lookup_sigue_siendo_global(self, monkeypatch) -> None:
        """La firma quedó retrocompatible a propósito: el parámetro es opcional."""
        repo, eqs = self._repo_con_espia(monkeypatch)
        repo.find_empresa_for(str(CURSO_B))
        assert eqs == [("id", str(CURSO_B))]


# ══ 2. Evaluaciones: BORRADO el 2026-08-11 (bloque J5a) ════════════════════════════════════
#
# Acá vivía `TestEmpleadoDeOtraEmpresaEnElCiclo` (4 tests) sobre `_ev_instancia_crear.crear`:
# verificaba que el empleado se buscara acotado a la empresa del CICLO, no a la del header.
# Se fue con el módulo `ev_*` entero —17 archivos, 19 endpoints— que estaba publicado por HTTP
# y era inalcanzable desde la UI. Las tablas `ev_*` siguen en la base hasta la migración de J5b.
#
# 🔴 NO se perdió cobertura de la barrera de empresa: el eje que estos tests cubrían —que la
# empresa viaje EN EL WHERE y no en un `if` posterior— lo sigue cubriendo el bloque 1 de este
# mismo archivo (`TestElWhereDelCursoLlevaLaEmpresa`), que es su homólogo de capacitaciones y
# fue el molde del que estos salieron.
