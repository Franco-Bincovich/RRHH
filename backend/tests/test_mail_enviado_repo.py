"""
T3 — `MailEnviadoRepo` contra el CLIENTE DE SUPABASE FALSEADO, no contra un fake de repo.

QUÉ SOSTIENE ESTO. `ya_enviado()` es lo único que impide que un lote cortado por el timeout de
Vercel se REENVÍE ENTERO al reintentarlo. El peor caso del módulo de mails no es que tarde: es que
30 personas de afuera reciban el mismo mail dos veces, y eso no se deshace.

🔴 POR QUÉ EL FAKE ES EL CLIENTE Y NO EL REPO. `test_mail_envio.py` prueba la idempotencia con un
`_Log` que recuerda en memoria: eso verifica que el SERVICE pregunte, no que la CONSULTA sea
correcta. Un `.eq("estado", ...)` borrado, una columna cambiada o un `gte` invertido dejan ese
test en verde y la garantía rota. Es el patrón que este repo ya pagó cinco veces: mappers rotos
con 10 tests verdes, un repo que devolvía su entrada con 20, un select angostado con 43.
Molde: `TestElOrdenLoPoneLaQuery` (test_historial_salarial.py) y `test_mail_historial.py`.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. `_Tabla` REGISTRA cada `.select/.eq/.gte/.limit/.insert` y los tests afirman sobre eso. Un
     fake que solo devolviera filas no podría desmentir NINGUNA de las condiciones del WHERE.
  2. Las DOS formas de destinatario se prueban una contra otra (`empleado_id` vs `destinatario`):
     con una sola, la rama que se agregó para el envío a direcciones sueltas quedaría sin cubrir
     — y es justo la que se tocó último.
  3. `_Tabla` devuelve lo que se le cargó, así que `ya_enviado` se prueba en sus DOS desenlaces
     (hay fila → True, no hay → False). Con uno solo, un `return True` fijo pasaría.
  4. Los atributos de registro NO se llaman como los métodos (`eqs`, no `eq`): un atributo de
     instancia con el mismo nombre pisa al método y la cadena revienta. Ya pasó en este repo.
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

from datetime import date, datetime, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories.mail_enviado_repo as repo_mod  # noqa: E402
import services.mailer.engine as engine  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPLEADO = str(uuid4())
CLAVE = "bienvenida"


class _Tabla:
    """Cliente de Supabase falseado que REGISTRA la consulta. Es el único nivel donde se puede
    ver si una condición del WHERE viajó de verdad."""

    def __init__(self, filas) -> None:
        self.filas = filas
        self.eqs: dict = {}
        self.gtes: dict = {}
        self.limite = None
        self.select_spec = None
        self.insertado = None

    def select(self, spec):
        self.select_spec = spec
        return self

    def eq(self, col, val):
        self.eqs[col] = val
        return self

    def gte(self, col, val):
        self.gtes[col] = val
        return self

    def limit(self, n):
        self.limite = n
        return self

    def insert(self, fila):
        self.insertado = fila
        self.filas = [{**fila, "id": str(uuid4())}]
        return self

    def execute(self):
        return SimpleNamespace(data=self.filas)


def _repo(monkeypatch, filas=None):
    tabla = _Tabla(filas if filas is not None else [])
    monkeypatch.setattr(repo_mod, "supabase_admin", SimpleNamespace(table=lambda _n: tabla))
    return repo_mod.MailEnviadoRepo(), tabla


# ── 1. 🔴 La idempotencia: qué pregunta la consulta ───────────────────────────

class TestYaEnviadoPorEmpleado:

    def test_pregunta_por_la_plantilla_Y_el_empleado(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, EMPLEADO)

        assert tabla.eqs["plantilla_clave"] == CLAVE
        assert tabla.eqs["empleado_id"] == EMPLEADO

    def test_solo_cuentan_los_enviados_no_los_fallidos(self, monkeypatch) -> None:
        """Un intento FALLIDO no puede bloquear el reintento: reintentarlo es exactamente lo que
        se quiere. Sin este `.eq`, una dirección que rebotó quedaría marcada como entregada y
        nadie la volvería a intentar nunca."""
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, EMPLEADO)

        assert tabla.eqs["estado"] == "enviado"

    def test_la_ventana_arranca_al_COMIENZO_DEL_DIA_UTC(self, monkeypatch) -> None:
        """🔴 No son "las últimas 24 h". Con una ventana móvil, el mismo lote reintentado a las
        23:50 y a las 00:10 se comporta distinto según la hora — la clase de bug que aparece una
        vez cada tanto y que nadie reproduce."""
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, EMPLEADO)

        marca = datetime.fromisoformat(tabla.gtes["created_at"])
        assert marca.date() == date.today()
        assert (marca.hour, marca.minute, marca.second) == (0, 0, 0)
        assert marca.tzinfo is not None, "sin tz, Postgres lo interpreta en la zona del servidor"

    def test_un_desde_explicito_se_respeta(self, monkeypatch) -> None:
        """Contrapeso: sin esto, un `desde` ignorado pasaría el test de arriba igual."""
        repo, tabla = _repo(monkeypatch)
        desde = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)

        repo.ya_enviado(CLAVE, EMPLEADO, desde=desde)

        assert tabla.gtes["created_at"] == desde.isoformat()

    def test_pide_UNA_sola_fila(self, monkeypatch) -> None:
        """Es un `EXISTS`, no un listado: traer todo el historial para contestar un booleano."""
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, EMPLEADO)

        assert tabla.limite == 1

    def test_no_trae_el_cuerpo_del_mail(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, EMPLEADO)

        assert tabla.select_spec == "id"

    def test_con_una_fila_devuelve_True(self, monkeypatch) -> None:
        repo, _ = _repo(monkeypatch, filas=[{"id": "x"}])

        assert repo.ya_enviado(CLAVE, EMPLEADO) is True

    def test_sin_filas_devuelve_False(self, monkeypatch) -> None:
        """El otro desenlace. Con uno solo, un `return True` fijo pasaría."""
        repo, _ = _repo(monkeypatch, filas=[])

        assert repo.ya_enviado(CLAVE, EMPLEADO) is False


class TestYaEnviadoPorDireccionLibre:
    """🔴 La rama que se agregó para el envío a direcciones escritas a mano. Sin `empleado_id` no
    hay con qué preguntar, así que la consulta va por `destinatario`. Antes esta función solo
    sabía preguntar por empleado: un lote libre cortado se habría reenviado entero."""

    def test_pregunta_por_DESTINATARIO_cuando_no_hay_empleado(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, destinatario="ana@k.com")

        assert tabla.eqs["destinatario"] == "ana@k.com"
        assert "empleado_id" not in tabla.eqs

    def test_con_empleado_NO_pregunta_por_destinatario(self, monkeypatch) -> None:
        """Las dos ramas se afirman una contra la otra: si la condición eligiera siempre la misma
        columna, uno de los dos tests rojea."""
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, EMPLEADO, destinatario="ana@k.com")

        assert tabla.eqs["empleado_id"] == EMPLEADO
        assert "destinatario" not in tabla.eqs

    def test_el_resto_de_las_condiciones_son_las_MISMAS(self, monkeypatch) -> None:
        """La semántica no cambia por el modo: misma plantilla, mismo estado, misma ventana."""
        repo, tabla = _repo(monkeypatch)

        repo.ya_enviado(CLAVE, destinatario="ana@k.com")

        assert tabla.eqs["plantilla_clave"] == CLAVE
        assert tabla.eqs["estado"] == "enviado"
        assert "created_at" in tabla.gtes

    def test_devuelve_True_si_esa_direccion_ya_recibio_el_mail(self, monkeypatch) -> None:
        repo, _ = _repo(monkeypatch, filas=[{"id": "x"}])

        assert repo.ya_enviado(CLAVE, destinatario="ana@k.com") is True


# ── 2. `registrar`: la fila que queda ─────────────────────────────────────────

class TestRegistrar:

    def test_inserta_la_fila_tal_cual_y_devuelve_la_creada(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)
        fila = {"destinatario": "ana@k.com", "estado": "enviado", "asunto_render": "Hola"}

        out = repo.registrar(fila)

        assert tabla.insertado == fila
        assert out["destinatario"] == "ana@k.com" and "id" in out

    def test_un_insert_que_no_devuelve_nada_da_None_y_NO_rompe(self, monkeypatch) -> None:
        """El mail ya salió: el caller no puede reventar porque el log no contestó."""
        repo, tabla = _repo(monkeypatch)
        tabla.insert = lambda fila: SimpleNamespace(execute=lambda: SimpleNamespace(data=[]))

        assert repo.registrar({"destinatario": "ana@k.com"}) is None


# ── 3. 🔴 El registro del FALLO, desde el punto de salida único ───────────────

class _LogEspia:
    def __init__(self) -> None:
        self.filas: list = []

    def registrar(self, fila):
        self.filas.append(fila)
        return fila


def _mailer(monkeypatch, falla: bool):
    """Arma `enviar_mail` con el proveedor falseado. Se parchea el DICT de proveedores, que es el
    punto de despacho real: así el test recorre el mismo camino que producción, incluido el
    registro que vive en el engine y NO en el proveedor."""
    def _enviar(token, remitente, destinatario, asunto, html, md):
        if falla:
            raise AppError("Gmail rechazó el envío", "MAIL_ERROR_PROVEEDOR", 502)
        return "gmail-msg-1"

    monkeypatch.setattr(engine, "_PROVEEDORES", {"gmail": _enviar})
    monkeypatch.setattr(engine, "access_token_valido", lambda repo, user_id: "tok")
    log = _LogEspia()
    remitente = SimpleNamespace(get_remitente=lambda: {
        "user_id": "u1", "email_cuenta": "sistema@k.com"})
    return log, remitente


class TestElFalloQuedaRegistrado:
    """Es lo que hace posible contestar "no me llegó". Sin la fila, el caso en que MÁS se necesita
    el log es justo el que no deja rastro."""

    def test_un_envio_fallido_escribe_estado_fallido_con_el_motivo(self, monkeypatch) -> None:
        log, remitente = _mailer(monkeypatch, falla=True)

        with pytest.raises(AppError):
            engine.enviar_mail("ana@k.com", "Hola", "Texto", plantilla_clave=CLAVE,
                               log_repo=log, remitente_repo=remitente)

        assert len(log.filas) == 1
        fila = log.filas[0]
        assert fila["estado"] == "fallido"
        assert "MAIL_ERROR_PROVEEDOR" in fila["error"] and "rechazó" in fila["error"]

    def test_el_fallo_se_registra_ANTES_de_propagar(self, monkeypatch) -> None:
        """Si el `raise` fuera primero, la fila no se escribiría nunca — y el error igual llega
        al usuario, así que el síntoma sería idéntico salvo por el log que falta."""
        log, remitente = _mailer(monkeypatch, falla=True)

        with pytest.raises(AppError) as exc:
            engine.enviar_mail("ana@k.com", "Hola", "Texto", log_repo=log, remitente_repo=remitente)

        assert exc.value.code == "MAIL_ERROR_PROVEEDOR"   # sí propaga
        assert log.filas[0]["estado"] == "fallido"        # y además dejó rastro

    def test_la_fila_del_fallo_conserva_el_destinatario_y_el_texto(self, monkeypatch) -> None:
        """Es lo que permite reconstruir qué se intentó mandar y a quién."""
        log, remitente = _mailer(monkeypatch, falla=True)

        with pytest.raises(AppError):
            engine.enviar_mail("ana@k.com", "Asunto real", "Cuerpo real",
                               plantilla_clave=CLAVE, log_repo=log, remitente_repo=remitente)

        fila = log.filas[0]
        assert fila["destinatario"] == "ana@k.com"
        assert fila["asunto_render"] == "Asunto real" and fila["cuerpo_render"] == "Cuerpo real"
        assert fila["plantilla_clave"] == CLAVE

    def test_un_envio_OK_queda_como_enviado_y_SIN_error(self, monkeypatch) -> None:
        """🔴 EL CONTRAPESO. Sin esto, un `estado` hardcodeado en 'fallido' pasaría todo lo de
        arriba — y la idempotencia, que solo mira los 'enviado', dejaría de funcionar entera."""
        log, remitente = _mailer(monkeypatch, falla=False)

        engine.enviar_mail("ana@k.com", "Hola", "Texto", log_repo=log, remitente_repo=remitente)

        fila = log.filas[0]
        assert fila["estado"] == "enviado"
        assert fila.get("error") is None
        assert fila["gmail_message_id"] == "gmail-msg-1"

    def test_los_dos_estados_usan_el_literal_que_el_CHECK_de_la_tabla_acepta(self, monkeypatch) -> None:
        """`mail_enviado_estado_check` solo admite 'enviado' y 'fallido'. Un tercer valor haría
        fallar el INSERT, y `_registrar` se traga la excepción: el evento desaparecería."""
        log_ok, rem_ok = _mailer(monkeypatch, falla=False)
        engine.enviar_mail("a@k.com", "H", "T", log_repo=log_ok, remitente_repo=rem_ok)
        log_mal, rem_mal = _mailer(monkeypatch, falla=True)
        with pytest.raises(AppError):
            engine.enviar_mail("a@k.com", "H", "T", log_repo=log_mal, remitente_repo=rem_mal)

        assert {log_ok.filas[0]["estado"], log_mal.filas[0]["estado"]} == {"enviado", "fallido"}

    def test_un_fallo_del_LOG_no_tumba_el_envio(self, monkeypatch) -> None:
        """El mail ya salió: que no se pueda escribir la fila no puede cambiar ese hecho."""
        _, remitente = _mailer(monkeypatch, falla=False)
        roto = SimpleNamespace(registrar=lambda fila: (_ for _ in ()).throw(RuntimeError("db")))

        out = engine.enviar_mail("ana@k.com", "Hola", "Texto",
                                 log_repo=roto, remitente_repo=remitente)

        assert out["enviado"] is True
