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


class _FakeRemitente:
    """La casilla del sistema. Por default NO hay ninguna designada.

    🔴 HAY QUE INYECTARLO SÍ O SÍ, no es una comodidad. Sin él, `UsuarioService` construye el
    `IntegracionRemitenteRepo` real y `get_remitente()` sale a la red: contra el Supabase falso
    de los tests eso levanta `ConnectError`, que el fail-open de la guarda se traga. O sea que
    los tests pasarían **por el camino de "no se pudo verificar"**, sin ejercitar la guarda —y
    seguirían pasando aunque la guarda no existiera—. Verificado: se comprobó que sin inyectar
    esto la lectura real levanta ConnectError y el except la absorbe.

    Modela la casilla de UN usuario concreto (no un booleano global): con un booleano,
    "bloquea al de la casilla" y "bloquea a todos" serían indistinguibles.
    """

    def __init__(self, user_id: str | None = None, *, falla: bool = False) -> None:
        self.user_id = user_id
        self.falla = falla
        self.llamadas = 0

    def get_remitente(self):
        self.llamadas += 1
        if self.falla:
            raise RuntimeError("supabase caído")
        if not self.user_id:
            return None
        # La fila ENTERA, como el `select("*")` real: de acá sale el user_id que mira la guarda.
        return {"user_id": self.user_id, "tipo": "google", "es_remitente_sistema": True,
                "email_cuenta": "rrhh@k.com", "activo": True}


def _svc(repo, audit, remitente: _FakeRemitente | None = None) -> UsuarioService:
    """Service con los tres colaboradores falsos. Sin casilla designada salvo que se pida."""
    return UsuarioService(repo=repo, audit=audit, remitente_repo=remitente or _FakeRemitente())


def test_baja_desactiva_banea_y_audita(del_auth):
    auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
    _svc(repo, aud).eliminar_usuario(_UID, _OTRO_UID)
    assert repo.fila["activo"] is False                       # lo que hace regir la baja
    assert auth.actualizado == (_UID, {"ban_duration": _BAN})  # y lo que corta el refresh
    assert [c["evento"] for c in aud.calls] == ["baja_usuario"]
    assert aud.calls[0]["registro_id"] == _UID


def test_la_baja_no_borra_la_identidad(del_auth):
    """La mitad que cambió: antes acá había un delete_user y el CASCADE se llevaba todo."""
    auth, repo = del_auth(), _FakeDelRepo()
    _svc(repo, _FakeAudit()).eliminar_usuario(_UID, _OTRO_UID)
    assert auth.borrado is None


def test_la_baja_conserva_la_fila_y_el_vinculo_con_el_empleado(del_auth):
    """El motivo de que sea blanda: el empleado no puede quedar sin su usuario, y la auditoría
    vieja tiene que seguir resolviendo el id a un nombre."""
    del_auth()
    repo = _FakeDelRepo()
    _svc(repo, _FakeAudit()).eliminar_usuario(_UID, _OTRO_UID)
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
    _svc(_FakeDelRepo(), _FakeAudit()).eliminar_usuario(_UID, _OTRO_UID)
    assert invalidados == [_UID]


def test_si_falla_el_ban_la_baja_queda_aplicada_y_avisa(del_auth):
    """El orden importa: la baja en nuestra base es la que corta, así que se aplica primero y
    NO se revierte. Revertir para dejar consistencia dejaría al usuario adentro."""
    auth, repo, aud = del_auth(update_falla=True), _FakeDelRepo(), _FakeAudit()
    with pytest.raises(AppError) as e:
        _svc(repo, aud).eliminar_usuario(_UID, _OTRO_UID)
    assert e.value.code == "USUARIO_DELETE_ERROR" and e.value.status_code == 502
    assert repo.fila["activo"] is False            # la baja quedó puesta
    assert [c["evento"] for c in aud.calls] == ["baja_usuario"]  # y quedó registrada
    assert auth.borrado is None


def test_no_permite_autoeliminacion_400(del_auth):
    auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
    with pytest.raises(AppError) as e:
        _svc(repo, aud).eliminar_usuario(_UID, _UID)  # ejecutor == objetivo
    assert e.value.code == "AUTOELIMINACION" and e.value.status_code == 400
    assert repo.fila["activo"] is True and auth.actualizado is None  # no se tocó nada
    assert aud.calls == []


def test_baja_usuario_inexistente_404(del_auth):
    auth, repo, aud = del_auth(), _FakeDelRepo(existe=False), _FakeAudit()
    with pytest.raises(AppError) as e:
        _svc(repo, aud).eliminar_usuario(_UID, _OTRO_UID)
    assert e.value.code == "USUARIO_NOT_FOUND" and e.value.status_code == 404
    assert auth.actualizado is None and auth.borrado is None
    assert aud.calls == []


# ─── Guarda: no se puede bajar al usuario que sostiene la casilla del sistema ──


