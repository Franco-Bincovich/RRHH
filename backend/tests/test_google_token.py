"""
El access_token de Google: los TRES BUGS del refresh, uno por uno — sin red.

Los tres estaban rotos en producción para la lectura de candidatos, y se vuelven caros con el
envío de mails (el token se pide por cada mail de un lote). Ver el encabezado de
`services/_google_token.py`.

  1. El token renovado no se persistía → cada request post-vencimiento pagaba un round-trip.
  2. `token_expiry` NULL salteaba el refresh → Gmail 401 envuelto en un 502 engañoso.
  3. `except (ValueError, TypeError): pass` devolvía el token viejo EN SILENCIO.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_Repo` CUENTA las llamadas a `actualizar_token` y guarda lo que recibe. Un fake que solo
    aceptara el método sin registrar nada no podría desmentir el bug 1: el test pasaría con la
    persistencia puesta o sacada.
  · `_HttpFalso` CUENTA los POST al endpoint de token. Es lo único que distingue "no renovó"
    de "renovó y devolvió lo mismo" — sin ese contador, los bugs 2 y 3 son indistinguibles de
    un token que casualmente seguía sirviendo.
  · El token guardado y el renovado son strings DISTINTOS ("viejo" vs "nuevo"): si fueran el
    mismo, ningún test podría decir cuál se devolvió.
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

from datetime import datetime, timedelta, timezone

import pytest

import services._google_token as mod
from utils.errors import AppError

USER = "user-1"
VIEJO, NUEVO = "token-viejo", "token-nuevo"


def _ahora(delta_seg: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seg)).isoformat()


class _Repo:
    """Integración fake. REGISTRA los `actualizar_token` — es lo que hace medible el bug 1."""

    def __init__(self, fila) -> None:
        self._fila = fila
        self.persistidos: list = []

    def get_by_user_and_tipo(self, user_id, tipo):
        return self._fila

    def actualizar_token(self, user_id, access_token, token_expiry):
        self.persistidos.append((user_id, access_token, token_expiry))


class _RechazoDeGoogle(Exception):
    """Lo que levanta `raise_for_status()` de httpx: la RESPUESTA viaja adentro de la excepción.

    🔴 ANTES ERA UN `RuntimeError` PELADO, y eso alcanzaba mientras todos los fallos de
    renovación salían con el mismo código. Desde que `_google_token_fallo` distingue "Google
    rechazó la credencial" (hay respuesta HTTP, 4xx) de "no se pudo hablar con Google" (no hay
    respuesta), un fake sin `.response` **colapsa los dos casos en el segundo**: el test que dice
    probar el permiso revocado pasaría igual con la clasificación entera borrada.
    `error_de_renovacion` lee el atributo por duck-typing, así que el fake modela exactamente eso.
    """

    def __init__(self, response) -> None:
        super().__init__("400 Bad Request")
        self.response = response


class _Resp:
    def __init__(self, datos: dict, ok: bool = True, status_code: int = 400) -> None:
        self._datos, self._ok, self.status_code = datos, ok, status_code

    def raise_for_status(self):
        if not self._ok:
            raise _RechazoDeGoogle(self)

    def json(self):
        return self._datos


class _HttpFalso:
    """Cliente httpx fake. CUENTA los POST: sin eso no se puede distinguir "no renovó"."""

    def __init__(self, datos: dict, ok: bool = True, status: int = 400, explota=None) -> None:
        self._datos, self._ok, self._status, self._explota = datos, ok, status, explota
        self.posts = 0

    def __call__(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, data=None):
        self.posts += 1
        if self._explota is not None:
            raise self._explota  # no hubo respuesta: timeout, DNS, conexión cortada
        return _Resp(self._datos, self._ok, self._status)


def _fila(expiry, access=VIEJO, refresh="refresh-1") -> dict:
    return {"access_token": access, "refresh_token": refresh, "token_expiry": expiry}


def _armar(monkeypatch, fila, *, datos=None, ok=True, status=400, explota=None):
    http = _HttpFalso(datos if datos is not None else {"access_token": NUEVO, "expires_in": 3600},
                      ok, status, explota)
    monkeypatch.setattr(mod.httpx, "Client", http)
    return _Repo(fila), http


# ── El camino feliz: token vigente, no se toca nada ───────────────────────────

def test_token_vigente_no_renueva_ni_persiste(monkeypatch) -> None:
    """El contrapeso de todo el archivo: si esto fallara, estaríamos renovando siempre."""
    repo, http = _armar(monkeypatch, _fila(_ahora(3600)))
    assert mod.access_token_valido(repo, USER) == VIEJO
    assert http.posts == 0 and repo.persistidos == []


# ── 🔴 BUG 1: el token renovado no se persistía ───────────────────────────────

class TestBug1ElTokenRenovadoSePersiste:
    def test_se_guarda_el_token_nuevo(self, monkeypatch) -> None:
        """Para que falle: borrar la llamada a `_persistir` en `_renovar`."""
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)))
        assert mod.access_token_valido(repo, USER) == NUEVO
        assert len(repo.persistidos) == 1
        assert repo.persistidos[0][0] == USER and repo.persistidos[0][1] == NUEVO

    def test_se_guarda_tambien_el_vencimiento_nuevo(self, monkeypatch) -> None:
        """Sin el `token_expiry` nuevo, la fila quedaría vencida para siempre y el ahorro del
        round-trip no existiría: es la mitad del bug, no un extra."""
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)))
        mod.access_token_valido(repo, USER)
        vence = datetime.fromisoformat(repo.persistidos[0][2])
        assert vence > datetime.now(timezone.utc) + timedelta(minutes=50)

    def test_sin_expires_in_se_guarda_el_token_con_vencimiento_nulo(self, monkeypatch) -> None:
        """Google siempre manda `expires_in`, pero si faltara igual conviene guardar el token:
        NULL vuelve a caer en el camino de "no se sabe" → se renueva. Degrada, no rompe."""
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)), datos={"access_token": NUEVO})
        assert mod.access_token_valido(repo, USER) == NUEVO
        assert repo.persistidos[0][2] is None

    def test_si_la_persistencia_falla_el_token_igual_se_devuelve(self, monkeypatch) -> None:
        """Best-effort: quien llama ya tiene el token. Un fallo acá degrada al comportamiento
        viejo (pagar el round-trip la próxima), que es el peor caso aceptable."""
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)))

        def _explota(*a, **k):
            raise RuntimeError("la columna no existe")

        repo.actualizar_token = _explota
        assert mod.access_token_valido(repo, USER) == NUEVO


# ── 🔴 BUG 2: token_expiry NULL salteaba el refresh ───────────────────────────

@pytest.mark.parametrize("vacio", [None, ""], ids=["null", "vacio"])
def test_bug2_sin_vencimiento_guardado_SE_RENUEVA(monkeypatch, vacio) -> None:
    """Antes se devolvía el token tal cual → Gmail 401 → envuelto en un 502 que decía "error al
    consultar Gmail" cuando el problema era "tu sesión venció".

    Para que falle: volver a poner el `if expiry_str:` como única puerta al refresh."""
    repo, http = _armar(monkeypatch, _fila(vacio))
    assert mod.access_token_valido(repo, USER) == NUEVO
    assert http.posts == 1


# ── 🔴 BUG 3: expiry ilegible devolvía el token viejo en silencio ─────────────

class TestBug3NadaSeTragaEnSilencio:
    @pytest.mark.parametrize("basura", ["no-es-una-fecha", "2026-13-45", "{}"],
                             ids=["texto", "fecha-imposible", "json"])
    def test_un_expiry_ilegible_RENUEVA_en_vez_de_seguir(self, monkeypatch, basura) -> None:
        """Para que falle: reponer el `except (ValueError, TypeError): pass`."""
        repo, http = _armar(monkeypatch, _fila(basura))
        assert mod.access_token_valido(repo, USER) == NUEVO
        assert http.posts == 1

    def test_un_expiry_NAIVE_se_asume_UTC_y_no_explota(self, monkeypatch) -> None:
        """Era la rama que hacía saltar el TypeError. No se rechaza —se asume UTC, que es como lo
        escribe `procesar_callback`—: rechazarlo forzaría un refresh eterno."""
        naive = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None).isoformat()
        repo, http = _armar(monkeypatch, _fila(naive))
        assert mod.access_token_valido(repo, USER) == VIEJO   # vigente: no renueva
        assert http.posts == 0

    def test_un_naive_VENCIDO_si_renueva(self, monkeypatch) -> None:
        """El contrapeso: asumir UTC no puede volver eterno a un token naive ya vencido."""
        naive = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
        repo, http = _armar(monkeypatch, _fila(naive))
        assert mod.access_token_valido(repo, USER) == NUEVO and http.posts == 1


# ── El margen de renovación anticipada ────────────────────────────────────────

def test_un_token_a_punto_de_vencer_se_renueva_antes(monkeypatch) -> None:
    """Un token con 20 s de vida pasa el chequeo y se muere a mitad del trabajo — y el envío
    masivo dura minutos. Se renueva un minuto antes del vencimiento real."""
    repo, http = _armar(monkeypatch, _fila(_ahora(20)))
    assert mod.access_token_valido(repo, USER) == NUEVO and http.posts == 1


# ── Los errores siguen siendo ruidosos y con el código correcto ───────────────

class TestLosErroresNoCambiaron:
    def test_sin_integracion_es_not_configured(self, monkeypatch) -> None:
        repo, _ = _armar(monkeypatch, None)
        with pytest.raises(AppError) as exc:
            mod.access_token_valido(repo, USER)
        assert exc.value.code == "GMAIL_NOT_CONFIGURED" and exc.value.status_code == 400

    def test_sin_refresh_token_es_not_configured(self, monkeypatch) -> None:
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10), refresh=None))
        with pytest.raises(AppError) as exc:
            mod.access_token_valido(repo, USER)
        assert exc.value.code == "GMAIL_NOT_CONFIGURED"

    def test_refresh_revocado_es_502_ruidoso(self, monkeypatch) -> None:
        """🔴 ESTE TEST SE LLAMABA `..._es_401_ruidoso` Y FIJABA EL 401 COMO CONTRATO. Dado
        vuelta en su lugar el 23/8/2026, con el porqué acá y no en el mensaje del commit.

        **"Ruidoso" era lo correcto y sigue rigiendo**: el caso real —el permiso revocado desde
        la cuenta de Google— tiene que salir con código propio y mensaje propio, nunca un 500 ni
        un silencio. Eso no cambió.

        **El 401 era lo equivocado, y costó caro.** Un 401 dice "VOS no estás autenticado", y acá
        el usuario lo está: quien no puede autenticarse es este backend contra Google. El
        interceptor del front leía el status y solo el status, así que este 401 llegaba a
        `/vacantes` —que pide los mails pendientes al montar— y **deslogueaba a un usuario
        perfectamente autenticado, en cada carga de la pantalla**, durante los once días que el
        token de la casilla estuvo vencido.

        La lección, para que no vuelva: **un status HTTP no es solo un número para el test que lo
        assertea; es una instrucción para todo cliente que lo reciba.** Elegir 401 para "una
        integración se cayó" le dice al front algo falso sobre la sesión del usuario.
        """
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)), ok=False)
        with pytest.raises(AppError) as exc:
            mod.access_token_valido(repo, USER)
        assert exc.value.code == "GMAIL_TOKEN_EXPIRED" and exc.value.status_code == 502

    def test_sin_contacto_con_google_es_el_OTRO_502(self, monkeypatch) -> None:
        """Un timeout no es un permiso revocado: reconectar la cuenta no arregla nada y decirle
        a RRHH que la reconecte lo manda a rehacer una integración que estaba bien."""
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)), explota=TimeoutError("se cortó"))
        with pytest.raises(AppError) as exc:
            mod.access_token_valido(repo, USER)
        assert exc.value.code == "GMAIL_RENOVACION_FALLIDA" and exc.value.status_code == 502

    def test_una_respuesta_sin_access_token_no_es_un_KeyError(self, monkeypatch) -> None:
        """No puede salir un KeyError crudo: el contrato de errores del repo es AppError.

        Sale por el code TRANSITORIO y no por el de revocado, a propósito: Google contestó y no
        rechazó nada, así que afirmar "te revocaron el permiso" sería inventar un diagnóstico.
        """
        repo, _ = _armar(monkeypatch, _fila(_ahora(-10)), datos={"error": "invalid_grant"})
        with pytest.raises(AppError) as exc:
            mod.access_token_valido(repo, USER)
        assert exc.value.code == "GMAIL_RENOVACION_FALLIDA" and exc.value.status_code == 502

    def test_ningun_fallo_de_renovacion_sale_401(self, monkeypatch) -> None:
        """🔴 El invariante que cierra el bug, dicho de una: NINGUNA de las formas de fallar acá
        puede volver a emitir un 401. Es lo que el front no puede distinguir de "tu sesión
        venció". Barre los tres caminos; agregar un cuarto sin pensarlo rojea acá."""
        caminos = [
            {"ok": False},                                  # Google rechazó
            {"explota": TimeoutError("se cortó")},           # no hubo respuesta
            {"datos": {"sin": "token"}},                     # respuesta sin access_token
        ]
        for kwargs in caminos:
            repo, _ = _armar(monkeypatch, _fila(_ahora(-10)), **kwargs)
            with pytest.raises(AppError) as exc:
                mod.access_token_valido(repo, USER)
            assert exc.value.status_code != 401, f"{kwargs} volvió a emitir un 401"
