"""
El error del proveedor traducido a un motivo que RRHH puede leer y accionar.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · Las excepciones se construyen con **las clases REALES del SDK** (`anthropic.RateLimitError`,
    `APITimeoutError`, `BadRequestError`…), no con stubs. Un fake que levantara siempre un
    `RuntimeError` haría indistinguibles "distingue las causas" y "siempre dice lo mismo": todos
    caerían en `desconocido` y cinco tests afirmarían el mismo mensaje sin notarlo.
  · Cada categoría se prueba con **su propia excepción y su propio mensaje esperado**, y hay un
    test que verifica que los cinco mensajes son distintos entre sí. Sin eso, colapsar cuatro
    categorías a una pasaría en verde.
  · El error de saldo se construye con **el texto literal que llegó de producción**, no con una
    paráfrasis: es lo único que puede desmentir que la detección por marcas funcione contra el
    wording real.
  · `_FakeLogger` **captura el `extra`**, que es lo único capaz de demostrar que el detalle
    técnico no se perdió al sacarlo de la pantalla.
"""
import httpx
import pytest

import anthropic
from services import _screening_candidato as sc
from services._error_ia import MENSAJES, PREFIJO_FALLO, categoria_de, motivo_de

# El texto EXACTO que llegó de producción. No es una paráfrasis a propósito.
_CRUDO_SALDO = (
    "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': "
    "'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing "
    "to upgrade or purchase credits.'}, 'request_id': 'req_011CdsmyFvjX1xUygdNP8Nb7'}"
)


def _status(clase, mensaje: str, status: int):
    """Una excepción de status del SDK, construida como la construye el SDK."""
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    res = httpx.Response(status, request=req, json={"error": {"message": mensaje}})
    return clase(mensaje, response=res, body=None)


def _conexion(clase=anthropic.APIConnectionError):
    return clase(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))


class TestCadaCausaTieneSuMensaje:
    """Cinco causas, cinco acciones distintas. El fake levanta las excepciones REALES del SDK."""

    def test_sin_saldo(self) -> None:
        exc = _status(anthropic.BadRequestError, _CRUDO_SALDO, 400)
        assert categoria_de(exc) == "saldo"
        assert "sin saldo" in motivo_de(exc)
        assert "recargue" in motivo_de(exc)

    @pytest.mark.parametrize("clase,status", [(anthropic.RateLimitError, 429)])
    def test_rate_limit(self, clase, status) -> None:
        assert categoria_de(_status(clase, "rate limited", status)) == "sobrecarga"

    def test_sobrecarga_del_proveedor(self) -> None:
        assert categoria_de(_status(anthropic.InternalServerError, "overloaded", 529)) == "sobrecarga"

    @pytest.mark.parametrize("clase", [anthropic.APIConnectionError, anthropic.APITimeoutError])
    def test_red_y_timeout(self, clase) -> None:
        """`APITimeoutError` hereda de `APIConnectionError`: si el orden del isinstance se
        invirtiera, el timeout caería en otra categoría."""
        assert categoria_de(_conexion(clase)) == "conexion"

    @pytest.mark.parametrize("clase,status", [(anthropic.AuthenticationError, 401),
                                              (anthropic.PermissionDeniedError, 403)])
    def test_credenciales(self, clase, status) -> None:
        assert categoria_de(_status(clase, "invalid x-api-key", status)) == "configuracion"

    def test_cualquier_otra_cosa(self) -> None:
        assert categoria_de(RuntimeError("algo raro")) == "desconocido"

    def test_los_cinco_mensajes_son_DISTINTOS(self) -> None:
        """Si alguien colapsara las categorías a un mensaje único, esto lo dice."""
        assert len(set(MENSAJES.values())) == len(MENSAJES) == 5


class TestUn400QueNoEsDeSaldo:
    """El caso que NO se puede distinguir por clase, y su degradación."""

    def test_un_400_sin_marcas_de_facturacion_NO_dice_sin_saldo(self) -> None:
        exc = _status(anthropic.BadRequestError, "max_tokens: must be greater than 0", 400)
        assert categoria_de(exc) == "configuracion"
        assert "saldo" not in motivo_de(exc)

    def test_y_NO_manda_a_reintentar(self) -> None:
        """Un 400 no se arregla apretando el botón otra vez. Mandar a RRHH a hacerlo diez veces
        es peor que no decir nada."""
        exc = _status(anthropic.BadRequestError, "malformed request", 400)
        motivo = motivo_de(exc)
        assert "Probá de nuevo" not in motivo
        assert "reintentar no lo va a resolver" in motivo

    @pytest.mark.parametrize("marca", ["credit balance", "billing", "credits", "quota",
                                       "insufficient", "payment"])
    def test_las_marcas_de_facturacion_se_detectan_sin_importar_las_mayusculas(self, marca) -> None:
        exc = _status(anthropic.BadRequestError, f"Something about {marca.upper()} here", 400)
        assert categoria_de(exc) == "saldo"

    def test_otro_status_cae_en_configuracion_y_no_en_desconocido(self) -> None:
        """404/409/422: no son de red ni de saldo, y reintentar tampoco los arregla."""
        assert categoria_de(_status(anthropic.NotFoundError, "model not found", 404)) == "configuracion"


