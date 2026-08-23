"""
La CLASIFICACIÓN de un fallo de renovación del token de Google: qué status, qué code, qué dice.

Archivo propio porque cubre un módulo propio (`services/_google_token_fallo.py`), que es el
criterio del repo. `tests/test_google_token.py` prueba el contrato que ven los callers a través
de `access_token_valido`; acá se prueba la decisión en sí, sin pasar por el refresh.

## Qué se está protegiendo

Dos cosas que este repo ya pagó:

  1. **El status.** Esto salía 401 y el interceptor del front lee el status: un token de Google
     muerto deslogueaba al usuario cada vez que abría /vacantes. Once días seguidos.
  2. **El diagnóstico.** Todo fallo salía con el mismo mensaje, y el log solo tenía `str(exc)`
     —"Client error '400 Bad Request'"— así que `invalid_grant` (reconectá la cuenta) e
     `invalid_client` (el client_secret está mal) eran indistinguibles desde afuera.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · La excepción de "Google rechazó" LLEVA una respuesta con `status_code` y `json()`, igual que
    el `HTTPStatusError` real de httpx. Un fake sin `.response` haría caer todo en la rama
    transitoria y los tests de la rama de rechazo pasarían con la clasificación borrada.
  · Los dos casos usan status_code DISTINTOS (400 vs 503): si los dos fueran 4xx, el test no
    podría desmentir que el corte esté puesto en el lugar correcto.
  · Los mensajes se comparan por su INSTRUCCIÓN ("Reconectala" / "Reintentá"), no por igualdad
    con la constante: comparar contra la constante que el código exporta es afirmar que una
    variable es igual a sí misma.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "anon-key-de-test",
    "SUPABASE_SERVICE_KEY": "service-key-de-test",
    "JWT_SECRET": "jwt-secret-de-test-con-mas-de-32-caracteres",
    "ANTHROPIC_API_KEY": "sk-ant-de-test",
    "RESEND_API_KEY": "re_de_test",
}
for _clave, _valor in _TEST_ENV.items():
    os.environ.setdefault(_clave, _valor)

from services import _google_token_fallo as mod  # noqa: E402


class _RespuestaDeGoogle:
    """La respuesta HTTP que httpx cuelga de `HTTPStatusError.response`."""

    def __init__(self, status_code: int, body) -> None:
        self.status_code, self._body = status_code, body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _ConRespuesta(Exception):
    """`raise_for_status()` falló: Google contestó, y contestó rechazando."""

    def __init__(self, respuesta: _RespuestaDeGoogle) -> None:
        super().__init__("error de status")
        self.response = respuesta


def _rechazo(status: int = 400, body=None) -> Exception:
    return _ConRespuesta(_RespuestaDeGoogle(status, body if body is not None else {}))


class TestElStatusNuncaMasEs401:
    """El invariante que cierra el bug de /vacantes, dicho sin rodeos."""

    def test_un_rechazo_de_google_es_502(self) -> None:
        assert mod.error_de_renovacion(_rechazo()).status_code == 502

    def test_no_poder_hablar_con_google_tambien_es_502(self) -> None:
        assert mod.error_de_renovacion(TimeoutError("se cortó")).status_code == 502

    def test_un_5xx_de_google_es_transitorio_y_no_un_rechazo(self) -> None:
        """Google caído no es "te revocaron el permiso": ahí reintentar SÍ sirve."""
        error = mod.error_de_renovacion(_rechazo(status=503))
        assert error.status_code == 502 and error.code == "GMAIL_RENOVACION_FALLIDA"


class TestCadaCausaDiceQueHacer:
    def test_el_rechazo_manda_a_reconectar_la_cuenta(self) -> None:
        error = mod.error_de_renovacion(_rechazo(body={"error": "invalid_grant"}))
        assert error.code == "GMAIL_TOKEN_EXPIRED"
        assert "Reconectala" in error.message and "Configuración" in error.message

    def test_el_fallo_de_red_manda_a_esperar_y_NO_a_reconectar(self) -> None:
        """Es la mitad del valor de separar los dos casos: mandar a reconectar por un blip de red
        hace que RRHH rehaga una integración que estaba perfecta."""
        error = mod.error_de_renovacion(TimeoutError("se cortó"))
        assert error.code == "GMAIL_RENOVACION_FALLIDA"
        assert "Reintentá" in error.message and "Reconectala" not in error.message

    def test_los_dos_mensajes_son_distintos(self) -> None:
        """Si fueran el mismo, separar las causas no le llegaría nunca a quien mira la pantalla."""
        assert mod.MSG_REVOCADO != mod.MSG_SIN_CONTACTO


class TestElDetalleDeGoogleLlegaAlLog:
    """🔴 Lo que faltaba: once días de logs a ERROR que no decían POR QUÉ."""

    def test_saca_el_error_y_su_descripcion(self) -> None:
        detalle = mod.detalle_de_google(_rechazo(body={
            "error": "invalid_grant", "error_description": "Token has been expired or revoked.",
        }))
        assert detalle == "invalid_grant: Token has been expired or revoked."

    def test_distingue_invalid_grant_de_invalid_client(self) -> None:
        """Los DOS llegan como 400 y se arreglan de formas distintas: uno se reconecta, el otro
        es config nuestra. Si el log no los separa, nadie puede saber cuál pasó."""
        grant = mod.detalle_de_google(_rechazo(body={"error": "invalid_grant"}))
        client = mod.detalle_de_google(_rechazo(body={"error": "invalid_client"}))
        assert grant != client and "invalid_grant" in grant and "invalid_client" in client

    def test_sin_respuesta_no_hay_detalle_pero_tampoco_explota(self) -> None:
        assert mod.detalle_de_google(TimeoutError("se cortó")) is None

    def test_un_body_ilegible_no_puede_tumbar_el_log(self) -> None:
        """El log corre en el camino de un error: si esto levantara, el fallo original quedaría
        tapado por uno peor y sin ninguna traza."""
        assert mod.detalle_de_google(_rechazo(body=ValueError("no es JSON"))) is None

    def test_un_body_vacio_devuelve_None_y_no_una_cadena_vacia(self) -> None:
        """`extra={"google": ""}` en el log se lee como "Google no dijo nada", que es distinto de
        "no hubo respuesta". None dice la verdad en los dos casos."""
        assert mod.detalle_de_google(_rechazo(body={})) is None
