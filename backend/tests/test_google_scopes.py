"""
El scope de envío y el aviso previo — sin red.

El problema que cubren: agregar `gmail.send` NO amplía el consentimiento ya otorgado. La
integración que RRHH tiene conectada sigue leyendo, pero el primer intento de envío devuelve
403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`. Que eso se sepa ANTES —y no en medio de un envío— es
todo el punto de guardar los scopes concedidos.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_Repo` devuelve filas con listas de scopes DISTINTAS entre sí (con envío, sin envío, y
    None). Un fake que devolviera siempre la misma lista no podría distinguir "leyó los scopes"
    de "devolvió un valor fijo".
  · La fila SIN la clave `scopes` (None) está modelada aparte: es literalmente el estado de la
    integración que existe hoy en producción, conectada antes de que la columna existiera.
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

import pytest

from services._google_scopes import SCOPE_ENVIO, SCOPE_LECTURA, SCOPES_PEDIDOS, puede_enviar
from services.integracion_service import IntegracionService


class _Repo:
    """Integraciones fake. Cada fila trae una lista de scopes DISTINTA — sin eso, ningún test
    de acá podría desmentir que el service devuelve un booleano fijo."""

    def __init__(self, scopes, tipo: str = "google") -> None:
        self._fila = {"tipo": tipo, "activo": True, "email_cuenta": "a@b.com"}
        if scopes is not _SIN_CLAVE:
            self._fila["scopes"] = scopes

    def get_by_user(self, user_id):
        return [self._fila]


_SIN_CLAVE = object()   # la fila no trae la columna: integración anterior a la migración 087


# ── El helper, aislado ────────────────────────────────────────────────────────

class TestPuedeEnviar:
    def test_con_el_scope_de_envio_es_true(self) -> None:
        assert puede_enviar([SCOPE_LECTURA, SCOPE_ENVIO]) is True

    def test_solo_con_lectura_es_false(self) -> None:
        """🔴 El estado exacto de la integración conectada hoy en producción."""
        assert puede_enviar([SCOPE_LECTURA]) is False

    @pytest.mark.parametrize("vacio", [None, [], ()], ids=["none", "lista", "tupla"])
    def test_sin_scopes_guardados_es_false(self, vacio) -> None:
        """Conectada ANTES de que existiera la columna. Asumir que puede enviar sería justo el
        403-en-el-peor-momento que esto vino a evitar: sin dato, se asume que NO."""
        assert puede_enviar(vacio) is False

    def test_el_orden_y_los_extras_no_importan(self) -> None:
        assert puede_enviar(["openid", SCOPE_ENVIO, "otro"]) is True


def test_el_scope_de_envio_esta_entre_los_pedidos() -> None:
    """Si alguien lo saca de la lista, nadie vuelve a poder conceder el permiso — y el helper
    diría False para siempre, sin que ningún otro test se entere."""
    assert SCOPE_ENVIO in SCOPES_PEDIDOS


def test_no_se_pide_acceso_al_buzon_entero() -> None:
    """🔴 `gmail.send` es lo mínimo para enviar. `gmail.modify` y `mail.google.com` dan el buzón
    completo para la misma tarea: si alguien los agrega, este test lo frena."""
    assert not {"https://mail.google.com/",
                "https://www.googleapis.com/auth/gmail.modify"} & set(SCOPES_PEDIDOS)


# ── El aviso llega al front por la respuesta de la API ────────────────────────

class TestElServiceLoExpone:
    @staticmethod
    def _google(scopes):
        integraciones = IntegracionService(repo=_Repo(scopes)).get_integraciones("u1")
        return next(i for i in integraciones if i.tipo == "google")

    def test_conectada_con_envio_reporta_puede_enviar(self) -> None:
        assert self._google([SCOPE_LECTURA, SCOPE_ENVIO]).puede_enviar is True

    def test_conectada_SIN_envio_reporta_que_no_puede(self) -> None:
        """Es lo que la UI necesita para avisar "reconectá" antes de que alguien intente mandar.
        Para que falle: que el service deje de leer `scopes` y devuelva `connected` como si
        fuera lo mismo — que es exactamente el estado anterior a este commit."""
        google = self._google([SCOPE_LECTURA])
        assert google.connected is True and google.puede_enviar is False

    def test_una_integracion_vieja_sin_la_columna_no_puede_enviar(self) -> None:
        assert self._google(_SIN_CLAVE).puede_enviar is False

    def test_una_integracion_que_no_es_google_nunca_puede_enviar(self) -> None:
        """El scope de Gmail no significa nada en Anthropic o Zernio. Aunque la fila trajera el
        scope por error, `puede_enviar` tiene que dar False para las otras dos."""
        integraciones = IntegracionService(
            repo=_Repo([SCOPE_ENVIO], tipo="anthropic")).get_integraciones("u1")
        assert all(i.puede_enviar is False for i in integraciones if i.tipo != "google")

    def test_desconectada_no_puede_enviar(self) -> None:
        """Sin integración no hay fila: el default del schema tiene que ser False, no None."""
        integraciones = IntegracionService(repo=_RepoVacio()).get_integraciones("u1")
        assert all(i.puede_enviar is False and i.connected is False for i in integraciones)


class _RepoVacio:
    def get_by_user(self, user_id):
        return []