class TestNoSePuedeBajarLaCasillaDelSistema:
    """`usuario_integraciones` cuelga de una persona: bajarla apaga el envío de mails de TODO el
    sistema, y hoy nadie se entera hasta que alguien intenta mandar uno.

    🔴 LOS TESTS USAN DOS USUARIOS (`_UID` y `_OTRO_UID`) Y LA CASILLA ESTÁ EN UNO SOLO. Con un
    solo usuario, "bloquea al de la casilla" y "bloquea a todas las bajas" darían el mismo
    resultado y ningún test podría distinguirlos.
    """

    def test_bajar_al_que_sostiene_la_casilla_da_409(self, del_auth):
        """¿Qué tendría que ser distinto en el fake para que falle? Que `_FakeRemitente`
        devolviera una fila SIN `user_id` (o None): ahí la guarda no tendría contra qué comparar
        y dejaría pasar la baja. Por eso la fila del fake trae el user_id, como el `select("*")`
        real."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        with pytest.raises(AppError) as e:
            _svc(repo, aud, _FakeRemitente(_UID)).eliminar_usuario(_UID, _OTRO_UID)
        assert e.value.code == "USUARIO_ES_REMITENTE_SISTEMA"
        assert e.value.status_code == 409

    def test_y_el_usuario_SIGUE_ACTIVO(self, del_auth):
        """🔴 No alcanza con que levante: hay que mirar el ESTADO. Un orden invertido
        —desactivar y después chequear— levantaría la misma excepción dejando al usuario abajo y
        el envío de mails caído, que es exactamente el daño que la guarda viene a evitar."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        with pytest.raises(AppError):
            _svc(repo, aud, _FakeRemitente(_UID)).eliminar_usuario(_UID, _OTRO_UID)
        assert repo.fila["activo"] is True      # no se tocó la baja
        assert auth.actualizado is None         # ni el ban
        assert aud.calls == []                  # ni se auditó una baja que no ocurrió

    def test_bajar_a_OTRO_usuario_funciona_normalmente(self, del_auth):
        """La casilla la sostiene `_OTRO_UID`; se da de baja a `_UID` y la baja procede.

        Es el test que impide que la guarda se implemente como "bloquear si hay casilla": con
        `_FakeRemitente(_OTRO_UID)` esa versión rompe acá."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        _svc(repo, aud, _FakeRemitente(_OTRO_UID)).eliminar_usuario(_UID, _OTRO_UID)
        assert repo.fila["activo"] is False
        assert auth.actualizado == (_UID, {"ban_duration": _BAN})
        assert [c["evento"] for c in aud.calls] == ["baja_usuario"]

    def test_sin_casilla_designada_la_baja_de_cualquiera_funciona(self, del_auth):
        """Estado inicial del sistema: nadie designó casilla todavía. No hay nada que proteger.

        ¿Qué tendría que ser distinto en el fake para que falle? Que `get_remitente()` devolviera
        una fila en vez de None — o sea, que el fake no supiera representar "no hay casilla"."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        _svc(repo, aud, _FakeRemitente(None)).eliminar_usuario(_UID, _OTRO_UID)
        assert repo.fila["activo"] is False
        assert [c["evento"] for c in aud.calls] == ["baja_usuario"]

    def test_una_fila_sin_user_id_no_bloquea_a_nadie(self, del_auth):
        """Fila marcada pero con `user_id` en NULL: no identifica a nadie, así que no puede
        bloquear una baja. Sin esta rama, `str(None) != str(_UID)` igual dejaría pasar, pero un
        cambio a `if remitente:` a secas bloquearía TODAS las bajas."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        rem = _FakeRemitente(_UID)
        rem.user_id = _UID
        svc = _svc(repo, aud, rem)
        rem.get_remitente = lambda: {"user_id": None, "tipo": "google"}  # type: ignore[method-assign]
        svc.eliminar_usuario(_UID, _OTRO_UID)
        assert repo.fila["activo"] is False

    def test_la_guarda_corre_ANTES_de_tocar_al_usuario(self, del_auth):
        """El orden explícito: cuando la guarda consulta la casilla, el usuario todavía está
        activo. Si el chequeo se moviera después del `set_activo`, acá se vería `False`."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        visto: list = []

        class _RemitenteQueMira:
            def get_remitente(self):
                visto.append(repo.fila["activo"])
                return None

        _svc(repo, aud, _RemitenteQueMira()).eliminar_usuario(_UID, _OTRO_UID)
        assert visto == [True], "la guarda corrió después de desactivar al usuario"

    def test_si_no_se_puede_verificar_la_baja_SIGUE(self, del_auth):
        """🔴 FAIL-OPEN deliberado. Dar de baja es una acción de SEGURIDAD: no puede quedar
        bloqueada porque un subsistema no relacionado esté caído. Lo que la guarda evita es un
        error operativo recuperable (designar otra casilla); fail-closed convertiría un blip de
        base en "no se puede echar a nadie"."""
        auth, repo, aud = del_auth(), _FakeDelRepo(), _FakeAudit()
        _svc(repo, aud, _FakeRemitente(_UID, falla=True)).eliminar_usuario(_UID, _OTRO_UID)
        assert repo.fila["activo"] is False

    def test_el_mensaje_es_accionable_y_sin_jerga(self, del_auth):
        """Un 409 que diga "conflicto" no le sirve a nadie: quien lo lee está en la pantalla de
        usuarios y necesita saber QUÉ pasa y A DÓNDE ir. Se afirma que nombra la consecuencia
        (mails) y la salida (designar otra en Configuración), no el texto literal."""
        del_auth()
        with pytest.raises(AppError) as e:
            _svc(_FakeDelRepo(), _FakeAudit(), _FakeRemitente(_UID)).eliminar_usuario(_UID, _OTRO_UID)
        msg = e.value.message.lower()
        assert "mails" in msg or "correo" in msg
        assert "configuración" in msg or "configuracion" in msg
        assert "designá" in msg or "designa" in msg
        for jerga in ("integración", "conflicto", "fk", "cascade", "usuario_integraciones"):
            assert jerga not in msg, f"jerga técnica en el mensaje: {jerga}"

    def test_la_autoeliminacion_gana_sobre_la_casilla(self, del_auth):
        """Si sos la casilla Y te estás bajando a vos mismo, sale el 400 de autoeliminación: es
        el chequeo más barato y no necesita consultar nada. Fija el orden de los tres."""
        del_auth()
        rem = _FakeRemitente(_UID)
        with pytest.raises(AppError) as e:
            _svc(_FakeDelRepo(), _FakeAudit(), rem).eliminar_usuario(_UID, _UID)
        assert e.value.code == "AUTOELIMINACION"
        assert rem.llamadas == 0, "no hacía falta consultar la casilla"

    def test_un_usuario_inexistente_da_404_no_409(self, del_auth):
        """El 404 va primero: un id que no existe no puede ser la casilla de nada."""
        del_auth()
        with pytest.raises(AppError) as e:
            _svc(_FakeDelRepo(existe=False), _FakeAudit(), _FakeRemitente(_UID)).eliminar_usuario(
                _UID, _OTRO_UID)
        assert e.value.code == "USUARIO_NOT_FOUND"


