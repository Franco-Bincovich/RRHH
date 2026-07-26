"""
Tests del orquestador de import de evaluaciones (fase 4) — fakes, sin red.

Cubre: preview con los 3 estados (resuelto/ambiguo/sin_candidato) y aviso de período
existente, y confirmar con reimportación que pisa, guardado selectivo de equivalencias,
evaluado sin candidato (empleado_id null) y el rechazo de un empleado de otra empresa.

Incluye además la baja de un lote (EvaluacionService.delete_lote), que reusa el mismo
_FakeRepo: borrado con snapshot auditado, borrado desacoplado de la empresa activa (un lote
de otra empresa se borra igual), 404 del inexistente, fallo del repo, y la baja múltiple
(delete_lotes_bulk) con éxito parcial clasificado.
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

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from schemas.evaluacion_import import ResolucionIdentidad
from schemas.evaluacion_import_api import ConfirmarRequest, EvaluadoConfirm, ResultadoConfirm
from schemas.evaluacion_resultados import EvaluadoResponse, LoteResponse
from services import _evaluacion_import_transforms as tx
from services.evaluacion_import_orchestrator import EvaluacionImportOrchestrator
from services.evaluacion_service import EvaluacionService
from utils.errors import AppError

EMPRESA = uuid4()


# ── Fakes ─────────────────────────────────────────────────────────────────────

class _FakeSvc:
    # drop_evaluados / drop_resultados simulan un insert parcial SILENCIOSO (persiste de menos)
    # para probar la verificación por conteo del orchestrator.
    def __init__(self, drop_evaluados: int = 0, drop_resultados: int = 0) -> None:
        self.lote_creado = None
        self._drop_ev = drop_evaluados
        self._drop_res = drop_resultados

    def crear_lote(self, data):
        self.lote_creado = LoteResponse(id=uuid4(), empresa_id=data.empresa_id, periodo=data.periodo,
                                        importado_por=data.importado_por, created_at=datetime.now(timezone.utc))
        return self.lote_creado

    def guardar_evaluados(self, lote_id, filas):
        creados = [EvaluadoResponse(id=uuid4(), lote_id=lote_id, created_at=datetime.now(timezone.utc),
                                    **f.model_dump()) for f in filas]
        return creados[: len(creados) - self._drop_ev] if self._drop_ev else creados

    def guardar_resultados(self, evaluado_id, filas):
        n = len(filas)
        if self._drop_res > 0:  # persiste de menos una sola vez
            n -= self._drop_res
            self._drop_res = 0
        return n


class _FakeRepo:
    def __init__(self, prior=None, evaluados_prior=0, delete_ok=True, rename_ok=True) -> None:
        self.prior, self._n_prior, self.borrados = prior, evaluados_prior, []
        self._delete_ok = delete_ok
        self._rename_ok = rename_ok
        self.renombrados = []  # (lote_id, periodo) de cada update_periodo_lote

    def find_lote_by_periodo(self, empresa_id, periodo):
        return self.prior

    def find_lote_by_id(self, id):
        return self.prior if self.prior and str(self.prior.id) == str(id) else None

    def find_evaluados(self, lote_id):
        return [object()] * self._n_prior

    def delete_lote(self, id):
        self.borrados.append(id)
        return self._delete_ok

    def update_periodo_lote(self, id, periodo):
        if not self._rename_ok:
            raise AppError("Error al renombrar el lote de evaluación", "DB_ERROR", 500)
        self.renombrados.append((id, periodo))
        return self.prior  # el valor no lo usa el orchestrator


class _FakeMatcheo:
    def __init__(self, ids_empresa=()) -> None:
        from schemas.evaluacion_import import EmpleadoCandidato
        self._cands = [EmpleadoCandidato(empleado_id=i, apellido="X", nombre="Y") for i in ids_empresa]
        self.equivalencias = []

    def find_empleados_empresa(self, empresa_id):
        return list(self._cands)

    def crear_equivalencia(self, datos):
        self.equivalencias.append(datos)
        return datos


class _FakeAudit:
    def __init__(self) -> None:
        self.eventos = []

    def registrar(self, **kw):
        self.eventos.append(kw)


class _FakeResolutor:
    def __init__(self, por_nombre) -> None:
        self._m = por_nombre

    def resolver(self, empresa_id, apellido, nombre, apellido_superior=None, nombre_superior=None):
        return self._m[(apellido, nombre)]


# ── Helpers de CSV para el preview ────────────────────────────────────────────

def _desglose(filas: list[dict]) -> bytes:
    lineas = [";".join(tx.HEADERS_DESGLOSE)]
    lineas += [";".join(str(f.get(h, "")) for h in tx.HEADERS_DESGLOSE) for f in filas]
    return "\r\n".join(lineas).encode("utf-8")


def _fila(apellido, nombre, **comps) -> dict:
    return {"APELLIDO EVALUADO": apellido, "NOMBRE EVALUADO": nombre,
            "TIPO EVALUACION": "AUTOEVALUACION", **comps}


def _res(apellido, nombre, estado, empleado_id=None, fuente=None):
    return ResolucionIdentidad(apellido_csv=apellido, nombre_csv=nombre, estado=estado,
                               empleado_id=empleado_id, fuente=fuente)


# ── Preview ───────────────────────────────────────────────────────────────────

def test_preview_tres_estados_y_resumen():
    desglose = _desglose([
        _fila("GODOY", "SOL", AUTOGESTION="8"),
        _fila("BUSTAMANTE", "DARIO", AUTOGESTION="7", EMPATIA="6"),
        _fila("LERZO", "JUAN", AUTOGESTION="9"),
    ])
    resolutor = _FakeResolutor({
        ("GODOY", "SOL"): _res("GODOY", "SOL", "resuelto", empleado_id=uuid4(), fuente="nombre+superior"),
        ("BUSTAMANTE", "DARIO"): _res("BUSTAMANTE", "DARIO", "ambiguo"),
        ("LERZO", "JUAN"): _res("LERZO", "JUAN", "sin_candidato"),
    })
    orch = EvaluacionImportOrchestrator(resolutor=resolutor, repo=_FakeRepo(), matcheo_repo=_FakeMatcheo())
    r = orch.preview(EMPRESA, "Ciclo 2026", _desglose([]), desglose)
    assert r.resumen.evaluados == 3 and r.resumen.resueltos == 1
    assert r.resumen.ambiguos == 1 and r.resumen.sin_candidato == 1 and r.resumen.resultados == 4
    assert r.periodo_existe is False and r.registros_a_pisar == 0


def test_preview_avisa_periodo_existente():
    prior = LoteResponse(id=uuid4(), empresa_id=EMPRESA, periodo="Ciclo 2026",
                         importado_por=None, created_at=datetime.now(timezone.utc))
    desglose = _desglose([_fila("GODOY", "SOL", AUTOGESTION="8")])
    resolutor = _FakeResolutor({("GODOY", "SOL"): _res("GODOY", "SOL", "sin_candidato")})
    orch = EvaluacionImportOrchestrator(resolutor=resolutor, repo=_FakeRepo(prior=prior, evaluados_prior=7),
                                        matcheo_repo=_FakeMatcheo())
    r = orch.preview(EMPRESA, "Ciclo 2026", _desglose([]), desglose)
    assert r.periodo_existe is True and r.registros_a_pisar == 7


# ── Confirmar ─────────────────────────────────────────────────────────────────

def _confirm(empleado_id, apellido="GODOY", nombre="SOL", guardar_equiv=False, n_res=2) -> EvaluadoConfirm:
    resultados = [ResultadoConfirm(tipo_evaluador="AUTOEVALUACION", competencia=f"C{i}", orden=i, nota=8.0)
                  for i in range(1, n_res + 1)]
    return EvaluadoConfirm(apellido_evaluado=apellido, nombre_evaluado=nombre, perfil="general",
                           empleado_id=empleado_id, guardar_equivalencia=guardar_equiv, resultados=resultados)


def test_confirmar_reimporta_pisa_y_audita_una_vez():
    e1, e2 = uuid4(), uuid4()
    prior = LoteResponse(id=uuid4(), empresa_id=EMPRESA, periodo="Ciclo 2026",
                         importado_por=None, created_at=datetime.now(timezone.utc))
    svc, repo, audit = _FakeSvc(), _FakeRepo(prior=prior), _FakeAudit()
    orch = EvaluacionImportOrchestrator(persistencia=svc, repo=repo,
                                        matcheo_repo=_FakeMatcheo([e1, e2]), audit=audit)
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="Ciclo 2026", evaluados=[
        _confirm(e1, "GODOY", "SOL"), _confirm(e2, "AMADO", "ANDREA")])
    r = orch.confirmar(req, usuario_id=str(uuid4()))
    assert r.piso_periodo_anterior is True and repo.borrados == [str(prior.id)]
    assert r.evaluados == 2 and r.resultados == 4
    # el lote nuevo se creó con sufijo temporal y se renombró al período REAL (sin residuo)
    assert svc.lote_creado.periodo == "Ciclo 2026 ::importando::"
    assert repo.renombrados == [(str(svc.lote_creado.id), "Ciclo 2026")]
    assert len(audit.eventos) == 1 and audit.eventos[0]["evento"] == "importacion_evaluaciones"


def test_confirmar_primer_import_sin_prior_ok():
    e1 = uuid4()
    svc, repo = _FakeSvc(), _FakeRepo(prior=None)  # no hay período previo
    orch = EvaluacionImportOrchestrator(persistencia=svc, repo=repo,
                                        matcheo_repo=_FakeMatcheo([e1]), audit=_FakeAudit())
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="Ciclo 2026", evaluados=[_confirm(e1)])
    r = orch.confirmar(req)
    assert r.piso_periodo_anterior is False and repo.borrados == []  # no borró nada
    assert repo.renombrados == [(str(svc.lote_creado.id), "Ciclo 2026")]  # igual renombra al real


def test_confirmar_evaluados_incompletos_no_borra_el_viejo():
    # EL test: si se persisten MENOS evaluados de los esperados, la verificación por conteo lo
    # detecta, se lanza AppError, el lote VIEJO sigue intacto y el temporal huérfano se limpia.
    e1, e2 = uuid4(), uuid4()
    prior = _lote()
    svc, repo, audit = _FakeSvc(drop_evaluados=1), _FakeRepo(prior=prior), _FakeAudit()
    orch = EvaluacionImportOrchestrator(persistencia=svc, repo=repo,
                                        matcheo_repo=_FakeMatcheo([e1, e2]), audit=audit)
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="Ciclo 2026", evaluados=[
        _confirm(e1, "GODOY", "SOL"), _confirm(e2, "AMADO", "ANDREA")])
    with pytest.raises(AppError) as exc:
        orch.confirmar(req)
    assert exc.value.code == "IMPORT_INCOMPLETO" and exc.value.status_code == 500
    assert str(prior.id) not in repo.borrados            # el VIEJO NO se borró
    assert repo.borrados == [str(svc.lote_creado.id)]    # solo se limpió el temporal huérfano
    assert repo.renombrados == [] and audit.eventos == []  # no llegó a renombrar ni auditar


def test_confirmar_resultados_incompletos_no_borra_el_viejo():
    e1 = uuid4()
    prior = _lote()
    svc, repo, audit = _FakeSvc(drop_resultados=1), _FakeRepo(prior=prior), _FakeAudit()
    orch = EvaluacionImportOrchestrator(persistencia=svc, repo=repo,
                                        matcheo_repo=_FakeMatcheo([e1]), audit=audit)
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="Ciclo 2026", evaluados=[_confirm(e1, n_res=3)])
    with pytest.raises(AppError) as exc:
        orch.confirmar(req)
    assert exc.value.code == "IMPORT_INCOMPLETO"
    assert str(prior.id) not in repo.borrados
    assert repo.borrados == [str(svc.lote_creado.id)]    # temporal limpiado
    assert audit.eventos == []


def test_confirmar_guarda_solo_equivalencias_marcadas():
    e1, e2 = uuid4(), uuid4()
    matcheo = _FakeMatcheo([e1, e2])
    orch = EvaluacionImportOrchestrator(persistencia=_FakeSvc(), repo=_FakeRepo(),
                                        matcheo_repo=matcheo, audit=_FakeAudit())
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="C", evaluados=[
        _confirm(e1, "GODOY", "SOL", guardar_equiv=True),
        _confirm(e2, "AMADO", "ANDREA", guardar_equiv=False)])
    r = orch.confirmar(req)
    assert r.equivalencias == 1 and len(matcheo.equivalencias) == 1
    assert matcheo.equivalencias[0]["apellido_csv"] == "godoy"  # normalizado


def test_confirmar_sin_candidato_persiste_con_null():
    orch = EvaluacionImportOrchestrator(persistencia=_FakeSvc(), repo=_FakeRepo(),
                                        matcheo_repo=_FakeMatcheo(), audit=_FakeAudit())
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="C",
                           evaluados=[_confirm(None, "LERZO", "JUAN", n_res=3)])
    r = orch.confirmar(req)
    assert r.evaluados == 1 and r.resultados == 3 and r.equivalencias == 0


def test_confirmar_rechaza_empleado_de_otra_empresa():
    ajeno = uuid4()  # no está en la empresa del lote
    orch = EvaluacionImportOrchestrator(persistencia=_FakeSvc(), repo=_FakeRepo(),
                                        matcheo_repo=_FakeMatcheo([uuid4()]), audit=_FakeAudit())
    req = ConfirmarRequest(empresa_id=EMPRESA, periodo="C", evaluados=[_confirm(ajeno)])
    with pytest.raises(AppError) as exc:
        orch.confirmar(req)
    assert exc.value.code == "EMPLEADO_FUERA_DE_EMPRESA"


# ── Baja de un lote (EvaluacionService.delete_lote) ───────────────────────────

def _lote(empresa_id=None, periodo="Ciclo 2026") -> LoteResponse:
    return LoteResponse(id=uuid4(), empresa_id=empresa_id or EMPRESA, periodo=periodo,
                        importado_por=None, created_at=datetime.now(timezone.utc))


def test_delete_lote_borra_y_audita_con_snapshot():
    lote, usuario = _lote(), str(uuid4())
    repo, audit = _FakeRepo(prior=lote, evaluados_prior=10), _FakeAudit()
    EvaluacionService(repo=repo, audit=audit).delete_lote(lote.id, usuario)
    assert repo.borrados == [str(lote.id)]
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert ev["evento"] == "baja_lote_evaluaciones" and ev["accion"] == "DELETE"
    assert ev["entidad"] == "evaluacion" and ev["registro_id"] == str(lote.id)
    assert ev["empresa_id"] == str(EMPRESA) and ev["usuario_id"] == usuario
    # El snapshot se toma ANTES del CASCADE: después no se puede reconstruir.
    assert ev["datos_anteriores"] == {"periodo": "Ciclo 2026", "evaluados": 10}
    assert ev["datos_nuevos"] is None


def test_delete_lote_de_otra_empresa_ahora_borra():
    # Desacople: el borrado ya NO depende de la empresa activa. Un lote de cualquier empresa
    # se borra igual (el gate WRITE del router es lo único que protege). La auditoría usa la
    # empresa del propio lote, no la del header.
    ajeno = _lote(empresa_id=uuid4())
    repo, audit = _FakeRepo(prior=ajeno, evaluados_prior=4), _FakeAudit()
    EvaluacionService(repo=repo, audit=audit).delete_lote(ajeno.id)
    assert repo.borrados == [str(ajeno.id)]
    assert len(audit.eventos) == 1
    assert audit.eventos[0]["empresa_id"] == str(ajeno.empresa_id)


def test_delete_lote_inexistente_es_404():
    repo, audit = _FakeRepo(), _FakeAudit()
    with pytest.raises(AppError) as exc:
        EvaluacionService(repo=repo, audit=audit).delete_lote(uuid4())
    assert exc.value.code == "LOTE_NOT_FOUND" and exc.value.status_code == 404
    assert repo.borrados == [] and audit.eventos == []


def test_delete_lote_falla_si_el_repo_no_borro():
    lote = _lote()
    repo, audit = _FakeRepo(prior=lote, evaluados_prior=3, delete_ok=False), _FakeAudit()
    with pytest.raises(AppError) as exc:
        EvaluacionService(repo=repo, audit=audit).delete_lote(lote.id)
    assert exc.value.code == "DB_ERROR" and exc.value.status_code == 500
    assert audit.eventos == []  # no se audita un borrado que no ocurrió


def test_delete_lotes_bulk_clasifica_valido_e_inexistente():
    lote, inexistente = _lote(), uuid4()
    repo, audit = _FakeRepo(prior=lote, evaluados_prior=5), _FakeAudit()
    r = EvaluacionService(repo=repo, audit=audit).delete_lotes_bulk([lote.id, inexistente])
    assert r.eliminados == [lote.id]
    assert len(r.fallidos) == 1
    assert r.fallidos[0].id == inexistente and r.fallidos[0].motivo == "Importación no encontrada"
    assert repo.borrados == [str(lote.id)]          # solo el válido se borró
    assert len(audit.eventos) == 1                  # un evento por baja efectiva, no agregado
    assert audit.eventos[0]["registro_id"] == str(lote.id)
