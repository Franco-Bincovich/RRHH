"""
Auditoría del cambio de logo de empresa (`EmpresaService.upload_logo`).

POR QUÉ EXISTE. `set_logo_url` escribía en `empresas` sin emitir un solo evento, en un módulo
que SÍ audita el alta, la edición y el toggle de activa. No era criterio: era olvido — un cambio
de logo era invisible en /auditoria mientras los tres hermanos aparecían.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · `_FakeRepo.find_by_id` devuelve una empresa cuyo `.id` NO coincide con el id que recibe la
    función. Es artificial a propósito y es LO QUE HACE FALSABLE el test de la empresa del
    evento: en producción los dos valores son iguales, así que un payload que usara el argumento
    del router en vez de `row.id` pasaría inadvertido. Con el fake divergente, "sale de la
    entidad" y "sale del parámetro" dan resultados distintos.
    (Acá no hay `X-Empresa-Id` del que confundirse: `upload_logo` no recibe header. La entidad
    ES la empresa. Se verifica igual, porque el payload podría tomar el valor equivocado.)

  · `_FakeRepo` devuelve un logo ANTERIOR distinto del nuevo, y `set_logo_url` construye su
    respuesta A PARTIR de la url que recibe —nunca una constante prefabricada—. Sin esas dos
    cosas, un payload que informara el mismo valor en `datos_anteriores` y `datos_nuevos` (o que
    los cruzara) seguiría en verde: no habría nada que los distinguiera.

  · `_FakeAudit` acumula en una lista en vez de contar: así el test puede afirmar que hay UN
    evento y no "al menos uno".
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

import pytest

import services.empresa_service as emp_mod
from schemas.empresa import EmpresaResponse
from services.empresa_service import EmpresaService

AHORA = datetime.now(timezone.utc)

# El id REAL de la entidad. Distinto del que se le pasa a upload_logo (ver docstring).
EMPRESA_REAL = "11111111-1111-1111-1111-111111111111"
ID_DEL_ROUTER = "99999999-9999-9999-9999-999999999999"

LOGO_VIEJO = "https://cdn/avatars/logos/viejo.png"


def _empresa(logo: str | None) -> EmpresaResponse:
    return EmpresaResponse(id=EMPRESA_REAL, nombre="DOSUBA", activa=True,
                           logo_url=logo, created_at=AHORA)


class _FakeAudit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


class _FakeRepo:
    """La lectura trae el logo VIEJO; la escritura devuelve lo que se le pidió escribir."""

    def __init__(self) -> None:
        self.escrito: str | None = None

    def find_by_id(self, id: str):
        return _empresa(LOGO_VIEJO)

    def set_logo_url(self, id: str, logo_url: str):
        self.escrito = logo_url
        return _empresa(logo_url)          # construida A PARTIR de lo recibido


class _FakeStorage:
    """Reemplaza supabase_admin.storage: acepta el upload y devuelve una URL pública fija."""

    NUEVA_URL = "https://cdn/avatars/logos/nuevo.png"

    def from_(self, bucket):
        return self

    def upload(self, path, file, file_options):
        return None

    def get_public_url(self, path):
        return self.NUEVA_URL


@pytest.fixture
def storage(monkeypatch):
    fake = _FakeStorage()
    monkeypatch.setattr(emp_mod.supabase_admin, "storage", fake, raising=False)
    return fake


def _subir(repo, audit):
    svc = EmpresaService(repo=repo, audit=audit)
    return svc.upload_logo(ID_DEL_ROUTER, b"\x89PNG imagen", "logo.png", "image/png", "user-7")


def test_upload_logo_emite_un_evento(storage):
    repo, audit = _FakeRepo(), _FakeAudit()
    _subir(repo, audit)
    assert len(audit.eventos) == 1
    ev = audit.eventos[0]
    assert ev["evento"] == "cambio_logo_empresa"
    assert ev["accion"] == "UPDATE"
    assert ev["entidad"] == "empresa"
    assert ev["usuario_id"] == "user-7"


def test_el_evento_lleva_la_empresa_de_la_entidad(storage):
    """La empresa del evento sale del REGISTRO devuelto por el repo, no del id que llegó del
    router. Para que falle: que el payload use el argumento en vez de `row.id`."""
    repo, audit = _FakeRepo(), _FakeAudit()
    _subir(repo, audit)
    ev = audit.eventos[0]
    assert ev["empresa_id"] == EMPRESA_REAL
    assert ev["registro_id"] == EMPRESA_REAL
    assert ev["empresa_id"] != ID_DEL_ROUTER


def test_el_evento_lleva_el_logo_anterior_y_el_nuevo(storage):
    """Un evento que solo dice "cambió el logo" no sirve para auditar: hay que poder reconstruir
    qué se reemplazó. Para que falle: que el payload informe el mismo valor en los dos lados."""
    repo, audit = _FakeRepo(), _FakeAudit()
    _subir(repo, audit)
    ev = audit.eventos[0]
    assert ev["datos_anteriores"] == {"logo_url": LOGO_VIEJO}
    assert ev["datos_nuevos"] == {"logo_url": _FakeStorage.NUEVA_URL}
    assert ev["datos_anteriores"]["logo_url"] != ev["datos_nuevos"]["logo_url"]


def test_el_logo_nuevo_es_el_que_se_persistio(storage):
    """Cierra el lazo con la capa de abajo: el valor auditado es el MISMO que se mandó a escribir,
    no uno recalculado en el payload."""
    repo, audit = _FakeRepo(), _FakeAudit()
    resultado = _subir(repo, audit)
    assert repo.escrito == _FakeStorage.NUEVA_URL
    assert resultado.logo_url == _FakeStorage.NUEVA_URL
    assert audit.eventos[0]["datos_nuevos"]["logo_url"] == repo.escrito


def test_empresa_inexistente_no_audita(storage):
    """El 404 corta ANTES de subir a Storage y antes de auditar: no puede quedar un evento de un
    cambio que no ocurrió."""
    from utils.errors import AppError

    class _Vacio(_FakeRepo):
        def find_by_id(self, id: str):
            return None

    repo, audit = _Vacio(), _FakeAudit()
    with pytest.raises(AppError) as exc:
        _subir(repo, audit)
    assert exc.value.code == "EMPRESA_NOT_FOUND"
    assert audit.eventos == []
