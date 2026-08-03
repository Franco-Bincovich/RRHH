"""
El caché de estado de usuario + el corte por `activo` en el middleware.

El agujero que cierra: `users.activo` existía en el schema y NO lo leía nadie. Dar de baja a
alguien no lo sacaba del sistema — su JWT seguía siendo válido (la firma y el `exp` no saben
nada de una baja) y el middleware solo miraba el rol. El corte tiene que estar en el camino de
cada request, porque no hay nada en el token que se entere.

El caché se prueba con un repo fake que CUENTA sus llamadas, igual que el de empresas: el
requisito no es solo "resuelve bien", es "no dispara una query por request". Un caché correcto
que consultara siempre pasaría cualquier test de comportamiento y no serviría para nada.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El repo fake devuelve una fila MUTABLE que el test cambia entre llamadas (rol y activo), y un
contador. Si devolviera una constante, "reactivarlo lo devuelve a la normalidad" y "la baja
rige" pasarían las dos sin que el caché leyera nada — estarían afirmando sobre la constante del
propio test. Y `_RepoQueFalla` es lo único que puede desmentir el fail-closed: sin él, la rama
del except no se ejecuta nunca.
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
from uuid import uuid4

import httpx
import pytest

import middleware.auth as auth_mod
import utils.usuario_estado as estado_mod
from main import app
from utils._sesion_inactividad import sesion_expirada
from utils.usuario_estado import DENEGADO, EstadoUsuario, _UsuarioEstadoCache

UID = str(uuid4())


def _hace(**delta) -> str:
    """Timestamp ISO de hace tanto tiempo, en el formato en que lo devuelve PostgREST."""
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat()


class _RepoContador:
    """Repo fake con fila mutable + contador. El punto del caché es que el contador NO suba.

    Modela `ultimo_acceso` como lo que es —una columna que se LEE y se ESCRIBE— y cuenta las
    escrituras aparte: sin ese contador, "el throttle no escribe en cada request" no tendría
    nada que mirar y pasaría con el throttle borrado.
    """

    def __init__(self, *, rol: str | None = "admin_rrhh", activo: bool = True,
                 ultimo_acceso: str | None = None) -> None:
        self.fila: dict | None = {"rol": rol, "activo": activo, "ultimo_acceso": ultimo_acceso}
        self.llamadas = 0
        self.escrituras = 0

    def get_estado(self, user_id: str) -> dict | None:
        self.llamadas += 1
        return dict(self.fila) if self.fila is not None else None

    def tocar_ultimo_acceso(self, user_id: str) -> str:
        self.escrituras += 1
        sello = datetime.now(timezone.utc).isoformat()
        if self.fila is not None:
            self.fila["ultimo_acceso"] = sello
        return sello


class _RepoQueFalla:
    def __init__(self) -> None:
        self.llamadas = 0

    def get_estado(self, user_id: str) -> dict | None:
        self.llamadas += 1
        raise RuntimeError("base no disponible")

    def tocar_ultimo_acceso(self, user_id: str) -> str:
        raise RuntimeError("base no disponible")


def _vencer(cache: _UsuarioEstadoCache, user_id: str) -> None:
    """Envejece la entrada más allá del TTL sin dormir el test."""
    estado, cargado_en = cache._entradas[user_id]
    cache._entradas[user_id] = (estado, cargado_en - estado_mod._TTL_SEGUNDOS - 1)


# ─── El caché ─────────────────────────────────────────────────────────────────


class TestCache:
    def test_construir_no_toca_la_base(self) -> None:
        """Carga perezosa, como el PyJWKClient: el cold start no paga la query."""
        repo = _RepoContador()
        _UsuarioEstadoCache(repo=repo)
        assert repo.llamadas == 0

    def test_primera_consulta_carga(self) -> None:
        repo = _RepoContador()
        assert _UsuarioEstadoCache(repo=repo).estado(UID).rol == "admin_rrhh"
        assert repo.llamadas == 1

    def test_no_dispara_una_query_por_request(self) -> None:
        """El requisito central: 50 requests consecutivos = 1 sola query."""
        repo = _RepoContador()
        c = _UsuarioEstadoCache(repo=repo)
        for _ in range(50):
            assert c.estado(UID).rol == "admin_rrhh"
        assert repo.llamadas == 1

    def test_usuarios_distintos_no_comparten_entrada(self) -> None:
        """Cachear por proceso una sola entrada le daría a todos el rol del primero."""
        repo = _RepoContador(rol="admin_rrhh")
        c = _UsuarioEstadoCache(repo=repo)
        assert c.estado(UID).rol == "admin_rrhh"
        repo.fila = {"rol": "mandos_medios", "activo": True}
        assert c.estado(str(uuid4())).rol == "mandos_medios"

    def test_ttl_vencido_relee(self) -> None:
        repo = _RepoContador()
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        _vencer(c, UID)
        c.estado(UID)
        assert repo.llamadas == 2

    def test_usuario_inexistente_da_denegado(self) -> None:
        """Sin fila no hay rol que asumir: rol=None hace que permisos.py niegue todo."""
        repo = _RepoContador()
        repo.fila = None
        estado = _UsuarioEstadoCache(repo=repo).estado(UID)
        assert estado.rol is None and estado.activo is False

    def test_invalidar_fuerza_una_relectura(self) -> None:
        repo = _RepoContador()
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        c.invalidar(UID)
        c.estado(UID)
        assert repo.llamadas == 2

    def test_invalidar_un_usuario_no_toca_a_los_demas(self) -> None:
        repo = _RepoContador()
        c = _UsuarioEstadoCache(repo=repo)
        otro = str(uuid4())
        c.estado(UID)
        c.estado(otro)
        c.invalidar(UID)
        c.estado(otro)
        assert repo.llamadas == 2  # el otro sigue cacheado


class TestActivo:
    def test_usuario_activo_pasa(self) -> None:
        assert _UsuarioEstadoCache(repo=_RepoContador(activo=True)).estado(UID).activo is True

    def test_usuario_inactivo_queda_marcado_y_resuelto(self) -> None:
        """`resuelto=True` es lo que distingue "lo dieron de baja" de "no pude leer la fila"."""
        estado = _UsuarioEstadoCache(repo=_RepoContador(activo=False)).estado(UID)
        assert estado.activo is False and estado.resuelto is True

    def test_la_baja_rige_al_vencer_el_ttl(self) -> None:
        repo = _RepoContador(activo=True)
        c = _UsuarioEstadoCache(repo=repo)
        assert c.estado(UID).activo is True
        repo.fila = {"rol": "admin_rrhh", "activo": False}   # lo dan de baja
        _vencer(c, UID)
        assert c.estado(UID).activo is False

    def test_reactivarlo_lo_devuelve_a_la_normalidad(self) -> None:
        """La baja es reversible: `activo=true` (+ ban "none" en Auth) y vuelve a entrar."""
        repo = _RepoContador(activo=False)
        c = _UsuarioEstadoCache(repo=repo)
        assert c.estado(UID).activo is False
        repo.fila = {"rol": "admin_rrhh", "activo": True}
        c.invalidar(UID)
        estado = c.estado(UID)
        assert estado.activo is True and estado.rol == "admin_rrhh"


class TestFailClosed:
    def test_si_no_puede_resolver_niega(self) -> None:
        """Al revés que empresas_cache: acá no hay nada que ensanchar, el rol ES la autorización."""
        assert _UsuarioEstadoCache(repo=_RepoQueFalla()).estado(UID) == DENEGADO

    def test_el_denegado_no_finge_ser_una_baja(self) -> None:
        """`resuelto=False`: un blip de base no puede decirle al usuario que lo dieron de baja."""
        assert _UsuarioEstadoCache(repo=_RepoQueFalla()).estado(UID).resuelto is False

    def test_loguea_a_error(self, caplog) -> None:
        with caplog.at_level("ERROR"):
            _UsuarioEstadoCache(repo=_RepoQueFalla()).estado(UID)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_el_fallo_no_se_cachea(self) -> None:
        """Cachear el fallo convertiría un blip de 1s en 60s de gente afuera."""
        repo = _RepoQueFalla()
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        c.estado(UID)
        assert repo.llamadas == 2

    def test_se_recupera_solo_cuando_la_base_vuelve(self) -> None:
        c = _UsuarioEstadoCache(repo=_RepoQueFalla())
        assert c.estado(UID) == DENEGADO
        c._repo = _RepoContador()
        assert c.estado(UID).rol == "admin_rrhh"

    def test_una_entrada_vencida_no_sobrevive_a_un_fallo(self) -> None:
        """Servir lo último bueno sería fail-OPEN: alguien recién dado de baja seguiría
        entrando mientras dure el incidente. Es la diferencia deliberada con empresas_cache,
        donde conservar el set viejo SÍ es lo correcto."""
        c = _UsuarioEstadoCache(repo=_RepoContador())
        c.estado(UID)
        _vencer(c, UID)
        c._repo = _RepoQueFalla()
        assert c.estado(UID) == DENEGADO


class TestInactividad:
    """8 horas sin un solo request y la sesión deja de valer."""

    def _estado(self, ultimo_acceso: str | None) -> EstadoUsuario:
        return _UsuarioEstadoCache(repo=_RepoContador(ultimo_acceso=ultimo_acceso)).estado(UID)

    def test_7h59_todavia_pasa(self) -> None:
        assert sesion_expirada(self._estado(_hace(hours=7, minutes=59))) is False

    def test_8h01_ya_no(self) -> None:
        assert sesion_expirada(self._estado(_hace(hours=8, minutes=1))) is True

    def test_actividad_reciente_pasa(self) -> None:
        assert sesion_expirada(self._estado(_hace(minutes=3))) is False

    def test_null_no_vence(self) -> None:
        """🔴 Hoy TODAS las filas de producción tienen ultimo_acceso en NULL (la columna estaba
        muerta). Si el NULL venciera, el deploy dejaría afuera al equipo entero."""
        assert sesion_expirada(self._estado(None)) is False

    def test_una_fecha_ilegible_no_vence_ni_rompe(self) -> None:
        """Preferible dejar pasar a tumbar el request de alguien por un formato raro."""
        assert sesion_expirada(self._estado("no-es-una-fecha")) is False

    def test_un_estado_sin_resolver_no_se_reporta_como_vencido(self) -> None:
        """El blip de base ya se niega por otro camino; que no se mezcle con la inactividad."""
        assert sesion_expirada(DENEGADO) is False

    def test_una_fecha_sin_zona_no_rompe_la_comparacion(self) -> None:
        """Comparar naive con aware LANZA: se asume UTC en vez de tumbar el request."""
        naive = (datetime.now(timezone.utc) - timedelta(hours=9)).replace(tzinfo=None).isoformat()
        assert sesion_expirada(self._estado(naive)) is True


class TestThrottleDeEscritura:
    def test_no_escribe_en_cada_request(self) -> None:
        """El requisito: 100 requests seguidos no son 100 UPDATE."""
        repo = _RepoContador(ultimo_acceso=_hace(minutes=1))
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        for _ in range(100):
            c.registrar_actividad(UID)
        assert repo.escrituras == 0

    def test_sella_cuando_el_valor_ya_esta_viejo(self) -> None:
        repo = _RepoContador(ultimo_acceso=_hace(minutes=30))
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        c.registrar_actividad(UID)
        assert repo.escrituras == 1

    def test_una_sola_escritura_por_ventana(self) -> None:
        """Tras sellar, los siguientes requests vuelven a caer dentro del throttle."""
        repo = _RepoContador(ultimo_acceso=_hace(minutes=30))
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        for _ in range(50):
            c.registrar_actividad(UID)
        assert repo.escrituras == 1

    def test_null_se_sella_la_primera_vez(self) -> None:
        """Es lo que saca a las filas de producción del NULL sin ninguna migración."""
        repo = _RepoContador(ultimo_acceso=None)
        c = _UsuarioEstadoCache(repo=repo)
        c.estado(UID)
        c.registrar_actividad(UID)
        assert repo.escrituras == 1

    def test_el_sello_queda_en_memoria_sin_releer(self) -> None:
        """Si no actualizara su copia, el chequeo de inactividad seguiría viendo el valor viejo
        hasta que venza el TTL — y con un valor de hace 9h eso es un 401 con la sesión recién
        sellada."""
        repo = _RepoContador(ultimo_acceso=_hace(hours=9))
        c = _UsuarioEstadoCache(repo=repo)
        assert sesion_expirada(c.estado(UID)) is True
        c.registrar_actividad(UID)
        assert sesion_expirada(c._entradas[UID][0]) is False
        assert repo.llamadas == 1  # sin releer

    def test_un_fallo_de_escritura_no_rompe_nada(self) -> None:
        c = _UsuarioEstadoCache(repo=_RepoContador(ultimo_acceso=_hace(hours=1)))
        c.estado(UID)
        c._repo = _RepoQueFalla()
        c.registrar_actividad(UID)  # no lanza

    def test_sin_entrada_no_escribe(self) -> None:
        """Nadie selló nunca a alguien que no pasó por `estado()` en este proceso."""
        repo = _RepoContador()
        _UsuarioEstadoCache(repo=repo).registrar_actividad(UID)
        assert repo.escrituras == 0


# ─── Un escalón más abajo: lo que viaja EN LA QUERY ───────────────────────────


class TestLaQueryTraeLosDosCampos:
    """🔴 EL REPO FAKE NO ALCANZA PARA ESTO, y es justo lo que sostiene el corte.

    Todos los tests de arriba reemplazan el repo entero, así que el `select` real nunca corre:
    sacarle `activo` deja el caché leyendo un campo que no viene, `bool(None)` da False y **el
    sistema entero queda afuera**; sacarle `ultimo_acceso` apaga la inactividad entera en
    silencio (None nunca vence) — con los tests de arriba en verde, porque su fake devuelve el
    diccionario que ellos mismos escribieron. Acá se faltea el cliente de Supabase y se mira la
    query, que es donde vive el "misma fila, misma query: costo 0".
    """

    def _repo_con_espia(self, monkeypatch):
        import repositories.usuario_repo as mod

        columnas: list[str] = []

        class _Q:
            def select(self, cols, *a, **k):
                columnas.append(cols)
                return self

            def eq(self, col, val):
                return self

            def limit(self, n):
                return self

            def execute(self):
                return type("R", (), {"data": [{"rol": "admin_rrhh", "activo": True, "ultimo_acceso": None}]})()

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.UsuarioRepo(), columnas

    def test_el_select_pide_los_tres_campos(self, monkeypatch) -> None:
        repo, columnas = self._repo_con_espia(monkeypatch)
        repo.get_estado(UID)
        assert columnas == ["rol, activo, ultimo_acceso"]

    def test_es_una_sola_query(self, monkeypatch) -> None:
        """El argumento de "leer activo no cuesta nada" solo vale si es la MISMA query."""
        repo, columnas = self._repo_con_espia(monkeypatch)
        repo.get_estado(UID)
        assert len(columnas) == 1


# ─── El middleware ────────────────────────────────────────────────────────────

_TRANSPORT = httpx.ASGITransport(app=app)
_RUTA = "/api/auditoria"  # gateada con AUDITORIA + READ; el gate corre antes del handler


@pytest.fixture
def sesion_valida(monkeypatch):
    """Da por bueno el JWT (la firma se prueba aparte) y deja fijar el estado del usuario.

    `registrar_actividad` se falsea para que el middleware no toque la base en un test, y
    de paso queda registrado quién fue sellado: eso es lo que permite afirmar que una sesión
    vencida NO se sella (si se sellara, no vencería nunca)."""
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: UID)
    sellados: list[str] = []
    monkeypatch.setattr(auth_mod, "registrar_actividad", sellados.append)

    def _con(estado: EstadoUsuario) -> list[str]:
        monkeypatch.setattr(auth_mod, "estado_usuario", lambda user_id: estado)
        return sellados
    return _con


async def _get() -> httpx.Response:
    async with httpx.AsyncClient(transport=_TRANSPORT, base_url="http://test") as c:
        return await c.get(_RUTA, headers={"Authorization": "Bearer token-valido"})


class TestMiddlewareCortaPorActivo:
    async def test_usuario_inactivo_recibe_403(self, sesion_valida) -> None:
        sesion_valida(EstadoUsuario(rol="admin_rrhh", activo=False))
        assert (await _get()).status_code == 403

    async def test_con_codigo_propio_para_que_el_front_mande_a_login(self, sesion_valida) -> None:
        sesion_valida(EstadoUsuario(rol="admin_rrhh", activo=False))
        assert (await _get()).json()["code"] == "USUARIO_INACTIVO"

    async def test_el_rol_no_lo_salva(self, sesion_valida) -> None:
        """admin_rrhh es el rol que puede todo: si `activo` no rigiera, esto daría 200."""
        sesion_valida(EstadoUsuario(rol="admin_rrhh", activo=False))
        assert (await _get()).status_code == 403

    async def test_reactivado_vuelve_a_pasar_el_middleware(self, sesion_valida) -> None:
        """Con activo=True el middleware NO corta: el 403 que queda es el del gate de rol
        (rol=None → FORBIDDEN), que es otro código. Lo que se afirma es que ya no es la baja."""
        sesion_valida(EstadoUsuario(rol=None, activo=True))
        assert (await _get()).json()["code"] == "FORBIDDEN"

    async def test_un_blip_de_base_no_se_reporta_como_baja(self, sesion_valida) -> None:
        """DENEGADO tiene activo=False, pero resuelto=False: no puede salir por USUARIO_INACTIVO."""
        sesion_valida(DENEGADO)
        resp = await _get()
        assert resp.status_code == 403 and resp.json()["code"] == "FORBIDDEN"


class TestMiddlewareCortaPorInactividad:
    def _viejo(self, **delta) -> EstadoUsuario:
        return EstadoUsuario(rol="admin_rrhh", activo=True,
                             ultimo_acceso=datetime.now(timezone.utc) - timedelta(**delta))

    async def test_8h01_recibe_401(self, sesion_valida) -> None:
        sesion_valida(self._viejo(hours=8, minutes=1))
        resp = await _get()
        assert resp.status_code == 401 and resp.json()["code"] == "SESION_EXPIRADA"

    async def test_7h59_pasa_el_middleware(self, sesion_valida) -> None:
        """El 403 que queda es el del gate de rol, no el corte por inactividad."""
        sesion_valida(EstadoUsuario(rol=None, activo=True,
                                    ultimo_acceso=datetime.now(timezone.utc) - timedelta(hours=7, minutes=59)))
        assert (await _get()).status_code == 403

    async def test_una_sesion_vencida_NO_se_sella(self, sesion_valida) -> None:
        """🔴 El orden del middleware: si sellara antes de chequear, este mismo request
        renovaría el reloj y la sesión no vencería jamás."""
        sellados = sesion_valida(self._viejo(hours=9))
        await _get()
        assert sellados == []

    async def test_un_request_valido_si_sella(self, sesion_valida) -> None:
        """rol=None a propósito: el sellado ocurre en el middleware, ANTES del gate de rol, así
        que el request muere en el 403 y el test no necesita que el handler toque la base."""
        sellados = sesion_valida(EstadoUsuario(rol=None, activo=True,
                                               ultimo_acceso=datetime.now(timezone.utc) - timedelta(minutes=10)))
        await _get()
        assert sellados == [UID]
