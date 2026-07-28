"""
Entrevista de salida del offboarding: se persiste, se lee, y pasa por la barrera de empresa.

🚨 EL FAKE HONRA `empresa_id`. `update_entrevista` devuelve False cuando la instancia es de
otra empresa, que es lo que hace el WHERE real. Un fake que aceptara el parámetro y lo
ignorara daría verde sin validar nada — y el agujero que taparía es exactamente el que este
archivo existe para cubrir.

Las dos columnas ya estaban en la tabla desde su migración original: esta tanda las expone, no
las crea. Por eso no hay test de migración.
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

from uuid import uuid4

import pytest

from repositories._offboarding_row import inst_row
from services.offboarding_service import OffboardingService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
INST_A, INST_B = str(uuid4()), str(uuid4())


class _FakeRepo:
    """DOS empresas. `update_entrevista` filtra por empresa como lo hace el WHERE real."""

    def __init__(self) -> None:
        self.filas = {
            INST_A: {"empresa_id": str(EMPRESA_A), "entrevista_salida": False,
                     "notas_entrevista": None},
            INST_B: {"empresa_id": str(EMPRESA_B), "entrevista_salida": False,
                     "notas_entrevista": None},
        }

    def update_entrevista(self, instancia_id, entrevista_salida, notas, empresa_id=None):
        fila = self.filas.get(instancia_id)
        if not fila:
            return False
        if empresa_id and fila["empresa_id"] != str(empresa_id):
            return False
        fila["entrevista_salida"] = entrevista_salida
        fila["notas_entrevista"] = notas
        return True


class _FakeAudit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _svc() -> tuple:
    repo, audit = _FakeRepo(), _FakeAudit()
    svc = OffboardingService(repo=repo, audit=audit)
    return svc, repo, audit


class TestSePersiste:
    def test_marca_la_entrevista_como_hecha(self) -> None:
        svc, repo, _ = _svc()
        assert svc.registrar_entrevista(INST_A, True, "Se va contento", empresa_id=EMPRESA_A)
        assert repo.filas[INST_A]["entrevista_salida"] is True

    def test_guarda_las_notas(self) -> None:
        svc, repo, _ = _svc()
        svc.registrar_entrevista(INST_A, True, "Motivo real: sueldo", empresa_id=EMPRESA_A)
        assert repo.filas[INST_A]["notas_entrevista"] == "Motivo real: sueldo"

    def test_se_puede_marcar_sin_notas(self) -> None:
        """Registrar que la entrevista se hizo no obliga a dejar constancia escrita."""
        svc, repo, _ = _svc()
        svc.registrar_entrevista(INST_A, True, None, empresa_id=EMPRESA_A)
        assert repo.filas[INST_A]["entrevista_salida"] is True
        assert repo.filas[INST_A]["notas_entrevista"] is None

    def test_notas_vacias_no_guardan_string_vacio(self) -> None:
        """"" y None significan lo mismo para el usuario; que no signifiquen distinto en la base."""
        svc, repo, _ = _svc()
        svc.registrar_entrevista(INST_A, True, "", empresa_id=EMPRESA_A)
        assert repo.filas[INST_A]["notas_entrevista"] is None

    def test_se_puede_revertir(self) -> None:
        svc, repo, _ = _svc()
        svc.registrar_entrevista(INST_A, True, "algo", empresa_id=EMPRESA_A)
        svc.registrar_entrevista(INST_A, False, None, empresa_id=EMPRESA_A)
        assert repo.filas[INST_A]["entrevista_salida"] is False


class TestSeLee:
    def test_el_mapper_devuelve_los_dos_campos(self) -> None:
        r = inst_row({"id": uuid4(), "empleado_id": uuid4(), "empresa_id": EMPRESA_A,
                      "motivo_egreso": "renuncia", "estado": "iniciado",
                      "created_at": "2026-07-27T10:00:00",
                      "entrevista_salida": True, "notas_entrevista": "ok"}, [])
        assert r.entrevista_salida is True and r.notas_entrevista == "ok"

    def test_una_instancia_vieja_sin_datos_no_rompe(self) -> None:
        """Las instancias creadas antes de exponer el campo no traen nada: default False."""
        r = inst_row({"id": uuid4(), "empleado_id": uuid4(), "empresa_id": EMPRESA_A,
                      "motivo_egreso": "renuncia", "estado": "iniciado",
                      "created_at": "2026-07-27T10:00:00"}, [])
        assert r.entrevista_salida is False and r.notas_entrevista is None


class TestBarreraDeEmpresa:
    def test_no_se_puede_escribir_en_otra_empresa(self) -> None:
        svc, repo, _ = _svc()
        with pytest.raises(AppError):
            svc.registrar_entrevista(INST_B, True, "ajeno", empresa_id=EMPRESA_A)
        assert repo.filas[INST_B]["entrevista_salida"] is False

    def test_el_404_es_el_mismo_que_el_de_no_existe(self) -> None:
        """Un código distinto delataría que la instancia existe y es de otra empresa."""
        svc, _, _ = _svc()
        with pytest.raises(AppError) as ajena:
            svc.registrar_entrevista(INST_B, True, None, empresa_id=EMPRESA_A)
        with pytest.raises(AppError) as inexistente:
            svc.registrar_entrevista(str(uuid4()), True, None, empresa_id=EMPRESA_A)
        assert (ajena.value.code, ajena.value.status_code, ajena.value.message) == \
               (inexistente.value.code, inexistente.value.status_code, inexistente.value.message)

    def test_nunca_es_403(self) -> None:
        svc, _, _ = _svc()
        with pytest.raises(AppError) as exc:
            svc.registrar_entrevista(INST_B, True, None, empresa_id=EMPRESA_A)
        assert exc.value.status_code == 404

    def test_consolidado_alcanza_cualquiera(self) -> None:
        """empresa_id=None es la vista consolidada, no un fallo de validación."""
        svc, repo, _ = _svc()
        assert svc.registrar_entrevista(INST_B, True, None, empresa_id=None)
        assert repo.filas[INST_B]["entrevista_salida"] is True


class TestElWhereDelRepoLlevaLaEmpresa:
    """🔴 EL FAKE DE REPO NO ALCANZA PARA ESTA LÍNEA, y el mutation check lo mostró.

    Los tests de arriba reemplazan el repo entero, así que su `_with_empresa` real nunca se
    ejecuta: sacarlo del UPDATE deja todo en verde. Y esa es justamente la línea que sostiene
    la barrera. Acá se faltea un escalón más abajo —el cliente de Supabase— y se verifica que
    el filtro de empresa quede EN LA QUERY, que es la forma A del patrón: en el WHERE, no en
    una comparación posterior que se puede olvidar.

    (El mismo hueco existe en los otros tests de scope del repo, que también faltean al nivel
    del repo. Cerrarlo en todos es una tanda propia; esto es el molde.)"""

    def _repo_con_espia(self, monkeypatch):
        import repositories.offboarding_repo as mod

        aplicados: list = []

        class _Q:
            def update(self, *a, **k):
                return self

            def eq(self, col, val):
                aplicados.append((col, val))
                return self

            def execute(self):
                return type("R", (), {"data": [{"id": INST_A}]})()

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.OffboardingRepo(), aplicados

    def test_el_update_filtra_por_empresa(self, monkeypatch) -> None:
        repo, aplicados = self._repo_con_espia(monkeypatch)
        repo.update_entrevista(INST_A, True, "n", EMPRESA_A)
        assert ("empresa_id", str(EMPRESA_A)) in aplicados

    def test_el_update_siempre_filtra_por_id(self, monkeypatch) -> None:
        repo, aplicados = self._repo_con_espia(monkeypatch)
        repo.update_entrevista(INST_A, True, "n", EMPRESA_A)
        assert ("id", INST_A) in aplicados

    def test_consolidado_no_agrega_filtro_de_empresa(self, monkeypatch) -> None:
        """None es vista consolidada: no restringe, y tampoco debe filtrar por None."""
        repo, aplicados = self._repo_con_espia(monkeypatch)
        repo.update_entrevista(INST_A, True, "n", None)
        assert not [c for c, _ in aplicados if c == "empresa_id"]


class TestAuditoria:
    def test_audita_el_registro(self) -> None:
        svc, _, audit = _svc()
        svc.registrar_entrevista(INST_A, True, "notas", empresa_id=EMPRESA_A)
        assert [e["evento"] for e in audit.eventos] == ["entrevista_salida"]

    def test_no_audita_si_no_escribio(self) -> None:
        """Un intento rechazado no es un cambio: auditarlo ensuciaría el log con no-eventos."""
        svc, _, audit = _svc()
        with pytest.raises(AppError):
            svc.registrar_entrevista(INST_B, True, None, empresa_id=EMPRESA_A)
        assert audit.eventos == []

    def test_el_texto_de_las_notas_no_va_al_audit(self) -> None:
        """Una entrevista de salida puede hablar de terceros; el log lo lee más gente que la
        que la tomó. Se audita QUE hubo notas y su largo, no qué decían."""
        svc, _, audit = _svc()
        svc.registrar_entrevista(INST_A, True, "El jefe es un problema", empresa_id=EMPRESA_A)
        assert "El jefe" not in str(audit.eventos[0])
        assert audit.eventos[0]["datos_nuevos"]["notas_cargadas"] is True