class TestElMotivoNoFILTRAelCrudoDelProveedor:
    """🔴 EL TEST DE LA SESIÓN. Sin esto, un motivo que concatene el original pasaría."""

    _PROHIBIDO = ("Error code", "request_id", "req_011", "Anthropic", "invalid_request_error",
                  "Plans & Billing", "credit balance")

    @pytest.mark.parametrize("prohibido", _PROHIBIDO)
    def test_el_texto_del_proveedor_no_aparece_en_el_motivo(self, prohibido: str) -> None:
        motivo = motivo_de(_status(anthropic.BadRequestError, _CRUDO_SALDO, 400))
        assert prohibido not in motivo

    def test_el_motivo_esta_en_castellano_y_es_corto(self) -> None:
        motivo = motivo_de(_status(anthropic.BadRequestError, _CRUDO_SALDO, 400))
        assert motivo.startswith(PREFIJO_FALLO)
        assert len(motivo) < 250      # entra en la ficha sin desbordarla
        assert "{" not in motivo and "'" not in motivo   # nada de payload crudo

    @pytest.mark.parametrize("exc", [
        _status(anthropic.BadRequestError, _CRUDO_SALDO, 400),
        _status(anthropic.RateLimitError, "rate limited", 429),
        _conexion(),
        _status(anthropic.AuthenticationError, "invalid x-api-key", 401),
        RuntimeError("boom interno"),
    ])
    def test_ninguna_categoria_filtra_nada(self, exc) -> None:
        motivo = motivo_de(exc)
        for prohibido in ("Error code", "request_id", "Anthropic", "api-key", "boom interno"):
            assert prohibido not in motivo


class _FakeRepo:
    def __init__(self) -> None:
        self.fallos: list = []

    def set_fallo(self, candidato_id, motivo, empresa_id=None):
        self.fallos.append(motivo)

    def set_clasificacion(self, *a, **k):  # pragma: no cover — no se llega acá en estos tests
        raise AssertionError("no debería clasificar")


class _FakeLogger:
    """Captura el `extra`: es lo único que puede demostrar que el detalle NO se perdió."""

    def __init__(self) -> None:
        self.errores: list = []

    def error(self, mensaje, extra=None):
        self.errores.append((mensaje, extra or {}))


class _ClienteQueFalla:
    def __init__(self, exc) -> None:
        self.exc = exc
        self.messages = self

    def create(self, **kw):
        raise self.exc


class TestElLogSIconservaElDetalle:
    """Sacarlo de la pantalla no puede perder información: por eso el log lo tiene entero."""

    def _correr(self, monkeypatch, exc):
        from types import SimpleNamespace
        log, repo = _FakeLogger(), _FakeRepo()
        monkeypatch.setattr(sc, "logger", log)
        vac = SimpleNamespace(titulo="Analista", area_nombre="Adm", descripcion=None,
                              funciones="conciliaciones", requisitos=None, formacion=None,
                              experiencia=None, conocimientos_tecnicos=None)
        crit = SimpleNamespace(def_relevante="a", def_dudoso="b", def_no_relevante="c",
                               instrucciones="")
        fila = {"id": "c1", "nombre": "N", "apellido": "A", "cv_texto": "cv " * 200,
                "screening_warning": None}
        sc.clasificar_uno(fila, vac, crit, None, repo=repo, cliente=_ClienteQueFalla(exc))
        return log, repo

    def test_el_request_id_del_proveedor_queda_en_el_log(self, monkeypatch) -> None:
        """Es lo que permite pedirle al proveedor que rastree una llamada puntual."""
        log, repo = self._correr(monkeypatch, _status(anthropic.BadRequestError, _CRUDO_SALDO, 400))
        _, extra = log.errores[0]
        assert "req_011CdsmyFvjX1xUygdNP8Nb7" in extra["error"]
        assert "credit balance" in extra["error"]
        # …y NO en lo que se persiste.
        assert "req_011" not in repo.fallos[0]

    def test_el_log_dice_la_clase_y_la_categoria(self, monkeypatch) -> None:
        """Sin esto el log tiene el texto pero no es greppable por causa."""
        log, _ = self._correr(monkeypatch, _status(anthropic.RateLimitError, "slow down", 429))
        _, extra = log.errores[0]
        assert extra["excepcion"] == "RateLimitError"
        assert extra["categoria"] == "sobrecarga"

    def test_lo_persistido_es_el_mensaje_traducido(self, monkeypatch) -> None:
        _, repo = self._correr(monkeypatch, _status(anthropic.BadRequestError, _CRUDO_SALDO, 400))
        assert repo.fallos == [f"{PREFIJO_FALLO}: {MENSAJES['saldo']}"]
