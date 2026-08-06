"""
El scope de envío, el aviso previo y la designación de la casilla del sistema — sin red.

El problema que cubren: agregar `gmail.send` NO amplía el consentimiento ya otorgado. La
integración que RRHH tiene conectada sigue leyendo, pero el primer intento de envío devuelve
403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`. Que eso se sepa ANTES —y no en medio de un envío— es
todo el punto de guardar los scopes concedidos.

La segunda mitad del archivo cubre `designar_remitente`, que es el consumidor de `puede_enviar`
en el camino de ESCRITURA: designar una casilla sin permiso de envío produce una casilla que se
ve configurada y no puede mandar nada.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_Repo` devuelve filas con listas de scopes DISTINTAS entre sí (con envío, sin envío, y
    None). Un fake que devolviera siempre la misma lista no podría distinguir "leyó los scopes"
    de "devolvió un valor fijo".
  · La fila SIN la clave `scopes` (None) está modelada aparte: es literalmente el estado de la
    integración que existe hoy en producción, conectada antes de que la columna existiera.
  · `_Remitente` modela DOS integraciones con su flag, y su `set_remitente` apaga todas antes de
    prender la pedida —el orden real del repo—, y NO prende nada si el usuario no tiene fila.
    Un fake que solo anotara "me llamaron con user_id=X" no podría distinguir "desmarcó la
    anterior y marcó esta" de "marcó esta y dejó dos en true", que es el estado que el índice
    único parcial de la migración 087 prohíbe.
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

from uuid import UUID

import pytest

from repositories.integracion_remitente_repo import IntegracionRemitenteRepo
from services._google_scopes import SCOPE_ENVIO, SCOPE_LECTURA, SCOPES_PEDIDOS, puede_enviar
from services.integracion_service import IntegracionService
from utils.errors import AppError


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


# ── Designar la casilla del sistema ───────────────────────────────────────────

YO = str(UUID(int=1))
OTRO = str(UUID(int=2))
SIN_GOOGLE = str(UUID(int=3))


def _fila(scopes, activo: bool = True, marcada: bool = False) -> dict:
    return {"tipo": "google", "activo": activo, "email_cuenta": "rrhh@k.com",
            "scopes": scopes, "es_remitente_sistema": marcada}


class _RepoPorUsuario:
    """Responde `get_by_user_and_tipo`, que es lo que `designar_remitente` consulta.

    Cada usuario tiene una fila DISTINTA, o ninguna: si todos devolvieran lo mismo, ningún test
    podría desmentir que el service lee la del usuario que se le pidió. Y filtra por `tipo`, así
    que la fila de google no puede colarse como respuesta a otra integración."""

    def __init__(self, filas: dict) -> None:
        self._filas = filas

    def get_by_user_and_tipo(self, user_id, tipo):
        fila = self._filas.get(str(user_id))
        return fila if fila and fila.get("tipo") == tipo else None


class _Remitente:
    """🔴 EL FAKE QUE HACE VERIFICABLE LA OPERACIÓN. Modela DOS integraciones y su flag.

    `set_remitente` reproduce el repo real: apaga TODAS las que estén en true y recién después
    prende la del usuario pedido —el orden que exige el índice único parcial de la 087—, y si
    ese usuario no tiene fila NO prende nada, dejando el sistema sin casilla. Esa última rama es
    justamente el daño que la validación previa del service tiene que impedir; sin modelarla, el
    test de "no se llamó al repo" no tendría ninguna consecuencia que mirar."""

    def __init__(self, marcada=None) -> None:
        self.flags: dict = {YO: False, OTRO: False}
        if marcada:
            self.flags[marcada] = True
        self.llamadas = 0

    def set_remitente(self, user_id) -> None:
        self.llamadas += 1
        for uid in self.flags:
            self.flags[uid] = False
        if str(user_id) in self.flags:
            self.flags[str(user_id)] = True


def _svc(filas: dict, remitente: _Remitente) -> IntegracionService:
    return IntegracionService(repo=_RepoPorUsuario(filas), remitente_repo=remitente)


class TestDesignarRemitente:
    def test_apaga_la_anterior_y_prende_la_nueva(self) -> None:
        """🔴 EL CASO CENTRAL, y se mira el estado de LAS DOS. Para que falle: que el repo
        marcara sin desmarcar (dos en true, lo que la base prohíbe) o que desmarcara sin marcar
        (cero, el sistema sin remitente). Verificar solo la nueva no distinguiría ni uno ni
        otro."""
        rem = _Remitente(marcada=OTRO)
        _svc({YO: _fila([SCOPE_LECTURA, SCOPE_ENVIO])}, rem).designar_remitente(YO)
        assert rem.flags == {YO: True, OTRO: False}

    def test_redesignar_la_que_ya_estaba_la_deja_marcada(self) -> None:
        """El repo desmarca TODAS incluida la propia y la vuelve a prender. Si el orden se
        rompiera, este caso la dejaría apagada: es el que detecta un desmarcado sin marcado."""
        rem = _Remitente(marcada=YO)
        _svc({YO: _fila([SCOPE_ENVIO])}, rem).designar_remitente(YO)
        assert rem.flags[YO] is True

    def test_sin_integracion_de_google_es_404_y_NO_toca_el_remitente(self) -> None:
        """🔴 La razón de ser de la validación previa. Si el service llamara igual al repo, el
        primer UPDATE desmarcaría la casilla vigente, el segundo no matchearía ninguna fila y el
        sistema quedaría SIN remitente — sin excepción y sin rastro. Se afirman las dos cosas:
        que no se llamó, y que la casilla anterior sigue en pie."""
        rem = _Remitente(marcada=OTRO)
        with pytest.raises(AppError) as exc:
            _svc({}, rem).designar_remitente(SIN_GOOGLE)
        assert exc.value.code == "INTEGRACION_NOT_FOUND" and exc.value.status_code == 404
        assert rem.llamadas == 0
        assert rem.flags[OTRO] is True, "se desmarcó la casilla vigente sin poner otra"

    def test_una_integracion_inactiva_tambien_es_404(self) -> None:
        """Existe la fila pero `activo=False`: la desconexión no la borra en todos los caminos.
        Para que falle: que el service chequee solo `if not row`."""
        rem = _Remitente(marcada=OTRO)
        with pytest.raises(AppError) as exc:
            _svc({YO: _fila([SCOPE_ENVIO], activo=False)}, rem).designar_remitente(YO)
        assert exc.value.code == "INTEGRACION_NOT_FOUND"
        assert rem.llamadas == 0

    @pytest.mark.parametrize("scopes", [[SCOPE_LECTURA], None, []],
                             ids=["solo-lectura", "none", "vacio"])
    def test_sin_el_scope_de_envio_es_409_y_NO_toca_el_remitente(self, scopes) -> None:
        """`None` es el estado de la integración que existe HOY en producción, conectada antes
        de que la columna `scopes` existiera. Designarla dejaría una casilla que se ve
        configurada y devuelve 403 en el primer envío. Para que falle: que el service llame a
        `puede_enviar` y descarte el resultado, o que no lo llame."""
        rem = _Remitente(marcada=OTRO)
        with pytest.raises(AppError) as exc:
            _svc({YO: _fila(scopes)}, rem).designar_remitente(YO)
        assert exc.value.code == "SCOPE_ENVIO_FALTANTE" and exc.value.status_code == 409
        assert rem.llamadas == 0
        assert rem.flags[OTRO] is True

    def test_el_orden_es_existencia_y_DESPUES_scope(self) -> None:
        """Una integración que no existe no puede reportar un problema de scope: eso confirmaría
        que la fila está ahí. Para que falle: invertir los dos ifs del service."""
        with pytest.raises(AppError) as exc:
            _svc({}, _Remitente()).designar_remitente(SIN_GOOGLE)
        assert exc.value.code == "INTEGRACION_NOT_FOUND"

    def test_la_respuesta_dice_que_es_la_casilla_del_sistema(self) -> None:
        """Lo que el front necesita para pintar el estado sin volver a pedir la lista. La fila
        de entrada viene con el flag en False: si el service devolviera la fila cruda, esto daría
        False y el test rojearía — por eso la fila NO se construye ya marcada."""
        out = _svc({YO: _fila([SCOPE_ENVIO], marcada=False)},
                   _Remitente()).designar_remitente(YO)
        assert out.es_remitente_sistema is True
        assert out.tipo == "google" and out.connected is True and out.puede_enviar is True
        assert out.email_cuenta == "rrhh@k.com"

    def test_el_service_se_sigue_construyendo_con_un_solo_repo(self) -> None:
        """El repo del remitente entró como SEGUNDO parámetro opcional: los fakes que ya
        existían pasan `repo=` por keyword y no deben romperse. Sin el default, todos los tests
        de arriba fallarían al construir el service."""
        svc = IntegracionService(repo=_Repo([SCOPE_ENVIO]))
        assert isinstance(svc._remitente_repo, IntegracionRemitenteRepo)