class TestLaFilaDelRemitenteTraeElUserId:
    """🔴 EL ESCALÓN QUE `_FakeRemitente` TAPA.

    Todos los tests de arriba inyectan un fake que devuelve un dict CON `user_id`, así que
    prueban que la guarda lo usa — no que el repo real lo traiga. Si alguien angostara el
    `select("*")` a las columnas "que se usan", `fila.get("user_id")` sería None y **la guarda
    dejaría de proteger en silencio**, con todos los tests de service en verde. Es la misma
    clase de agujero que dejó dos mappers rotos y un repo devolviendo su entrada sin que nadie
    se enterara.

    El mismo campo lo consume `mailer/engine._remitente`, así que angostarlo también apagaría
    el envío. Se faltea el cliente de Supabase, un escalón más abajo.
    """

    @staticmethod
    def _repo_con_espia(monkeypatch, data):
        import repositories.integracion_remitente_repo as mod

        capt: dict = {"select": None, "eq": []}

        class _Q:
            def select(self, spec):
                capt["select"] = spec
                return self

            def eq(self, col, val):
                capt["eq"].append((col, val))
                return self

            def maybe_single(self):
                return self

            def execute(self):
                return SimpleNamespace(data=data)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.IntegracionRemitenteRepo(), capt

    def test_la_fila_devuelta_incluye_user_id(self, monkeypatch) -> None:
        """El contrato del que depende la guarda: sin `user_id` no hay a quién proteger."""
        repo, _ = self._repo_con_espia(monkeypatch, {"user_id": _UID, "tipo": "google"})
        assert repo.get_remitente()["user_id"] == _UID

    def test_el_select_no_esta_angostado(self, monkeypatch) -> None:
        """Se pide la fila ENTERA. Si alguien enumera columnas, que rompa acá y no en producción
        con la guarda desactivada y el mailer diciendo que no hay casilla."""
        repo, capt = self._repo_con_espia(monkeypatch, {})
        repo.get_remitente()
        assert capt["select"] == "*", (
            "get_remitente tiene que traer la fila entera: la guarda de la baja y el mailer "
            "leen user_id y tokens de ahí"
        )

    def test_filtra_por_google_y_por_la_marca(self, monkeypatch) -> None:
        """Sin el filtro de `es_remitente_sistema` devolvería CUALQUIER integración de Google y
        la guarda bloquearía la baja de cualquiera que tenga Gmail conectado."""
        repo, capt = self._repo_con_espia(monkeypatch, {})
        repo.get_remitente()
        assert ("tipo", "google") in capt["eq"]
        assert ("es_remitente_sistema", True) in capt["eq"]

    def test_sin_casilla_devuelve_none(self, monkeypatch) -> None:
        """"Todavía nadie la configuró" es un estado válido, no un 500 (por eso maybe_single)."""
        repo, _ = self._repo_con_espia(monkeypatch, None)
        assert repo.get_remitente() is None
