"""
Auditoría del import de nómina de COSTOS (Flujo 2): UN evento por lote.

Antes de esto el flujo tenía cobertura CERO: `batch_upsert_nomina` y `confirmar_nomina`
aparecían en un solo test de todo el repo, y solo para verificar que el endpoint tuviera rate
limit. El `confirmar` persistía el lote sin emitir ningún evento, así que un import de sueldos
era invisible en `/auditoria`, contra la regla propia de "un evento por lote".

Qué se fija acá:
  1. Un import emite EXACTAMENTE UN evento, no uno por fila.
  2. El conteo del evento sale del RETORNO DEL REPO, no de los flags del body.
  3. El evento se emite SIEMPRE: también con lote vacío y con lote parcial.
  4. `registro_id` es un uuid válido y distinto en cada import (es id de EVENTO).
  5. `empresa_id` es el del body, nunca None.
  6. El repo DEVUELVE lo que persistió — el escalón que el fake de repo tapa.

⚠️ La pregunta obligatoria ("¿qué tendría que ser distinto en el fake para que este test
falle?") está contestada en el docstring de cada test.
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
from uuid import UUID, uuid4

from schemas.importacion import FilaNominaPreview, ImportacionNominaConfirmarRequest
from services._audit_payloads_import import payload_importacion_costos
from services.nomina_import_service import NominaImportService, _periodos

EMPRESA = str(uuid4())


def _fila(n: int, *, anio: int = 2026, mes: int = 6, bruto: float = 1000.0,
          neto: float = 800.0, actualizacion: bool = False) -> FilaNominaPreview:
    return FilaNominaPreview(
        fila=n, dni=f"3000000{n}", nombre_empleado=f"Emp {n}", empleado_id=f"emp-{n}",
        anio=anio, mes=mes, salario_bruto=bruto, neto=neto, es_actualizacion=actualizacion,
    )


def _body(filas, empresa_id: str = EMPRESA) -> ImportacionNominaConfirmarRequest:
    return ImportacionNominaConfirmarRequest(empresa_id=empresa_id, filas=filas)


class _FakeRepo:
    """Repo falso que devuelve una cantidad de filas CONFIGURABLE, distinta de la enviada.

    🔴 Que el retorno se pueda configurar aparte de la entrada es lo que hace falsable el test
    del conteo: si el fake devolviera siempre `filas` (lo que recibió), "contar el retorno" y
    "contar el body" darían el mismo número y ningún test podría distinguir de dónde salió.
    """

    def __init__(self, devuelve: int | None = None) -> None:
        self._devuelve = devuelve
        self.recibido: list[list[dict]] = []

    def batch_upsert_nomina(self, filas: list[dict]) -> list[dict]:
        self.recibido.append(filas)
        n = len(filas) if self._devuelve is None else self._devuelve
        return [{"id": str(uuid4())} for _ in range(n)]


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


def _correr(filas, devuelve=None, usuario_id="u1"):
    """Corre el confirmar con repo y audit falsos. Devuelve (respuesta, repo, audit)."""
    repo, audit = _FakeRepo(devuelve), _FakeAudit()
    svc = NominaImportService(repo=repo, audit=audit)
    resp = svc.confirmar(_body(filas), usuario_id)
    return resp, repo, audit


# ─── El payload puro ──────────────────────────────────────────────────────────


class TestElPayloadPuro:
    """Molde: `test_audit_payload_nomina.py` — se compara el dict `datos_nuevos` ENTERO."""

    def test_forma_completa_del_evento(self) -> None:
        """La comparación es del dict entero, no de claves sueltas, a propósito: es lo que hace
        que una clave agregada sin querer al payload rompa el test en vez de colarse.

        ¿Qué tendría que ser distinto para que falle? Nada del fake — no hay fake, es una
        función pura. Falla si alguien cambia la forma del evento sin actualizar el contrato."""
        p = payload_importacion_costos(EMPRESA, ["2026-06"], 5, 5, "u1")
        assert p["entidad"] == "nomina"
        assert p["evento"] == "importacion_costos"
        assert p["accion"] == "INSERT"
        assert p["usuario_id"] == "u1"
        assert p["datos_anteriores"] is None
        assert p["datos_nuevos"] == {
            "periodos": ["2026-06"], "filas_enviadas": 5,
            "filas_persistidas": 5, "parcial": False,
        }

    def test_no_lleva_importados_ni_actualizados(self) -> None:
        """🔴 Omisión DELIBERADA: el upsert de PostgREST no dice cuáles filas fueron INSERT y
        cuáles UPDATE, y el único lugar donde esa distinción existe es el `es_actualizacion` del
        body, que lo manda el cliente. El log no afirma lo que no puede sostener.

        Sin este test, alguien "completa" el payload con los dos campos leyéndolos del body y
        vuelve a meter el dato no verificable, que es justo lo que este diseño evita."""
        datos = payload_importacion_costos(EMPRESA, ["2026-06"], 5, 5, "u1")["datos_nuevos"]
        assert "importados" not in datos and "actualizados" not in datos

    def test_registro_id_es_uuid_valido_y_distinto_por_llamada(self) -> None:
        """id DE EVENTO (uuid4), no de recurso: `costos_nomina` no persiste un lote con id
        propio. Un sentinel de texto rompería el cast a uuid de la columna y `AuditService` se
        tragaría el error → evento perdido en silencio (ya pasó con "lote_nomina")."""
        a = payload_importacion_costos(EMPRESA, ["2026-06"], 1, 1, "u1")
        b = payload_importacion_costos(EMPRESA, ["2026-06"], 1, 1, "u1")
        UUID(a["registro_id"])
        UUID(b["registro_id"])
        assert a["registro_id"] != b["registro_id"]

    def test_empresa_id_va_seteada_no_none(self) -> None:
        """Al revés que `payload_importacion_nomina` (empleados), que va con None porque su lote
        cruza empresas. Con None, el evento quedaría fuera del filtro por empresa de /auditoria."""
        assert payload_importacion_costos(EMPRESA, [], 0, 0, "u1")["empresa_id"] == EMPRESA

    def test_parcial_se_deriva_de_los_dos_conteos(self) -> None:
        """`parcial` no es un parámetro que el caller pueda mentir: se calcula acá."""
        assert payload_importacion_costos(EMPRESA, [], 5, 2, "u1")["datos_nuevos"]["parcial"] is True
        assert payload_importacion_costos(EMPRESA, [], 5, 5, "u1")["datos_nuevos"]["parcial"] is False


# ─── Un evento por lote ───────────────────────────────────────────────────────


class TestUnEventoPorLote:
    def test_tres_filas_emiten_un_solo_evento(self) -> None:
        """🔴 El lote tiene TRES filas y no una: con una sola, "un evento por lote" y "un evento
        por fila" dan el mismo número y el test no distingue las dos implementaciones.

        ¿Qué tendría que ser distinto en el fake para que falle? Que el lote tuviera 1 fila.
        Con 3, mover el `registrar` adentro de un loop por fila lo rompe."""
        _, _, audit = _correr([_fila(1), _fila(2), _fila(3)])
        assert len(audit.calls) == 1
        assert audit.calls[0]["evento"] == "importacion_costos"

    def test_el_evento_lleva_la_empresa_del_body(self) -> None:
        """La empresa sale del BODY (parámetro de la acción), no del header ni de None."""
        otra = str(uuid4())
        repo, audit = _FakeRepo(), _FakeAudit()
        NominaImportService(repo=repo, audit=audit).confirmar(_body([_fila(1)], otra), "u1")
        assert audit.calls[0]["empresa_id"] == otra

    def test_el_usuario_viaja_al_evento(self) -> None:
        """Sin esto el evento no diría quién importó los sueldos. El handler no lo extraía."""
        _, _, audit = _correr([_fila(1)], usuario_id="franco-123")
        assert audit.calls[0]["usuario_id"] == "franco-123"

    def test_dos_imports_seguidos_dan_registro_id_distinto(self) -> None:
        """A nivel service, no solo del payload puro: cada import es un evento propio."""
        _, _, a1 = _correr([_fila(1)])
        _, _, a2 = _correr([_fila(1)])
        assert a1.calls[0]["registro_id"] != a2.calls[0]["registro_id"]


# ─── De dónde salen los conteos ───────────────────────────────────────────────


class TestLosConteosSalenDelRepo:
    """🔴 EL PUNTO CENTRAL: el número del evento sale de lo que devolvió la BASE, no de lo que
    dijo el cliente. `es_actualizacion` se calculó en el preview y volvió por la red en el body.
    """

    def test_filas_persistidas_es_el_retorno_no_el_body(self) -> None:
        """El fake recibe 4 filas y devuelve 2: los dos números tienen que ser distinguibles.

        Los flags del body dan importados=1 y actualizados=3. El retorno da 2. Los tres números
        son distintos entre sí Y distintos de 4, así que `filas_persistidas == 2` solo puede
        haber salido del retorno del repo — ninguna cuenta sobre el body da 2.

        ¿Qué tendría que ser distinto en el fake para que falle? Que devolviera tantas filas
        como recibió (`devuelve=None`): ahí 4 == 4 y contar el body pasaría igual."""
        filas = [
            _fila(1, actualizacion=True), _fila(2, actualizacion=True),
            _fila(3, actualizacion=True), _fila(4, actualizacion=False),
        ]
        _, _, audit = _correr(filas, devuelve=2)
        datos = audit.calls[0]["datos_nuevos"]
        assert datos["filas_enviadas"] == 4
        assert datos["filas_persistidas"] == 2
        assert datos["parcial"] is True

    def test_la_respuesta_http_conserva_el_desglose_del_body(self) -> None:
        """La pantalla sigue viendo importados/actualizados: el contrato HTTP no cambió.

        Es la contracara del test de arriba — sin esto, "el evento no usa es_actualizacion"
        podría implementarse borrando el desglose también de la respuesta, y rompería el front.
        """
        filas = [_fila(1, actualizacion=True), _fila(2, actualizacion=False), _fila(3)]
        resp, _, _ = _correr(filas, devuelve=1)
        assert (resp.importados, resp.actualizados) == (2, 1)
        assert resp.errores == []


# ─── Lote vacío y lote parcial ────────────────────────────────────────────────


class TestSiempreSeEmite:
    def test_lote_vacio_igual_emite_evento(self) -> None:
        """Un confirmar sin filas es raro pero no imposible, y tiene que dejar rastro: alguien
        apretó el botón. Si el evento se emitiera solo cuando hay filas, ese intento sería
        invisible.

        ¿Qué tendría que ser distinto para que falle? Que el service pusiera el `registrar`
        detrás de un `if filas:`."""
        _, _, audit = _correr([])
        assert len(audit.calls) == 1
        assert audit.calls[0]["datos_nuevos"] == {
            "periodos": [], "filas_enviadas": 0, "filas_persistidas": 0, "parcial": False,
        }

    def test_lote_parcial_igual_emite_evento_y_lo_marca(self) -> None:
        """Se enviaron 3 y entró 1: el evento sale igual y `parcial` lo dice. Es el caso en el
        que MÁS importa que el evento exista."""
        _, _, audit = _correr([_fila(1), _fila(2), _fila(3)], devuelve=1)
        datos = audit.calls[0]["datos_nuevos"]
        assert datos["parcial"] is True
        assert (datos["filas_enviadas"], datos["filas_persistidas"]) == (3, 1)

    def test_el_evento_se_emite_DESPUES_de_persistir(self) -> None:
        """Orden: primero la base, después el log. Al revés, un fallo del upsert dejaría un
        evento afirmando un import que no ocurrió.

        El fake de audit consulta el repo en el momento de registrar: si el `registrar` se
        moviera antes del upsert, `recibido` estaría vacío y el test falla."""
        repo = _FakeRepo()
        orden: list[str] = []

        class _AuditQueMira:
            def registrar(self, **kw) -> None:
                orden.append("audit" if repo.recibido else "audit-antes-del-upsert")

        NominaImportService(repo=repo, audit=_AuditQueMira()).confirmar(_body([_fila(1)]), "u1")
        assert orden == ["audit"]


# ─── Períodos ─────────────────────────────────────────────────────────────────


class TestPeriodos:
    def test_un_solo_periodo_igual_va_como_lista(self) -> None:
        """Forma estable: siempre lista, aunque haya uno solo. Alternar string/lista según el
        contenido obliga a quien lee el log a manejar dos formas."""
        assert _periodos([_fila(1, mes=6), _fila(2, mes=6)]) == ["2026-06"]

    def test_varios_periodos_se_listan_ordenados_y_sin_repetir(self) -> None:
        filas = [_fila(1, anio=2026, mes=6), _fila(2, anio=2025, mes=12), _fila(3, anio=2026, mes=6)]
        assert _periodos(filas) == ["2025-12", "2026-06"]

    def test_el_mes_va_con_cero_adelante(self) -> None:
        """Sin el padding, "2026-9" ordena DESPUÉS de "2026-12" (orden de string) y la lista
        saldría mal ordenada."""
        assert _periodos([_fila(1, mes=9), _fila(2, mes=12)]) == ["2026-09", "2026-12"]

    def test_lote_vacio_da_lista_vacia(self) -> None:
        assert _periodos([]) == []


# ─── Lo que el fake de repo tapa ──────────────────────────────────────────────


class TestElRepoDevuelveLoQuePersistio:
    """🔴 EL ESCALÓN QUE LOS FAKES DE ARRIBA NO PUEDEN VER.

    Todos los tests de service inyectan un `_FakeRepo`, así que prueban que el service CUENTA el
    retorno — no que el repo real lo DEVUELVA. Es la misma clase de agujero que dejó dos mappers
    rotos con 10 tests de service en verde: el fake tapaba la capa donde estaba el bug.

    Si `batch_upsert_nomina` dejara de devolver (`res.data or []` → nada), el service recibiría
    None y `len(None)` reventaría el import entero; si devolviera una constante, el conteo del
    evento sería mentira. Acá se faltea el cliente de Supabase, un escalón más abajo.
    (Mismo molde que `TestElOrdenLoPoneLaQuery` en test_historial_salarial.py.)
    """

    @staticmethod
    def _repo_con_espia(monkeypatch, data):
        import repositories.nomina_import_repo as mod

        capturado: dict = {}

        class _Q:
            def upsert(self, filas, on_conflict=None):
                capturado["filas"] = filas
                capturado["on_conflict"] = on_conflict
                return self

            def execute(self):
                return SimpleNamespace(data=data)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.NominaImportRepo(), capturado

    def test_devuelve_las_filas_que_dio_la_base(self, monkeypatch) -> None:
        """El retorno del repo ES el dato autoritativo del evento: tiene que salir de `res.data`.

        Se le pide persistir 1 fila y la base "devuelve" 3: si el repo devolviera lo que recibió
        en vez de lo que respondió la base, este test daría 1 y falla. Es un caso imposible en
        producción, elegido justamente porque hace visible de dónde sale el número."""
        repo, _ = self._repo_con_espia(monkeypatch, [{"id": "a"}, {"id": "b"}, {"id": "c"}])
        assert len(repo.batch_upsert_nomina([{"empleado_id": "e1"}])) == 3

    def test_data_en_none_da_lista_vacia_no_explota(self, monkeypatch) -> None:
        """`res.data` puede venir None; el service hace `len(...)` sobre esto."""
        repo, _ = self._repo_con_espia(monkeypatch, None)
        assert repo.batch_upsert_nomina([{"empleado_id": "e1"}]) == []

    def test_el_on_conflict_es_la_clave_unica_real(self, monkeypatch) -> None:
        """Sin el `on_conflict` correcto el upsert inserta duplicados en vez de actualizar, y el
        import deja de ser idempotente. La clave única real de `costos_nomina` es esa terna."""
        repo, capturado = self._repo_con_espia(monkeypatch, [])
        repo.batch_upsert_nomina([{"empleado_id": "e1", "anio": 2026, "mes": 6}])
        assert capturado["on_conflict"] == "empleado_id,anio,mes"

    def test_lote_vacio_no_toca_la_base(self, monkeypatch) -> None:
        """Guard del repo: con 0 filas devuelve [] sin abrir una query. Si el guard se cayera,
        el upsert saldría con una lista vacía y PostgREST respondería un error."""
        repo, capturado = self._repo_con_espia(monkeypatch, [{"id": "a"}])
        assert repo.batch_upsert_nomina([]) == []
        assert capturado == {}, "no tenía que llegar a armar la query"


# ─── El armado de filas que se mudó del router ────────────────────────────────


class TestElArmadoDeFilas:
    """La construcción de las filas se movió del router al service. Estos tests son la red de
    esa mudanza: antes no existían, y el router no tenía ninguno."""

    def test_cargas_sociales_es_bruto_menos_neto(self) -> None:
        _, repo, _ = _correr([_fila(1, bruto=1000.0, neto=800.0)])
        assert repo.recibido[0][0]["cargas_sociales"] == 200.0

    def test_cargas_sociales_nunca_es_negativa(self) -> None:
        """`max(0.0, ...)`: un neto mayor que el bruto es un dato malo del archivo, no un
        crédito. Sin el piso, entraría un número negativo a la columna."""
        _, repo, _ = _correr([_fila(1, bruto=800.0, neto=1000.0)])
        assert repo.recibido[0][0]["cargas_sociales"] == 0.0

    def test_cada_fila_lleva_la_empresa_del_body(self) -> None:
        """La fila persistida se etiqueta con la empresa del body, no con la del header."""
        _, repo, _ = _correr([_fila(1), _fila(2)])
        assert [f["empresa_id"] for f in repo.recibido[0]] == [EMPRESA, EMPRESA]

    def test_no_se_manda_la_columna_generada_total(self) -> None:
        """`total` es columna generada en la base: mandarla hace fallar el insert."""
        _, repo, _ = _correr([_fila(1)])
        assert "total" not in repo.recibido[0][0]
