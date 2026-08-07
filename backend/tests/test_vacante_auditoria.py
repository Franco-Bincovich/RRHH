"""
Auditoría del módulo de vacantes y candidatos: alta y edición de vacante, alta de candidato,
adjuntar CV y cambio de etapa.

POR QUÉ EXISTE. El módulo auditaba la BAJA de vacante y la BAJA de candidato, y nada más. No era
criterio: era olvido — crear una búsqueda, editarla, sumar un postulante y moverlo por el pipeline
no dejaba una sola fila en /auditoria, mientras los dos borrados sí aparecían.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · **La empresa de la entidad ≠ la del header.** Todas las llamadas pasan `empresa_id=None`
    (modo consolidado, que es el caso real en el que el bug se manifiesta) y los fakes devuelven
    entidades con `empresa_id=EMPRESA_ENTIDAD`. Si el payload tomara el header, el evento saldría
    con None y el assert cae. Con los dos valores iguales el test no podría desmentir nada.

  · **`update_etapa_candidato` devuelve una etapa DISTINTA de la que devuelve `find_by_id`.** Sin
    esa divergencia, un payload que informara la misma etapa en `datos_anteriores` y
    `datos_nuevos` —o que las cruzara— seguiría en verde.

  · **Los fakes de escritura construyen la respuesta A PARTIR de lo que reciben** (el candidato
    sale con la empresa que se le pasó, la vacante con los campos del update). Un objeto
    prefabricado haría que el test afirme algo sobre su propia constante.
    🔴 ÚNICA EXCEPCIÓN DECLARADA: `_FakeVacanteRepo.save` devuelve `empresa_id=EMPRESA_ENTIDAD`
    aunque el body traiga otro valor. Es artificial a propósito y es lo que hace falsable el
    único caso donde no hay header: en el alta, la empresa viaja en el body, así que "sale de la
    fila persistida" y "sale del request" solo se distinguen si difieren.

  · **`_FakeAudit` acumula en una lista**, no cuenta: así se afirma UN evento y no "al menos uno".

  · **`set_cv` devuelve None**, igual que el repo real. Es lo que obliga a que la empresa del
    evento salga del candidato ya en mano y no de un valor de retorno que no existe.

🔴 Y UN TEST QUE NO USA FAKES (`TestElMapperDeCandidato`). Los cuatro eventos de candidato sacan
la empresa de `CandidatoResponse.empresa_id`, que la pone el mapper `_crow` del repo. Si ese
mapper la descartara —que es exactamente lo que pasó y se arregló para `baja_candidato`— todos
los tests de arriba seguirían verdes con fakes, y en producción cada evento saldría con empresa
None. Por eso se ejercita el mapper REAL contra una fila cruda.
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
from uuid import UUID, uuid4

import pytest

from repositories.candidato_repo import _crow
from schemas.vacante import CandidatoCreate, CandidatoResponse, VacanteCreate, VacanteResponse, VacanteUpdate
from services.vacante_service import VacanteService

AHORA = datetime.now(timezone.utc)
EMPRESA_ENTIDAD = "11111111-1111-1111-1111-111111111111"
EMPRESA_DEL_BODY = "22222222-2222-2222-2222-222222222222"
VACANTE_ID, CANDIDATO_ID, AREA_ID = str(uuid4()), str(uuid4()), str(uuid4())


def _vacante(**kw) -> VacanteResponse:
    base = dict(id=VACANTE_ID, empresa_id=EMPRESA_ENTIDAD, titulo="Analista", area_id=AREA_ID,
                estado="nueva", created_at=AHORA)
    base.update(kw)
    return VacanteResponse(**base)


def _candidato(etapa: str = "postulado", empresa: str = EMPRESA_ENTIDAD) -> CandidatoResponse:
    return CandidatoResponse(id=CANDIDATO_ID, vacante_id=VACANTE_ID, empresa_id=empresa,
                             nombre="Sol", apellido="Godoy", email="sol@x.com",
                             etapa_pipeline=etapa, created_at=AHORA)


class _FakeAudit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


class _FakeVacanteRepo:
    def find_by_id(self, id, empresa_id=None):
        return _vacante(titulo="Analista", estado="nueva")

    def save(self, data):
        # Ver la EXCEPCIÓN DECLARADA del encabezado: empresa_id NO sale del body a propósito.
        return _vacante(titulo=data.titulo, area_id=str(data.area_id))

    def update(self, id, data, empresa_id=None):
        patch = data.model_dump(exclude_none=True)
        return _vacante(**{k: str(v) if k == "area_id" else v for k, v in patch.items()})


class _FakeCandidatoRepo:
    def __init__(self, etapa_nueva: str = "entrevista_rrhh") -> None:
        self.cv_guardado = None
        self._etapa_nueva = etapa_nueva

    def save_candidato(self, vacante_id, data, empresa_id):
        return _candidato(empresa=empresa_id)          # construido con lo recibido

    def set_cv(self, candidato_id, path):
        self.cv_guardado = path
        return None                                     # igual que el repo real

    def find_by_id(self, candidato_id, empresa_id=None):
        return _candidato(etapa="postulado")            # etapa ANTERIOR

    def update_etapa_candidato(self, candidato_id, etapa, empresa_id=None):
        return _candidato(etapa=etapa)                  # etapa NUEVA, distinta de la anterior


class _FakeCv:
    def validar(self, *a, **kw):
        return None

    def subir(self, *a, **kw):
        return "cvs/empresa/cand.pdf"


def _svc(audit, cand_repo=None):
    return VacanteService(repo=_FakeVacanteRepo(), candidato_repo=cand_repo or _FakeCandidatoRepo(),
                          cv_service=_FakeCv(), adjunto_service=object(), audit=audit)


# ── Vacante ───────────────────────────────────────────────────────────────────

def test_alta_de_vacante_emite_un_evento_con_la_empresa_de_la_fila():
    """La empresa sale de la fila PERSISTIDA, no del body del request."""
    audit = _FakeAudit()
    _svc(audit).create_vacante(
        VacanteCreate(empresa_id=UUID(EMPRESA_DEL_BODY), titulo="Analista",
                      area_id=UUID(AREA_ID), tipo_contrato="efectivo"), "user-1")
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert (ev["evento"], ev["accion"], ev["entidad"]) == ("alta_vacante", "INSERT", "vacante")
    assert ev["empresa_id"] == EMPRESA_ENTIDAD
    assert ev["empresa_id"] != EMPRESA_DEL_BODY
    assert ev["usuario_id"] == "user-1"


def test_edicion_de_vacante_lleva_anterior_y_nuevo_y_la_empresa_de_la_entidad():
    """empresa_id=None (consolidado) en la llamada: si el evento lo tomara del header, saldría None."""
    audit = _FakeAudit()
    _svc(audit).update_vacante(UUID(VACANTE_ID), VacanteUpdate(titulo="Analista Sr"),
                               None, "user-2")
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert (ev["evento"], ev["accion"]) == ("edicion_vacante", "UPDATE")
    assert ev["empresa_id"] == EMPRESA_ENTIDAD
    assert ev["datos_anteriores"] == {"titulo": "Analista"}
    assert ev["datos_nuevos"] == {"titulo": "Analista Sr"}


def test_la_edicion_solo_registra_los_campos_tocados():
    """Un diff que volcara la fila entera haría ilegible el historial y registraría como cambio
    lo que no cambió."""
    audit = _FakeAudit()
    _svc(audit).update_vacante(UUID(VACANTE_ID), VacanteUpdate(estado="en_proceso"), None, "u")
    assert set(audit.eventos[0]["datos_nuevos"]) == {"estado"}


# ── Candidatos ────────────────────────────────────────────────────────────────

def test_alta_de_candidato_emite_evento_con_la_empresa_heredada_de_la_vacante():
    audit = _FakeAudit()
    _svc(audit).add_candidato(UUID(VACANTE_ID), CandidatoCreate(nombre="Sol", apellido="Godoy",
                                                                email="sol@x.com"),
                              None, None, None, None, "user-3")
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert (ev["evento"], ev["accion"], ev["entidad"]) == ("alta_candidato", "INSERT", "candidato")
    assert ev["empresa_id"] == EMPRESA_ENTIDAD
    assert ev["registro_id"] == CANDIDATO_ID


def test_adjuntar_cv_emite_su_propio_evento_pese_a_que_set_cv_no_devuelve_nada():
    """`set_cv` devuelve None: la empresa del evento sale del candidato ya en mano. Son DOS
    eventos porque son dos mutaciones que fallan por separado."""
    audit, repo = _FakeAudit(), _FakeCandidatoRepo()
    _svc(audit, repo).add_candidato(UUID(VACANTE_ID), CandidatoCreate(nombre="Sol", apellido="Godoy",
                                                                      email="sol@x.com"),
                                    None, b"%PDF-1.4", "cv.pdf", "application/pdf", "user-4")
    assert [e["evento"] for e in audit.eventos] == ["alta_candidato", "adjuntar_cv_candidato"]
    cv_ev = audit.eventos[1]
    assert cv_ev["empresa_id"] == EMPRESA_ENTIDAD
    assert cv_ev["datos_nuevos"] == {"cv_storage_path": repo.cv_guardado}


def test_cambio_de_etapa_lleva_la_etapa_anterior_y_la_nueva():
    """Para que falle: que el fake devuelva la misma etapa en find_by_id y en el update — ahí un
    payload que las confunda sería indistinguible de uno correcto."""
    audit = _FakeAudit()
    _svc(audit).mover_candidato(UUID(CANDIDATO_ID), "entrevista_rrhh", None, "user-5")
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert ev["evento"] == "cambio_etapa_candidato"
    assert ev["empresa_id"] == EMPRESA_ENTIDAD
    assert ev["datos_anteriores"] == {"etapa_pipeline": "postulado"}
    assert ev["datos_nuevos"] == {"etapa_pipeline": "entrevista_rrhh"}
    assert ev["datos_anteriores"] != ev["datos_nuevos"]


def test_etapa_invalida_no_audita():
    audit = _FakeAudit()
    from utils.errors import AppError
    with pytest.raises(AppError) as exc:
        _svc(audit).mover_candidato(UUID(CANDIDATO_ID), "inventada", None, "u")
    assert exc.value.code == "ETAPA_INVALIDA"
    assert audit.eventos == []


# ── La capa de abajo, sin fakes ───────────────────────────────────────────────

class TestElMapperDeCandidato:
    """🔴 Los cuatro eventos de candidato sacan la empresa de `CandidatoResponse.empresa_id`, que
    la puebla `_crow`. Con fakes, un mapper que la descarte es INVISIBLE. Acá se ejercita el real."""

    def _fila(self) -> dict:
        return {"id": CANDIDATO_ID, "vacante_id": VACANTE_ID, "empresa_id": EMPRESA_ENTIDAD,
                "nombre": "Sol", "apellido": "Godoy", "email": "sol@x.com",
                "etapa": "entrevista_rrhh", "created_at": AHORA}

    def test_crow_conserva_la_empresa(self) -> None:
        """Para que falle: sacarle la línea `empresa_id=...` a `_crow`, que es justo el bug que
        dejó los eventos de baja de candidato sin empresa."""
        assert _crow(self._fila()).empresa_id == EMPRESA_ENTIDAD

    def test_crow_mapea_etapa_a_etapa_pipeline(self) -> None:
        """La columna se llama `etapa` y el schema `etapa_pipeline`. El evento de cambio de etapa
        lee el segundo: si el mapeo se rompe, el payload informaría siempre 'postulado'."""
        assert _crow(self._fila()).etapa_pipeline == "entrevista_rrhh"
