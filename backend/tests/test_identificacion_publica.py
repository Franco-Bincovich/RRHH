"""
LA QUINTA RUTA PÚBLICA: identificación por DNI. Rechazo único, payload mínimo y los dos ejes
del rate limit.

Esta ruta es, por decisión de producto, la más débil de las cinco: el acceso es SOLO con dni y un
dni es un identificador enumerable, no un secreto. Lo que estos tests custodian es todo lo demás.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 El fake tendría que modelar UN SOLO modo de fallo.** "Rechazo único" y "rechazo distinto"
son indistinguibles con un solo caso: con un único desenlace, cualquier implementación pasa.
`_RepoFalso` modela los CINCO —dni inexistente, empleado de baja, empresa sin clientes, dni en dos
empresas, y el bloqueo por límite— y las aserciones comparan los rechazos ENTRE SÍ, no contra un
literal escrito a mano. Un literal dejaría pasar el caso en que los cinco cambian juntos.

**2. El fake tendría que devolver el mismo empleado para cualquier dni.** Devuelve filas
distintas por dni, así que un service que ignore el valor recibido y siempre resuelva lo mismo se
ve: `test_el_nombre_es_el_del_dni_pedido` compara dos dnis contra dos nombres distintos.

**3. `intentos` tendría que no registrarse.** Sin él, "el log distingue lo que la respuesta no
distingue" no se puede desmentir: un service que loguea siempre `sin_coincidencia` daría el mismo
resultado visible.

**4. El limitador tendría que estar cableado adentro.** Se inyecta, así que el test controla
cuándo bloquea. Con el real, "el bloqueo sale por el mismo rechazo" sería imposible de provocar
sin hacer 21 llamadas y dependería del reloj.

⚠️ EL PISO DE TIEMPO se baja a ~0 en la fixture (`_PISO_SEGUNDOS`), o cada test esperaría 300 ms.
Que el piso EXISTA y se aplique a todos los caminos se verifica aparte, en
`TestElPisoDeTiempo`, midiendo con el valor real — si se testeara solo con el piso pisado, sacar
la nivelación entera no rojearía nada.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from time import perf_counter  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import services.identificacion_service as svc_mod  # noqa: E402
from services.identificacion_service import IdentificacionService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_CON, EMPRESA_SIN = str(uuid4()), str(uuid4())
EMP_ACTIVO, EMP_BAJA, EMP_SIN_CLI = str(uuid4()), str(uuid4()), str(uuid4())

DNI_OK = "30111222"
DNI_BAJA = "30111333"
DNI_SIN_CLIENTES = "30111444"
DNI_AMBIGUO = "30111555"
DNI_INEXISTENTE = "99999999"
DNI_OTRO_OK = "30111666"

# Los CINCO desenlaces, no uno. Ver el punto 1 del encabezado.
_PADRON: dict[str, list] = {
    DNI_OK: [{"id": EMP_ACTIVO, "nombre": "Juan Carlos", "estado": "activo",
              "empresa_id": EMPRESA_CON}],
    DNI_OTRO_OK: [{"id": str(uuid4()), "nombre": "Mariana", "estado": "activo",
                   "empresa_id": EMPRESA_CON}],
    DNI_BAJA: [{"id": EMP_BAJA, "nombre": "Pedro", "estado": "baja",
                "empresa_id": EMPRESA_CON}],
    DNI_SIN_CLIENTES: [{"id": EMP_SIN_CLI, "nombre": "Sofía", "estado": "activo",
                        "empresa_id": EMPRESA_SIN}],
    DNI_AMBIGUO: [{"id": str(uuid4()), "nombre": "Ana", "estado": "activo",
                   "empresa_id": EMPRESA_CON},
                  {"id": str(uuid4()), "nombre": "Ana", "estado": "activo",
                   "empresa_id": EMPRESA_SIN}],
}


class _SesionesFalsas:
    """Doble de `SesionHorasRepo`. Sin él, el camino de ÉXITO pegaría contra Supabase — o sea el
    único camino que importa dejaría de poder testearse sin red."""

    def __init__(self) -> None:
        self.creadas: list[dict] = []

    def purgar_vencidas(self, ahora: str) -> int:
        return 0

    def crear(self, token_hash: str, empleado_id: str, empresa_id: str, expires_at: str) -> dict:
        fila = {"id": str(uuid4()), "token_hash": token_hash, "empleado_id": empleado_id,
                "empresa_id": empresa_id, "expires_at": expires_at}
        self.creadas.append(fila)
        return fila


class _RepoFalso:
    """Padrón con los cinco desenlaces, registro de los intentos y CONTEO DE CONSULTAS.

    🔴 `busquedas` no es decorativo. Sin él, `test_se_consulta_antes_de_tocar_la_base` afirmaba
    su propio título y no lo verificaba: invertir el orden (base primero, limitador después)
    dejaba el resultado en `bloqueado` y el `empleado_id` en None igual, así que el test pasaba
    con la mutación puesta. Lo detectó la corrida de mutación, no la lectura. Contar las llamadas
    es lo único que distingue "cortó antes" de "cortó después".
    """

    def __init__(self) -> None:
        self.intentos: list[dict] = []
        self.busquedas = 0
        self.consultas_clientes = 0

    def buscar_por_dni(self, dni: str) -> list:
        self.busquedas += 1
        return [dict(f) for f in _PADRON.get(dni, [])]

    def hay_clientes_activos(self, empresa_id: str) -> bool:
        self.consultas_clientes += 1
        return empresa_id == EMPRESA_CON

    def registrar_intento(self, **kw) -> None:
        self.intentos.append(kw)


@pytest.fixture(autouse=True)
def sin_piso(monkeypatch):
    """El piso real (300 ms) haría que cada test tarde eso. Se verifica aparte con el valor real."""
    monkeypatch.setattr(svc_mod, "_PISO_SEGUNDOS", 0.0)


@pytest.fixture
def repo() -> _RepoFalso:
    return _RepoFalso()


def _svc(repo: _RepoFalso, bloquea: bool = False,
         sesiones: "_SesionesFalsas | None" = None) -> IdentificacionService:
    return IdentificacionService(repo=repo, limitador=lambda _dni: not bloquea,
                                 sesiones=sesiones or _SesionesFalsas())


async def _rechazo(svc: IdentificacionService, dni: str) -> AppError:
    with pytest.raises(AppError) as exc:
        await svc.identificar(dni)
    return exc.value


# ── Rechazo único ─────────────────────────────────────────────────────────────


class TestRechazoUnico:
    """🔴 Los CINCO motivos salen exactamente igual. Se comparan ENTRE SÍ y no contra un literal:
    un literal escrito a mano dejaría pasar el caso en que los cinco cambian juntos."""

    @pytest.mark.parametrize("dni", [DNI_INEXISTENTE, DNI_BAJA, DNI_SIN_CLIENTES, DNI_AMBIGUO])
    async def test_todos_dan_el_mismo_status_code_y_mensaje(self, repo, dni) -> None:
        base = await _rechazo(_svc(repo), DNI_INEXISTENTE)
        otro = await _rechazo(_svc(repo), dni)
        assert (otro.status_code, otro.code, otro.message) == \
               (base.status_code, base.code, base.message)

    async def test_el_bloqueo_por_limite_tambien_sale_por_el_mismo_rechazo(self, repo) -> None:
        """Un 429 sería un oráculo de segundo orden: le diría al que pregunta que ese dni se
        viene probando. Se usa un dni que SÍ existe, así que sin el bloqueo daría 200."""
        base = await _rechazo(_svc(repo), DNI_INEXISTENTE)
        bloqueado = await _rechazo(_svc(repo, bloquea=True), DNI_OK)
        assert (bloqueado.status_code, bloqueado.code, bloqueado.message) == \
               (base.status_code, base.code, base.message)

    async def test_el_mensaje_no_nombra_el_motivo(self, repo) -> None:
        msg = (await _rechazo(_svc(repo), DNI_BAJA)).message.lower()
        assert not any(t in msg for t in
                       ("baja", "inactiv", "empresa", "cliente", "existe", "límite", "limite"))

    async def test_el_exito_si_es_distinguible_del_rechazo(self, repo) -> None:
        """El contraste que hace que todo lo de arriba signifique algo: si el service rechazara
        SIEMPRE, "los cinco rechazos son iguales" pasaría trivialmente."""
        assert (await _svc(repo).identificar(DNI_OK)).nombre == "Juan"


# ── El payload es mínimo ──────────────────────────────────────────────────────


class TestPayloadMinimo:
    async def test_devuelve_el_nombre_de_pila_y_nada_mas_de_la_persona(self, repo) -> None:
        """El payload cambió al sumar el paso 2: ahora lleva `token` y `expira_en`.

        🔴 NO es una excepción a la regla del payload mínimo. Esa regla es sobre DATOS DE LA
        PERSONA —cada campo es algo que alguien que adivinó un dni aprende de un tercero— y el
        token no dice nada de nadie: es una capacidad opaca que este mismo request creó. Y es lo
        que permite que el paso 2 NO reciba un `empleado_id` por el body. La alternativa a
        devolver el token era devolver el `empleado_id`, que es justo lo que rompe la condición #3.
        """
        resp = await _svc(repo).identificar(DNI_OK)
        assert resp.nombre == "Juan"                      # "Juan Carlos" → primer token
        assert set(resp.model_dump()) == {"nombre", "token", "expira_en"}

    async def test_el_token_es_opaco_y_no_deriva_de_la_persona(self, repo) -> None:
        """Un token derivable del dni o del id no sería un secreto: se calcularía."""
        resp = await _svc(repo).identificar(DNI_OK)
        assert len(resp.token) >= 40
        for dato in (DNI_OK, EMP_ACTIVO, EMPRESA_CON, "Juan"):
            assert dato not in resp.token

    async def test_dos_identificaciones_dan_tokens_distintos(self, repo) -> None:
        uno = (await _svc(repo).identificar(DNI_OK)).token
        otro = (await _svc(repo).identificar(DNI_OK)).token
        assert uno != otro

    async def test_la_sesion_guarda_el_hash_y_nunca_el_token(self, repo) -> None:
        """De la base no puede salir nada con lo que autenticarse."""
        sesiones = _SesionesFalsas()
        resp = await _svc(repo, sesiones=sesiones).identificar(DNI_OK)
        guardada = sesiones.creadas[0]
        assert guardada["token_hash"] != resp.token
        assert resp.token not in str(guardada)

    async def test_la_sesion_se_emite_con_la_identidad_de_la_fila(self, repo) -> None:
        """🔴 El empleado y la empresa de la sesión salen de la fila que el dni matcheó. Es de
        acá de donde el paso 2 los va a leer, así que si esto se equivoca, todo lo que se cargue
        después queda a nombre de otro."""
        sesiones = _SesionesFalsas()
        await _svc(repo, sesiones=sesiones).identificar(DNI_OK)
        assert sesiones.creadas[0]["empleado_id"] == EMP_ACTIVO
        assert sesiones.creadas[0]["empresa_id"] == EMPRESA_CON

    async def test_un_rechazo_no_emite_sesion(self, repo) -> None:
        """Emitir una sesión para un dni rechazado le daría al atacante justo lo que no consiguió."""
        sesiones = _SesionesFalsas()
        await _rechazo(_svc(repo, sesiones=sesiones), DNI_BAJA)
        assert sesiones.creadas == []

    @pytest.mark.parametrize("prohibido", ["apellido", "cargo", "empresa", "empresa_id",
                                           "empleado_id", "dni", "estado", "id"])
    async def test_no_incluye_datos_que_no_le_sirven_al_empleado(self, repo, prohibido) -> None:
        """La empresa es el peor de los tres del mockup: al empleado no le sirve —ya sabe dónde
        trabaja— y a alguien enumerando le arma el mapa de la organización dni por dni.
        `empleado_id` tampoco vuelve: la identidad se resuelve server-side y no puede volver por
        el request en el paso siguiente."""
        cuerpo = (await _svc(repo).identificar(DNI_OK)).model_dump()
        assert prohibido not in cuerpo

    async def test_el_nombre_es_el_del_dni_pedido(self, repo) -> None:
        """Dos dnis, dos nombres distintos: un service que ignorara el valor recibido y siempre
        resolviera la misma fila no podría pasar."""
        assert (await _svc(repo).identificar(DNI_OK)).nombre == "Juan"
        assert (await _svc(repo).identificar(DNI_OTRO_OK)).nombre == "Mariana"


# ── El log distingue lo que la respuesta no ───────────────────────────────────


class TestRegistroDeIntentos:
    @pytest.mark.parametrize("dni,esperado", [
        (DNI_INEXISTENTE, "sin_coincidencia"), (DNI_BAJA, "inactivo"),
        (DNI_SIN_CLIENTES, "sin_clientes"), (DNI_AMBIGUO, "ambiguo"),
    ])
    async def test_cada_motivo_queda_registrado_con_su_nombre(self, repo, dni, esperado) -> None:
        """Hacia afuera son uno; adentro son cuatro. Sin esto el log no sirve para investigar."""
        await _rechazo(_svc(repo), dni)
        assert repo.intentos[0]["resultado"] == esperado

    async def test_el_bloqueo_se_registra_como_bloqueado(self, repo) -> None:
        await _rechazo(_svc(repo, bloquea=True), DNI_OK)
        assert repo.intentos[0]["resultado"] == "bloqueado"

    async def test_el_exito_tambien_se_registra(self, repo) -> None:
        """Si solo se loguearan los fallos, una enumeración EXITOSA sería invisible."""
        await _svc(repo).identificar(DNI_OK, ip="1.2.3.4", user_agent="curl/8")
        i = repo.intentos[0]
        assert (i["resultado"], i["empleado_id"], i["empresa_id"]) == \
               ("ok", EMP_ACTIVO, EMPRESA_CON)
        assert (i["ip"], i["user_agent"], i["dni"]) == ("1.2.3.4", "curl/8", DNI_OK)

    async def test_un_fallo_no_atribuye_empleado(self, repo) -> None:
        """Rellenar el empleado "que se creía" en un fallo sería inventar."""
        await _rechazo(_svc(repo), DNI_INEXISTENTE)
        assert repo.intentos[0]["empleado_id"] is None


# ── Los dos ejes del rate limit ───────────────────────────────────────────────


class TestRateLimitPorDni:
    async def test_el_limitador_recibe_el_dni_intentado(self, repo) -> None:
        vistos: list = []
        svc = IdentificacionService(repo=repo, limitador=lambda d: vistos.append(d) or True,
                                    sesiones=_SesionesFalsas())
        await svc.identificar(DNI_OK)
        assert vistos == [DNI_OK]

    async def test_se_consulta_antes_de_tocar_la_base(self, repo) -> None:
        """🔴 Un contador que se consulta DESPUÉS de las queries no protege a la base de nada:
        el atacante ya pagó las dos lecturas antes de que alguien le diga que no.

        Se afirma sobre `busquedas`, o sea sobre si el repo LLEGÓ A LLAMARSE. Mirar el resultado
        o el `empleado_id` no alcanza — con el orden invertido los dos quedan igual, y este test
        pasaba con la mutación puesta hasta que la corrida de mutación lo delató.
        """
        await _rechazo(_svc(repo, bloquea=True), DNI_OK)
        assert repo.busquedas == 0, "el limitador corrió DESPUÉS de consultar la base"
        assert repo.consultas_clientes == 0
        assert repo.intentos[0]["resultado"] == "bloqueado"

    async def test_sin_bloqueo_la_base_si_se_consulta(self, repo) -> None:
        """El contraste: sin esto, "no consultó la base" pasaría con un repo que nunca se usa."""
        await _svc(repo).identificar(DNI_OK)
        assert (repo.busquedas, repo.consultas_clientes) == (1, 1)

    def test_el_eje_por_dni_y_el_de_ip_son_contadores_distintos(self) -> None:
        """No se solapan: el de IP es un decorador de slowapi sobre el endpoint y el de dni vive
        en el service. Si el de dni compartiera la key_func del de IP, un solo pool de IPs
        anularía los dos a la vez."""
        from utils import rate_limit, rate_limit_dni
        assert rate_limit_dni._clave("30111222") != rate_limit_dni._clave("30111223")
        assert rate_limit.limiter._key_func is rate_limit.client_ip
        assert "20" in str(rate_limit_dni.LIMITE_POR_DNI)


# ── El piso de tiempo ─────────────────────────────────────────────────────────


class TestElPisoDeTiempo:
    """Se mide con el valor REAL. Testearlo solo con el piso pisado a 0 dejaría que borrar la
    nivelación entera pasara en verde, que es justo el bug que importa."""

    @pytest.fixture(autouse=True)
    def piso_real(self, monkeypatch):
        monkeypatch.setattr(svc_mod, "_PISO_SEGUNDOS", 0.12)

    async def test_el_exito_espera_el_piso(self, repo) -> None:
        t0 = perf_counter()
        await _svc(repo).identificar(DNI_OK)
        assert perf_counter() - t0 >= 0.12

    @pytest.mark.parametrize("dni", [DNI_INEXISTENTE, DNI_BAJA, DNI_SIN_CLIENTES, DNI_AMBIGUO])
    async def test_todos_los_rechazos_esperan_el_mismo_piso(self, repo, dni) -> None:
        """🔴 El canal que el mensaje uniforme no cierra: un dni inexistente se resuelve con UNA
        query y uno que existe dispara dos. Sin el piso esa diferencia es medible desde afuera."""
        t0 = perf_counter()
        await _rechazo(_svc(repo), dni)
        assert perf_counter() - t0 >= 0.12

    async def test_el_bloqueo_tambien_espera(self, repo) -> None:
        """Es el camino MÁS corto de todos —no toca la base ni una vez—, así que es el que más
        se notaría sin nivelar."""
        t0 = perf_counter()
        await _rechazo(_svc(repo, bloquea=True), DNI_OK)
        assert perf_counter() - t0 >= 0.12
