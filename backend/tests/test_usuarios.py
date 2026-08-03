"""
Tests del alta de usuarios mandos_medios (UsuarioService).

Repo fake + AuditService fake; auth.admin (Supabase) monkeypatcheado (sin red). Foco:
fuerza rol='mandos_medios' + must_change_password; password temporal random y fuera del
audit; unicidad email/username antes de tocar Auth; ROLLBACK del auth user si el perfil
o el vínculo al empleado fallan.
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
from pydantic import ValidationError

import services.usuario_service as usuario_service
from schemas.usuario import CrearUsuarioRequest
from services.usuario_service import UsuarioService
from utils.errors import AppError

_UID = "11111111-1111-1111-1111-111111111111"


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeAuthAdmin:
    def __init__(self, *, update_falla=False) -> None:
        self.creado: dict | None = None
        self.borrado: str | None = None
        self.actualizado: tuple | None = None
        self._update_falla = update_falla

    def create_user(self, attrs):
        self.creado = attrs
        return SimpleNamespace(user=SimpleNamespace(id=_UID))

    # Se CONSERVA aunque la baja ya no borre: es lo que permite afirmar que no se llama.
    # Un fake sin este método haría pasar el test por AttributeError inexistente, no por
    # comportamiento.
    def delete_user(self, uid):
        self.borrado = uid

    def update_user_by_id(self, uid, attrs):
        if self._update_falla:
            raise Exception("gotrue caído")
        self.actualizado = (uid, attrs)


class _FakeRepo:
    def __init__(self, *, email_dup=False, user_dup=False, insert_fail=False, empleado_ok=True) -> None:
        self._email_dup = email_dup
        self._user_dup = user_dup
        self._insert_fail = insert_fail
        self._empleado_ok = empleado_ok
        self.perfil: dict | None = None
        self.vinculado: tuple | None = None

    def email_existe(self, email):
        return self._email_dup

    def username_existe(self, username):
        return self._user_dup

    def insert_perfil(self, payload):
        if self._insert_fail:
            raise AppError("boom", "DB_ERROR", 500)
        self.perfil = payload

    def vincular_empleado(self, empleado_id, user_id):
        self.vinculado = (empleado_id, user_id)
        return self._empleado_ok


@pytest.fixture
def auth(monkeypatch):
    fake = _FakeAuthAdmin()
    monkeypatch.setattr(usuario_service.supabase_admin, "auth", SimpleNamespace(admin=fake), raising=False)
    return fake


def _req(**over) -> CrearUsuarioRequest:
    base = dict(nombre="Ana", apellido="Lopez", email="Ana.Lopez@x.com", username="alopez",
                rol="mandos_medios")
    base.update(over)
    return CrearUsuarioRequest(**base)


def test_crea_usa_rol_del_request_y_flag(auth):
    repo, aud = _FakeRepo(), _FakeAudit()
    out = UsuarioService(repo=repo, audit=aud).crear_usuario(_req(), "admin1")
    assert repo.perfil["rol"] == "mandos_medios"  # el rol del request, no una constante
    assert repo.perfil["must_change_password"] is True
    assert repo.perfil["email"] == "ana.lopez@x.com"  # normalizado a minúsculas
    assert out.id == _UID and out.username == "alopez"
    assert len(out.password_temporal) >= 16
    assert auth.creado["email_confirm"] is True and auth.creado["password"] == out.password_temporal


@pytest.mark.parametrize("rol", ["admin_rrhh", "gerencia_lectura", "mandos_medios"])
def test_crea_con_cada_rol_valido(auth, rol):
    repo, aud = _FakeRepo(), _FakeAudit()
    UsuarioService(repo=repo, audit=aud).crear_usuario(_req(rol=rol), "admin1")
    assert repo.perfil["rol"] == rol                 # se persiste el rol elegido
    assert aud.calls[0]["datos_nuevos"]["rol"] == rol  # y se audita el mismo rol


@pytest.mark.parametrize("rol", ["superadmin", "management", "empleado", "", "ADMIN_RRHH"])
def test_rol_invalido_es_422(rol):
    # La validación vive en el schema (field_validator) → ValidationError, que FastAPI
    # traduce a 422. Un rol fuera de ROLES_VALIDOS nunca llega al service.
    with pytest.raises(ValidationError):
        _req(rol=rol)


def test_rol_ausente_es_422():
    with pytest.raises(ValidationError):
        CrearUsuarioRequest(nombre="Ana", apellido="Lopez", email="a@x.com", username="alopez")


def test_password_no_se_audita(auth):
    repo, aud = _FakeRepo(), _FakeAudit()
    out = UsuarioService(repo=repo, audit=aud).crear_usuario(_req(), "admin1")
    assert [c["evento"] for c in aud.calls] == ["alta_usuario"]
    dump = str(aud.calls[0])
    assert out.password_temporal not in dump  # la contraseña nunca entra al audit


def test_email_duplicado_409_sin_tocar_auth(auth):
    with pytest.raises(AppError) as e:
        UsuarioService(repo=_FakeRepo(email_dup=True), audit=_FakeAudit()).crear_usuario(_req(), "a")
    assert e.value.code == "EMAIL_DUPLICADO" and e.value.status_code == 409
    assert auth.creado is None  # no se creó identidad


def test_username_duplicado_409(auth):
    with pytest.raises(AppError) as e:
        UsuarioService(repo=_FakeRepo(user_dup=True), audit=_FakeAudit()).crear_usuario(_req(), "a")
    assert e.value.code == "USERNAME_DUPLICADO"
    assert auth.creado is None


def test_rollback_si_insert_perfil_falla(auth):
    repo, aud = _FakeRepo(insert_fail=True), _FakeAudit()
    with pytest.raises(AppError):
        UsuarioService(repo=repo, audit=aud).crear_usuario(_req(), "a")
    assert auth.borrado == _UID   # se borró la identidad huérfana
    assert aud.calls == []        # no se auditó un alta que se revirtió


def test_empleado_inexistente_hace_rollback(auth):
    repo = _FakeRepo(empleado_ok=False)
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=_FakeAudit()).crear_usuario(_req(empleado_id=uuid4()), "a")
    assert e.value.code == "EMPLEADO_NOT_FOUND"
    assert auth.borrado == _UID


def test_vincula_empleado_cuando_se_pasa(auth):
    repo = _FakeRepo()
    emp = uuid4()
    UsuarioService(repo=repo, audit=_FakeAudit()).crear_usuario(_req(empleado_id=emp), "a")
    assert repo.vinculado == (str(emp), _UID)


# --- Cambio de contraseña (self-service) ------------------------------------

class _FakePwdRepo:
    def __init__(self, *, email="ana@x.com") -> None:
        self._email = email
        self.flag_bajado: str | None = None

    def get_email(self, user_id):
        return self._email  # None simula usuario inexistente

    def bajar_flag_password(self, user_id):
        self.flag_bajado = user_id


class _FakeAuthClient:
    """Espeja supabase_client.auth: sign_in_with_password según credencial correcta."""
    def __init__(self, *, actual_ok=True) -> None:
        self._actual_ok = actual_ok
        self.actualizado: tuple | None = None

    def sign_in_with_password(self, creds):
        if not self._actual_ok:
            raise Exception("invalid login credentials")
        return SimpleNamespace(session=SimpleNamespace(access_token="t"))


@pytest.fixture
def pwd_env(monkeypatch):
    """Monkeypatchea client (reauth) y admin.update_user_by_id (cambio) sin red."""
    def _apply(*, actual_ok=True, update_ok=True):
        client = _FakeAuthClient(actual_ok=actual_ok)
        updates: dict = {}

        def _update(uid, attrs):
            if not update_ok:
                raise Exception("boom")
            updates["call"] = (uid, attrs)
        admin = SimpleNamespace(update_user_by_id=_update)
        monkeypatch.setattr(usuario_service.supabase_client, "auth",
                            SimpleNamespace(sign_in_with_password=client.sign_in_with_password), raising=False)
        monkeypatch.setattr(usuario_service.supabase_admin, "auth",
                            SimpleNamespace(admin=admin), raising=False)
        return updates
    return _apply


def test_cambio_password_ok_baja_flag_y_audita(pwd_env):
    updates = pwd_env()
    repo, aud = _FakePwdRepo(), _FakeAudit()
    UsuarioService(repo=repo, audit=aud).cambiar_password(_UID, "vieja123", "nueva1234")
    assert updates["call"] == (_UID, {"password": "nueva1234"})  # se cambió la clave
    assert repo.flag_bajado == _UID                              # flag true→false
    assert [c["evento"] for c in aud.calls] == ["cambio_password"]
    assert "nueva1234" not in str(aud.calls) and "vieja123" not in str(aud.calls)  # sin contraseñas


def test_cambio_password_actual_incorrecta_401(pwd_env):
    updates = pwd_env(actual_ok=False)
    repo, aud = _FakePwdRepo(), _FakeAudit()
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=aud).cambiar_password(_UID, "mala", "nueva1234")
    assert e.value.code == "INVALID_CREDENTIALS" and e.value.status_code == 401
    assert "call" not in updates          # no se tocó la credencial
    assert repo.flag_bajado is None       # no se bajó el flag
    assert aud.calls == []                # no se auditó


def test_cambio_password_usuario_inexistente_404(pwd_env):
    pwd_env()
    repo = _FakePwdRepo(email=None)
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=_FakeAudit()).cambiar_password(_UID, "x", "nueva1234")
    assert e.value.code == "USUARIO_NOT_FOUND" and e.value.status_code == 404


def test_cambio_password_falla_update_502_no_baja_flag(pwd_env):
    pwd_env(update_ok=False)
    repo, aud = _FakePwdRepo(), _FakeAudit()
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=aud).cambiar_password(_UID, "vieja123", "nueva1234")
    assert e.value.code == "PASSWORD_UPDATE_ERROR" and e.value.status_code == 502
    assert repo.flag_bajado is None and aud.calls == []


def test_schema_rechaza_nueva_igual_a_actual():
    from schemas.usuario import CambiarPasswordRequest
    with pytest.raises(ValueError):
        CambiarPasswordRequest(password_actual="misma1234", password_nueva="misma1234")


def test_schema_rechaza_nueva_corta():
    from schemas.usuario import CambiarPasswordRequest
    with pytest.raises(ValueError):
        CambiarPasswordRequest(password_actual="vieja123", password_nueva="corta")


# --- Baja de usuarios (admin-only) — BLANDA: ban + activo=false --------------

class _FakeDelRepo:
    """Modela la fila de `users` Y el vínculo `empleados.user_id`, con la semántica REAL de la
    FK de producción (`ON DELETE SET NULL`).

    🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN ESTE FAKE PARA QUE LOS TESTS PUEDAN FALLAR?

    Que borrar la fila NO arrastrara el vínculo. Un fake que solo guardara un booleano `activo`
    haría pasar "conserva el vínculo" incluso con la baja dura puesta, porque no habría vínculo
    que perder: el test estaría afirmando algo sobre un campo que el fake no modela. Acá borrar
    arrastra, igual que la FK, y `borrar_fila` sigue existiendo —aunque el service ya no lo
    llame— para que el camino viejo siga siendo EXPRESABLE y se pueda demostrar que rojea.
    """

    def __init__(self, *, existe=True) -> None:
        self.fila: dict | None = (
            {"id": _UID, "username": "alopez", "rol": "mandos_medios", "activo": True} if existe else None
        )
        self.empleado_user_id: str | None = _UID  # empleados.user_id apuntando a este usuario

    def get_perfil(self, user_id):
        return dict(self.fila) if self.fila else None

    def set_activo(self, user_id, activo):
        assert self.fila is not None, "se intentó desactivar una fila inexistente"
        self.fila["activo"] = activo

    def borrar_fila(self) -> None:
        """Lo que hacía la baja DURA: el CASCADE se lleva la fila, el SET NULL el vínculo."""
        self.fila = None
        self.empleado_user_id = None


@pytest.fixture
def del_auth(monkeypatch):
    """Monkeypatchea auth.admin; registra tanto el ban como el borrado (que ya no debe ocurrir)."""
    def _apply(*, update_falla=False):
        fake = _FakeAuthAdmin(update_falla=update_falla)
        monkeypatch.setattr(usuario_service.supabase_admin, "auth", SimpleNamespace(admin=fake), raising=False)
        return fake
    return _apply


_OTRO_UID = "22222222-2222-2222-2222-222222222222"
_BAN = usuario_service._BAN_PERMANENTE


def test_baja_desactiva_banea_y_audita(del_auth):
    auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
    UsuarioService(repo=repo, audit=aud).eliminar_usuario(_UID, _OTRO_UID)
    assert repo.fila["activo"] is False                       # lo que hace regir la baja
    assert auth.actualizado == (_UID, {"ban_duration": _BAN})  # y lo que corta el refresh
    assert [c["evento"] for c in aud.calls] == ["baja_usuario"]
    assert aud.calls[0]["registro_id"] == _UID


def test_la_baja_no_borra_la_identidad(del_auth):
    """La mitad que cambió: antes acá había un delete_user y el CASCADE se llevaba todo."""
    auth, repo = del_auth(), _FakeDelRepo()
    UsuarioService(repo=repo, audit=_FakeAudit()).eliminar_usuario(_UID, _OTRO_UID)
    assert auth.borrado is None


def test_la_baja_conserva_la_fila_y_el_vinculo_con_el_empleado(del_auth):
    """El motivo de que sea blanda: el empleado no puede quedar sin su usuario, y la auditoría
    vieja tiene que seguir resolviendo el id a un nombre."""
    del_auth()
    repo = _FakeDelRepo()
    UsuarioService(repo=repo, audit=_FakeAudit()).eliminar_usuario(_UID, _OTRO_UID)
    assert repo.fila is not None and repo.fila["username"] == "alopez"
    assert repo.empleado_user_id == _UID


def test_la_baja_dura_habria_roto_el_vinculo():
    """Guarda de regresión: demuestra que el fake modela el daño y no da verde de arriba."""
    repo = _FakeDelRepo()
    repo.borrar_fila()
    assert repo.empleado_user_id is None


def test_la_baja_invalida_el_cache_para_que_rija_en_el_acto(del_auth, monkeypatch):
    """Sin esto la baja tardaría hasta el TTL (60s) en regir en el proceso que la ejecutó."""
    del_auth()
    invalidados: list[str] = []
    monkeypatch.setattr(usuario_service, "invalidar_estado", invalidados.append)
    UsuarioService(repo=_FakeDelRepo(), audit=_FakeAudit()).eliminar_usuario(_UID, _OTRO_UID)
    assert invalidados == [_UID]


def test_si_falla_el_ban_la_baja_queda_aplicada_y_avisa(del_auth):
    """El orden importa: la baja en nuestra base es la que corta, así que se aplica primero y
    NO se revierte. Revertir para dejar consistencia dejaría al usuario adentro."""
    auth, repo, aud = del_auth(update_falla=True), _FakeDelRepo(), _FakeAudit()
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=aud).eliminar_usuario(_UID, _OTRO_UID)
    assert e.value.code == "USUARIO_DELETE_ERROR" and e.value.status_code == 502
    assert repo.fila["activo"] is False            # la baja quedó puesta
    assert [c["evento"] for c in aud.calls] == ["baja_usuario"]  # y quedó registrada
    assert auth.borrado is None


def test_no_permite_autoeliminacion_400(del_auth):
    auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=aud).eliminar_usuario(_UID, _UID)  # ejecutor == objetivo
    assert e.value.code == "AUTOELIMINACION" and e.value.status_code == 400
    assert repo.fila["activo"] is True and auth.actualizado is None  # no se tocó nada
    assert aud.calls == []


def test_baja_usuario_inexistente_404(del_auth):
    auth, repo, aud = del_auth(), _FakeDelRepo(existe=False), _FakeAudit()
    with pytest.raises(AppError) as e:
        UsuarioService(repo=repo, audit=aud).eliminar_usuario(_UID, _OTRO_UID)
    assert e.value.code == "USUARIO_NOT_FOUND" and e.value.status_code == 404
    assert auth.actualizado is None and auth.borrado is None
    assert aud.calls == []
