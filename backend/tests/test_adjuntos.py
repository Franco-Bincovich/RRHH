"""
Tests del service de adjuntos genéricos (B4.1).

Repo fake + AuditService fake inyectados; el cliente de Storage se monkeypatchea (sin red).
Foco: subir valida tipo/tamaño y gatea por sección · listar filtra por entidad y gatea ·
delete es SOFT (marcar_eliminado, no borra Storage) + audita · gating por rol/entidad.
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

from datetime import datetime
from uuid import uuid4

import pytest

import services.adjunto_service as adj_mod
from schemas.adjunto import Adjunto
from services.adjunto_service import AdjuntoService
from utils.errors import AppError

_PDF = "application/pdf"
_EID = uuid4()


def _adjunto(**over) -> Adjunto:
    base = dict(
        id="adj1", entidad="empleado", entidad_id=str(_EID), empresa_id="e1",
        bucket="documentos", storage_path="adjuntos/empleado/x/f.pdf", nombre_archivo="cv.pdf",
        mime_type=_PDF, tamano_bytes=10, categoria="cv", descripcion=None, estado="activo",
        subido_por="u1", created_at=datetime(2026, 1, 1, 9, 0),
    )
    base.update(over)
    return Adjunto(**base)


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeRepo:
    def __init__(self) -> None:
        self.creado: dict | None = None
        self.eliminado: str | None = None
        self.rows = [_adjunto()]

    def crear(self, datos: dict) -> Adjunto:
        self.creado = datos
        return _adjunto(**{k: datos[k] for k in ("entidad", "entidad_id") if k in datos})

    def find_by_entidad(self, entidad, entidad_id, empresa_id=None):
        return [r for r in self.rows if r.entidad == entidad and r.entidad_id == entidad_id]

    def find_by_id(self, id):
        return next((r for r in self.rows if r.id == id), None)

    def marcar_eliminado(self, id) -> None:
        self.eliminado = id


class _FakeStorage:
    """Reemplaza supabase_admin.storage: registra upload y sirve una signed URL fija."""

    def __init__(self) -> None:
        self.uploaded: dict | None = None

    def from_(self, bucket):
        self._bucket = bucket
        return self

    def upload(self, path, file, file_options):
        self.uploaded = {"path": path, "size": len(file)}

    def create_signed_url(self, path, expires_in):
        return {"signedURL": f"https://signed/{path}?e={expires_in}"}


@pytest.fixture
def storage(monkeypatch):
    fake = _FakeStorage()
    monkeypatch.setattr(adj_mod.supabase_admin, "storage", fake, raising=False)
    return fake


# Resolvers de padre permisivos: estos tests cubren gating/upload/soft-delete, no la barrera de
# empresa del padre (esa vive en test_adjuntos_padre_empresa.py, con dobles que sí la honran).
_PADRES_OK = {e: (lambda _eid, _emp: {"empresa_id": "e1"})
              for e in ("empleado", "vacacion", "ausencia", "vacante", "offboarding")}


def _svc(repo=None, audit=None, padres=None) -> AdjuntoService:
    return AdjuntoService(repo=repo or _FakeRepo(), audit=audit or _FakeAudit(),
                          padre_resolvers=padres or _PADRES_OK)


def test_subir_persiste_y_audita_alta(storage):
    repo, audit = _FakeRepo(), _FakeAudit()
    svc = _svc(repo, audit)
    adj = svc.subir("empleado", _EID, None, b"data", "cv.pdf", _PDF, "cv", None, "admin_rrhh", "u1")
    assert adj.entidad == "empleado"
    assert storage.uploaded is not None and storage.uploaded["path"].startswith("adjuntos/empleado/")
    assert repo.creado["storage_path"] == storage.uploaded["path"]
    assert [c["evento"] for c in audit.calls] == ["alta_adjunto"]


def test_subir_rechaza_tipo_invalido(storage):
    with pytest.raises(AppError) as e:
        _svc().subir("empleado", _EID, None, b"data", "x.exe", "application/x-msdownload", None, None, "admin_rrhh", "u1")
    assert e.value.code == "INVALID_FILE_TYPE"
    assert storage.uploaded is None  # no sube si la validación falla


def test_subir_rechaza_tamano(storage):
    grande = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(AppError) as e:
        _svc().subir("empleado", _EID, None, grande, "big.pdf", _PDF, None, None, "admin_rrhh", "u1")
    assert e.value.code == "FILE_TOO_LARGE"


def test_gating_por_entidad_deniega(storage):
    # mandos_medios NO puede escribir en EMPLEADOS (solo vacaciones/ausencias).
    with pytest.raises(AppError) as e:
        _svc().subir("empleado", _EID, None, b"d", "cv.pdf", _PDF, None, None, "mandos_medios", "u1")
    assert e.value.code == "FORBIDDEN"


def test_gating_por_entidad_permite_mando_en_vacacion(storage):
    repo = _FakeRepo()
    _svc(repo).subir("vacacion", _EID, None, b"d", "j.pdf", _PDF, None, None, "mandos_medios", "u1")
    assert repo.creado["entidad"] == "vacacion"


def test_entidad_no_soportada(storage):
    with pytest.raises(AppError) as e:
        _svc().listar("planeta", _EID, None, "admin_rrhh")
    assert e.value.code == "ENTIDAD_INVALIDA"


def test_listar_filtra_por_entidad(storage):
    items = _svc().listar("empleado", _EID, None, "admin_rrhh")
    assert len(items) == 1 and items[0].entidad == "empleado"


def test_listar_entidad_sin_adjuntos_vacio(storage):
    assert _svc().listar("empleado", uuid4(), None, "gerencia_lectura") == []


def test_eliminar_es_soft_y_audita(storage):
    repo, audit = _FakeRepo(), _FakeAudit()
    _svc(repo, audit).eliminar("adj1", None, "admin_rrhh", "u1")
    assert repo.eliminado == "adj1"  # soft delete
    assert [c["evento"] for c in audit.calls] == ["baja_adjunto"]


def test_url_descarga_firma(storage):
    url = _svc().url_descarga("adj1", None, "admin_rrhh")
    assert url.startswith("https://signed/adjuntos/empleado/x/f.pdf")


def test_get_owned_404_otra_empresa(storage):
    from uuid import UUID
    with pytest.raises(AppError) as e:
        _svc().url_descarga("adj1", UUID("00000000-0000-0000-0000-000000000999"), "admin_rrhh")
    assert e.value.code == "ADJUNTO_NOT_FOUND"
