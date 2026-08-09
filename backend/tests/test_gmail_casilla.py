"""
De QUÉ casilla se leen las postulaciones: la del SISTEMA, no la del usuario que apretó el botón.

## 🔴 EL FAKE TIENE DOS INTEGRACIONES, Y ESA ES TODA LA GRACIA DEL ARCHIVO

Hasta el 8/8/2026 `gmail_service` pedía el token con `access_token_valido(IntegracionRepo(),
user_id)` — la cuenta de quien disparaba la acción. **El bug sobrevivió meses porque en la base
hay UNA sola integración, y esa fila es a la vez la del usuario y la marcada
`es_remitente_sistema`**: "lee la del sistema" y "lee la del usuario" resolvían al mismo buzón y
eran literalmente indistinguibles.

Un fake con una sola integración reproduce exactamente esa ceguera. Por eso `_Integraciones`
expone las DOS puertas con **tokens distintos**:

  · `get_remitente()`            → `TOKEN_SISTEMA`   (la casilla institucional, sin user_id)
  · `get_by_user_and_tipo(...)`  → `TOKEN_USUARIO`   (la cuenta personal de quien pregunta)

Cualquier test de este archivo puede decir cuál de las dos se usó mirando el token que viaja. Con
un solo token, ninguno podría.

⚠️ Estos tests corren la resolución REAL (`_casilla_sistema.token_de_lectura` completo, incluidos
`repo_de` y `access_token_valido`); lo único falseado es el repo y la red. Por eso las filas
llevan `token_expiry` en el futuro: con una vencida, `access_token_valido` saldría a renovar
contra Google y el test dejaría de ser hermético.
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

import inspect  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

import services.gmail_service as gmail_mod  # noqa: E402
from services import _casilla_sistema  # noqa: E402
from services._casilla_sistema import fila_o_error, token_de_lectura  # noqa: E402
from utils.errors import AppError  # noqa: E402

TOKEN_SISTEMA = "token-de-la-casilla-del-sistema"
TOKEN_USUARIO = "token-de-la-cuenta-personal"
EMPRESA = uuid4()
VACANTE = UUID("11111111-1111-1111-1111-111111111111")

_FUTURO = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _fila(token: str, user_id: str, email: str) -> dict:
    """Una integración entera, como la devuelve `select("*")` del repo real."""
    return {"user_id": user_id, "tipo": "google", "access_token": token,
            "refresh_token": "r", "token_expiry": _FUTURO, "email_cuenta": email,
            "es_remitente_sistema": token == TOKEN_SISTEMA}


class _Integraciones:
    """LAS DOS PUERTAS, con contenidos distintos. Ver el encabezado."""

    def __init__(self, con_casilla: bool = True, casilla_sin_user_id: bool = False) -> None:
        self._con_casilla, self._sin_user = con_casilla, casilla_sin_user_id

    def get_remitente(self):
        if not self._con_casilla:
            return None
        fila = _fila(TOKEN_SISTEMA, "user-sistema", "postulaciones@karstec.com")
        if self._sin_user:
            fila["user_id"] = None
        return fila

    def get_by_user_and_tipo(self, user_id, tipo):
        return _fila(TOKEN_USUARIO, user_id, "personal@gmail.com")


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── 1. La resolución del token ────────────────────────────────────────────────

class TestDeQueCasillaSale:

    def test_sale_la_del_sistema_y_no_la_del_usuario(self) -> None:
        """🔴 EL TEST DEL ENUNCIADO (A3).

        ¿Qué tendría que ser distinto en el fake para que falle? Que las dos integraciones
        devolvieran el MISMO token: ahí las dos rutas serían indistinguibles y el test pasaría
        con la implementación vieja — que es exactamente por qué el bug sobrevivió en producción.
        """
        assert token_de_lectura(_Integraciones()) == TOKEN_SISTEMA
        assert token_de_lectura(_Integraciones()) != TOKEN_USUARIO

    def test_no_hay_fallback_a_la_del_usuario(self) -> None:
        """Sin casilla designada NO se cae a la cuenta personal, aunque exista y sirva.

        El fake tiene una integración de usuario perfectamente utilizable: si hubiera fallback,
        esto devolvería `TOKEN_USUARIO` en vez de cortar. Un fallback haría que el resultado
        dependa de quién pregunta, que es la ambigüedad que la casilla del sistema vino a cerrar.
        """
        err = _error(lambda: token_de_lectura(_Integraciones(con_casilla=False)))
        assert err.code == "GMAIL_SIN_CASILLA"

    def test_la_lectura_no_necesita_user_id(self) -> None:
        """La firma lo prueba: un proceso automático no tiene `user_id` que aportar, y sin este
        cambio la automatización del CV screening sería imposible."""
        params = inspect.signature(token_de_lectura).parameters
        assert "user_id" not in params
        for metodo in ("token", "ids_con_adjunto", "mensaje_completo"):
            assert "user_id" not in inspect.signature(
                getattr(gmail_mod.GmailService, metodo)).parameters, \
                f"{metodo} todavía recibe user_id: la lectura seguiría dependiendo de quién pregunta"


# ── 2. El error cuando no hay casilla (A2) ────────────────────────────────────

class TestElErrorEsAccionable:

    def test_dice_que_falta_y_donde_configurarlo(self) -> None:
        """Molde `MAIL_SIN_REMITENTE`: el mensaje nombra la consecuencia y la acción concreta."""
        err = _error(lambda: token_de_lectura(_Integraciones(con_casilla=False)))
        assert err.status_code == 400
        assert "postulaciones" in err.message, "no dice QUÉ se rompió"
        assert "Configuración" in err.message and "casilla del sistema" in err.message, \
            "no dice DÓNDE arreglarlo"

    def test_una_casilla_sin_user_id_tampoco_sirve(self) -> None:
        """`get_remitente` trae la fila entera y de ahí sale el dueño con el que se renueva el
        token. Sin `user_id` la fila no sirve, y fallar acá da el mensaje accionable en vez de un
        KeyError más abajo."""
        err = _error(lambda: token_de_lectura(_Integraciones(casilla_sin_user_id=True)))
        assert err.code == "GMAIL_SIN_CASILLA"

    def test_el_envio_conserva_su_propio_code_y_mensaje(self) -> None:
        """La resolución se comparte, los mensajes NO: cada camino nombra su consecuencia.
        Que el envío siga diciendo lo suyo es lo que prueba que el corte no cambió su contrato."""
        err = _error(lambda: fila_o_error(_Integraciones(con_casilla=False),
                                          _casilla_sistema.MSG_ENVIO, "MAIL_SIN_REMITENTE"))
        assert (err.code, err.status_code) == ("MAIL_SIN_REMITENTE", 400)
        assert "enviar" in err.message and "Configuración" in err.message


class TestElEnvioYLaLecturaCompartenLaResolucion:
    """Estructural: si el envío se copiara su propia versión, un arreglo quedaría en un lado solo.
    Es el mismo argumento con el que `_google_token` se extrajo en su momento."""

    def test_el_mailer_usa_el_modulo_compartido(self) -> None:
        from services.mailer import engine
        fuente = inspect.getsource(engine)
        assert "from services._casilla_sistema import" in fuente
        assert "def _remitente(" not in fuente, "el mailer se quedó con su copia de la resolución"


# ── 3. Punta a punta: qué token viaja en el header ────────────────────────────

class _Client:
    """httpx falso que CAPTURA el Authorization de cada request."""

    vistos: list = []

    def __call__(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **k):
        _Client.vistos.append(k.get("headers", {}).get("Authorization"))
        return SimpleNamespace(raise_for_status=lambda: None, is_success=True,
                               json=lambda: {"messages": [], "payload": {"headers": []}})


def test_el_token_que_viaja_a_gmail_es_el_de_la_casilla(monkeypatch) -> None:
    """El extremo del cable: no alcanza con que `token_de_lectura` devuelva el token bueno si el
    service después usa otro. Se mira el header real que sale hacia la API.

    ¿Qué tendría que ser distinto en el fake para que falle? Que `_Integraciones` devolviera el
    mismo token por las dos puertas — ahí este assert no distinguiría nada.
    """
    _Client.vistos = []
    monkeypatch.setattr(gmail_mod, "IntegracionRemitenteRepo", _Integraciones)
    servicio = gmail_mod.GmailService()
    servicio.ids_con_adjunto(_Client(), servicio.token())
    assert _Client.vistos, "no salió ningún request: el test no miró nada"
    assert all(h == f"Bearer {TOKEN_SISTEMA}" for h in _Client.vistos)
    assert f"Bearer {TOKEN_USUARIO}" not in _Client.vistos
