"""
Auditoría del marcado de adjunto principal (`AdjuntoService.marcar_principal`).

POR QUÉ EXISTE. El módulo auditaba `subir` y `eliminar`, y no el cambio de principal — que es la
operación que decide QUÉ documento representa a la entidad (la foto de un empleado, el PDF de una
vacante). Cambiarlo no dejaba rastro mientras el alta y la baja sí.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · **La llamada pasa `empresa_id=None`** (consolidado) y el fake devuelve el adjunto con
    `empresa_id=EMPRESA_ENTIDAD`. Si el payload tomara el header, el evento saldría con None.
    Con los dos iguales, "sale de la entidad" y "sale del header" serían indistinguibles.

  · **El adjunto previo tiene `es_principal=False` y se lo marca en True.** Sin esa divergencia,
    un payload que informara el mismo valor en `datos_anteriores` y `datos_nuevos` —o que los
    cruzara— pasaría igual.

  · **`set_principal` y `desmarcar_principales` devuelven None**, como el repo real: la empresa y
    el valor anterior tienen que salir del adjunto leído ANTES, no de un retorno inexistente.

  · **`_FakeAudit` acumula en lista**: permite afirmar UN evento, no "al menos uno".

  · El fake registra qué se le mandó escribir, así el test compara el valor auditado contra el
    persistido y no contra su propia constante.
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

from schemas.adjunto import Adjunto
from services.adjunto_service import AdjuntoService

AHORA = datetime.now(timezone.utc)
EMPRESA_ENTIDAD = "11111111-1111-1111-1111-111111111111"
ADJ_ID, EMPLEADO_ID = str(uuid4()), str(uuid4())


def _adj(principal: bool) -> Adjunto:
    return Adjunto(id=ADJ_ID, entidad="empleado", entidad_id=EMPLEADO_ID,
                   empresa_id=EMPRESA_ENTIDAD, bucket="documentos",
                   storage_path="adjuntos/empleado/x/f.pdf", nombre_archivo="foto.png",
                   estado="activo", es_principal=principal, created_at=AHORA)


class _FakeAudit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


class _FakeRepo:
    """El adjunto guardado arranca en es_principal=False; las escrituras devuelven None."""

    def __init__(self) -> None:
        self.escrito = None
        self.desmarcados = None

    def find_by_id(self, id):
        return _adj(False)                       # estado PREVIO

    def desmarcar_principales(self, entidad, entidad_id):
        self.desmarcados = (entidad, entidad_id)
        return None

    def set_principal(self, id, valor):
        self.escrito = (id, valor)
        return None


def _marcar(audit, repo, principal=True):
    svc = AdjuntoService(repo=repo, audit=audit)
    return svc.marcar_principal(ADJ_ID, principal, None, "admin_rrhh", "user-9")


def test_marcar_principal_emite_un_evento():
    audit, repo = _FakeAudit(), _FakeRepo()
    _marcar(audit, repo)
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert (ev["evento"], ev["accion"]) == ("cambio_principal_adjunto", "UPDATE")
    assert ev["usuario_id"] == "user-9"


def test_el_evento_lleva_la_empresa_de_la_entidad_no_del_header():
    """La llamada pasa empresa_id=None: si el payload lo tomara de ahí, el evento saldría sin
    empresa y quedaría fuera del filtro por empresa de /auditoria."""
    audit, repo = _FakeAudit(), _FakeRepo()
    _marcar(audit, repo)
    assert audit.eventos[0]["empresa_id"] == EMPRESA_ENTIDAD


def test_el_evento_se_registra_bajo_la_entidad_padre():
    """Mismo criterio que alta_adjunto y baja_adjunto: el historial del empleado tiene que
    mostrarlo, no un registro 'adjunto' suelto que nadie mira."""
    audit, repo = _FakeAudit(), _FakeRepo()
    _marcar(audit, repo)
    ev = audit.eventos[0]
    assert ev["entidad"] == "empleado"
    assert ev["registro_id"] == EMPLEADO_ID


def test_el_evento_lleva_el_valor_anterior_y_el_nuevo():
    """Para que falle: que el fake devuelva es_principal=True en find_by_id — ahí anterior y nuevo
    coincidirían y un payload que los confunda sería indistinguible de uno correcto."""
    audit, repo = _FakeAudit(), _FakeRepo()
    _marcar(audit, repo, principal=True)
    ev = audit.eventos[0]
    assert ev["datos_anteriores"] == {"adjunto_id": ADJ_ID, "es_principal": False}
    assert ev["datos_nuevos"] == {"adjunto_id": ADJ_ID, "es_principal": True}
    assert ev["datos_anteriores"]["es_principal"] != ev["datos_nuevos"]["es_principal"]


def test_el_valor_auditado_es_el_que_se_persistio():
    """Cierra el lazo con la escritura: el evento informa lo que se mandó a guardar, no un valor
    recalculado en el payload."""
    audit, repo = _FakeAudit(), _FakeRepo()
    _marcar(audit, repo, principal=True)
    assert repo.escrito == (ADJ_ID, True)
    assert audit.eventos[0]["datos_nuevos"]["es_principal"] == repo.escrito[1]


def test_desmarcar_tambien_audita_y_no_toca_a_los_hermanos():
    """Desmarcar es un cambio auditable igual que marcar, y NO dispara el desmarcado masivo."""
    audit, repo = _FakeAudit(), _FakeRepo()
    _marcar(audit, repo, principal=False)
    assert len(audit.eventos) == 1
    assert audit.eventos[0]["datos_nuevos"]["es_principal"] is False
    assert repo.desmarcados is None
