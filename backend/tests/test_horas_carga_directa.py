"""
Carga directa de horas (migración 103): el mapper `_hora_row.build` y los DOS caminos de
escritura de `horas_proyecto`.

Desde la 103 la tabla tiene dos escritores con contratos opuestos:
  · CAMINO NUEVO — carga directa: cliente + empleado + modalidad + textos. SIN asignación, SIN
    proyecto, SIN `valor_hora_snapshot`. **Es el caso normal del flujo, no el borde.**
  · CAMINO VIEJO — `POST /api/proyectos/{id}/horas`: asignación + proyecto + snapshot. No se
    puede romper.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. El catálogo tendría que tener UNA sola fila por dimensión.** Con un solo cliente, un solo
empleado y una sola empresa, un mapper que emitiera CONSTANTES pasaría idéntico: no habría con
qué contrastar. Por eso hay dos clientes con nombres distintos, dos empresas distintas, dos
empleados distintos y dos modalidades distintas, y cada aserción compara las filas ENTRE SÍ
(`!=`), no contra un literal suelto.

**2. `_FakeSupabase` tendría que devolver el mismo empleado sin importar el id.** Filtra por la
columna del `in_`, así que resolver el empleado por la asignación (camino viejo) y por la
columna propia (camino nuevo) da nombres DISTINTOS — y ahí se ve si el mapper eligió el origen
correcto. Un fake que respondiera lo mismo a los dos dejaría esa elección sin probar.

**3. El fake de escritura tendría que devolver una fila prefabricada.** Construye la fila A
PARTIR del payload que recibió, así que si `save` dejara de mandar `modalidad` o `cliente_id`,
la respuesta no los tendría y las aserciones de "el campo llega al response" fallarían. Un fake
que devolviera un objeto armado por el test estaría afirmando algo sobre su propia constante
(ver el encabezado de `test_domicilio_desglosado.py`).

**4. `consultas` tendría que no registrarse.** Sin ella, "los lookups son batch" no se puede
desmentir: un mapper que consultara una vez por fila daría exactamente el mismo resultado.
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

from datetime import UTC, date, datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories._hora_row as hora_row  # noqa: E402
import repositories.horas_repo as horas_repo_mod  # noqa: E402
from repositories.horas_repo import HorasRepo  # noqa: E402
from schemas.horas import HoraCreate  # noqa: E402
from services.horas_service import HorasService  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

EMPRESA_A, EMPRESA_B = str(uuid4()), str(uuid4())
CLI_ACME, CLI_GLOBEX = str(uuid4()), str(uuid4())
EMP_DIRECTO, EMP_POR_ASIG = str(uuid4()), str(uuid4())
ASIG, PROY = str(uuid4()), str(uuid4())
AHORA = datetime.now(UTC).isoformat()

# Dos filas por dimensión, con valores DISTINTOS. Ver el punto 1 del encabezado.
CATALOGO = {
    "proyecto_asignaciones": [{"id": ASIG, "empleado_id": EMP_POR_ASIG}],
    "empleados": [
        {"id": EMP_DIRECTO, "nombre": "Ana", "apellido": "Pérez"},
        {"id": EMP_POR_ASIG, "nombre": "Bruno", "apellido": "Gómez"},
    ],
    "empresas": [{"id": EMPRESA_A, "nombre": "Karstec"}, {"id": EMPRESA_B, "nombre": "Dosuba"}],
    "clientes": [{"id": CLI_ACME, "nombre": "Acme"}, {"id": CLI_GLOBEX, "nombre": "Globex"}],
}


def _directa(**kw) -> dict:
    """Fila del CAMINO NUEVO: sin asignación, sin proyecto, sin snapshot."""
    base = {
        "id": str(uuid4()), "asignacion_id": None, "proyecto_id": None,
        "valor_hora_snapshot": None, "empresa_id": EMPRESA_A,
        "empleado_empresa_id": EMPRESA_A, "empleado_id": EMP_DIRECTO,
        "fecha": "2026-08-03", "horas": 6.5, "descripcion": None, "cargado_por": None,
        "cliente_id": CLI_ACME, "modalidad": "home_office",
        "proyecto_texto": "Migración AWS", "tarea_texto": "Reunión de kickoff",
        "created_at": AHORA,
    }
    return {**base, **kw}


def _vieja(**kw) -> dict:
    """Fila del CAMINO VIEJO: asignación + proyecto + snapshot, sin nada de la 103."""
    base = {
        "id": str(uuid4()), "asignacion_id": ASIG, "proyecto_id": PROY,
        "valor_hora_snapshot": 1000.0, "empresa_id": EMPRESA_A,
        "empleado_empresa_id": EMPRESA_A, "empleado_id": None,
        "fecha": "2026-08-04", "horas": 8.0, "descripcion": "sprint", "cargado_por": None,
        "cliente_id": None, "modalidad": None, "proyecto_texto": None, "tarea_texto": None,
        "created_at": AHORA,
    }
    return {**base, **kw}


@pytest.fixture
def fake(monkeypatch) -> FakeSupabase:
    f = FakeSupabase({k: [dict(x) for x in v] for k, v in CATALOGO.items()})
    monkeypatch.setattr(hora_row, "supabase_admin", f)
    return f


# ── El mapper expone los campos nuevos ────────────────────────────────────────


class TestElMapperExponeLosCamposNuevos:
    """Los cinco campos de la 103 tienen que llegar al response. Pasó CINCO veces en este repo
    que el select trajera la columna y el schema la descartara en silencio (PresupuestoResponse,
    CandidatoResponse, `liderazgo`, los cinco de vacante, el organigrama)."""

    @pytest.fixture
    def filas(self, fake):
        directa_a = _directa()
        directa_b = _directa(
            empleado_empresa_id=EMPRESA_B, cliente_id=CLI_GLOBEX, modalidad="on_site",
            proyecto_texto=None, tarea_texto="Soporte", horas=2.0)
        return hora_row.build([directa_a, directa_b, _vieja()])

    def test_cliente_resuelto_y_distinto_por_fila(self, filas) -> None:
        """Dos clientes distintos: un mapper que emitiera una constante no podría pasar."""
        assert [f.cliente_nombre for f in filas] == ["Acme", "Globex", None]
        assert [str(f.cliente_id or "") for f in filas] == [CLI_ACME, CLI_GLOBEX, ""]

    def test_modalidad_llega_y_distingue(self, filas) -> None:
        assert [f.modalidad for f in filas] == ["home_office", "on_site", None]

    def test_proyecto_y_tarea_texto_llegan(self, filas) -> None:
        assert [f.proyecto_texto for f in filas] == ["Migración AWS", None, None]
        assert [f.tarea_texto for f in filas] == ["Reunión de kickoff", "Soporte", None]

    def test_el_empleado_sale_de_la_columna_propia_o_de_la_asignacion(self, filas) -> None:
        """🔴 Los dos orígenes dan nombres DISTINTOS: si el mapper leyera siempre el mismo, una
        de las dos filas saldría con el nombre del otro empleado."""
        assert [f.empleado_nombre for f in filas] == ["Ana Pérez", "Ana Pérez", "Bruno Gómez"]
        assert str(filas[0].empleado_id) == EMP_DIRECTO
        assert str(filas[2].empleado_id) == EMP_POR_ASIG

    def test_la_empresa_del_empleado_sale_de_la_fila(self, filas) -> None:
        """Las dos cargas directas tienen empresas distintas y NINGUNA tiene asignación: si el
        mapper siguiera resolviéndola por la asignación, las dos saldrían en None."""
        assert [f.empleado_empresa_nombre for f in filas] == ["Karstec", "Dosuba", "Karstec"]

    def test_costo_none_sin_snapshot_y_calculado_con_snapshot(self, filas) -> None:
        """None y NO 0.0: "no se puede costear" ≠ "costó cero". Un 0.0 se sumaría a un total
        como si fuera un dato."""
        assert [f.costo for f in filas] == [None, None, 8000.0]
        assert [f.valor_hora_snapshot for f in filas] == [None, None, 1000.0]

    def test_los_lookups_son_batch(self, fake, filas) -> None:
        """Una query por dimensión, nunca una por fila. Con 3 filas y 4 dimensiones, un mapper
        con N+1 registraría 12."""
        tablas = [t for t, _, _ in fake.consultas]
        assert sorted(tablas) == ["clientes", "empleados", "empresas", "proyecto_asignaciones"]


class TestLaListaVaciaNoPruebaNada:
    def test_el_early_return_sigue_ahi(self) -> None:
        """Anclaje: si alguien le saca el early-return, el test de abajo deja de significar lo
        que dice y hay que enterarse."""
        assert guarda_de(hora_row.build) == "rows"

    def test_con_lista_vacia_no_se_ejecuta_una_sola_query(self, fake) -> None:
        assert hora_row.build([]) == []
        assert fake.consultas == []


# ── Los dos caminos de escritura ──────────────────────────────────────────────


class _Escritor:
    """Fake de escritura de `horas_proyecto`: arma la fila CON EL PAYLOAD QUE RECIBIÓ.

    No prefabrica nada. Si `save` deja de mandar un campo, la fila guardada no lo tiene y el
    response tampoco — que es justo lo que los tests de abajo miran."""

    def __init__(self, lectura: FakeSupabase) -> None:
        self.lectura, self.payloads, self.filas = lectura, [], []

    def table(self, tabla: str) -> "_Escritor":
        self._tabla = tabla
        return self

    def select(self, *a, **k) -> "_Escritor":
        self._modo = "select"
        return self

    def insert(self, payload: dict) -> "_Escritor":
        self._modo, self._payload = "insert", payload
        return self

    def eq(self, col: str, val) -> "_Escritor":
        self._filtro = (col, str(val))
        return self

    def order(self, *a, **k) -> "_Escritor":
        return self

    def range(self, *a, **k) -> "_Escritor":
        return self

    def execute(self):
        if self._modo == "insert":
            self.payloads.append(dict(self._payload))
            fila = {"id": str(uuid4()), "created_at": AHORA, **self._payload}
            self.filas.append(fila)
            return SimpleNamespace(data=[fila], count=1)
        col, val = self._filtro
        halladas = [f for f in self.filas if str(f.get(col)) == val]
        return SimpleNamespace(data=halladas, count=len(halladas))


@pytest.fixture
def escritor(fake, monkeypatch) -> _Escritor:
    e = _Escritor(fake)
    monkeypatch.setattr(horas_repo_mod, "supabase_admin", e)
    return e


class TestCargaDirecta:
    """El caso NORMAL del flujo nuevo: sin proyecto y sin asignación."""

    @pytest.fixture
    def guardada(self, escritor):
        return HorasRepo().save(
            empresa_id=EMPRESA_A, empleado_empresa_id=EMPRESA_A, fecha="2026-08-03", horas=6.5,
            empleado_id=EMP_DIRECTO, cliente_id=CLI_ACME, modalidad="home_office",
            proyecto_texto="Migración AWS", tarea_texto="Reunión de kickoff")

    def test_guarda_sin_asignacion_ni_proyecto_ni_snapshot(self, escritor, guardada) -> None:
        """🔴 Las tres claves NO tienen que viajar en el INSERT. Mandarlas en None contra las
        columnas viejas funcionaría igual hoy, pero el punto de la 103 es que una carga directa
        no tiene nada que decir sobre ellas."""
        payload = escritor.payloads[0]
        assert "asignacion_id" not in payload
        assert "proyecto_id" not in payload
        assert "valor_hora_snapshot" not in payload

    def test_los_campos_nuevos_viajan_en_el_insert(self, escritor, guardada) -> None:
        payload = escritor.payloads[0]
        assert payload["cliente_id"] == CLI_ACME
        assert payload["modalidad"] == "home_office"
        assert payload["proyecto_texto"] == "Migración AWS"
        assert payload["tarea_texto"] == "Reunión de kickoff"
        assert payload["empleado_id"] == EMP_DIRECTO

    def test_el_response_trae_todo_resuelto(self, guardada) -> None:
        assert guardada.cliente_nombre == "Acme"
        assert guardada.empleado_nombre == "Ana Pérez"
        assert guardada.empleado_empresa_nombre == "Karstec"
        assert guardada.modalidad == "home_office"
        assert guardada.horas == 6.5

    def test_sin_costo_porque_no_hay_snapshot(self, guardada) -> None:
        assert guardada.costo is None and guardada.valor_hora_snapshot is None
        assert guardada.proyecto_id is None and guardada.asignacion_id is None

    def test_un_texto_vacio_es_un_dato_y_no_un_campo_ausente(self, escritor) -> None:
        """`proyecto_texto=""` lo escribió el usuario; no es lo mismo que no mandarlo. Por eso
        el repo filtra con `is not None` y no por truthiness."""
        HorasRepo().save(empresa_id=EMPRESA_A, empleado_empresa_id=EMPRESA_A,
                         fecha="2026-08-03", horas=1.0, proyecto_texto="")
        assert escritor.payloads[-1]["proyecto_texto"] == ""


class TestCaminoViejoSigueFuncionando:
    """El endpoint publicado `POST /api/proyectos/{id}/horas` no se puede romper. Se ejercita
    ENTERO —service + repo real + mapper—, no solo el repo: lo que cambió es la firma de `save`,
    y el único que la conoce desde afuera es el service."""

    @pytest.fixture
    def servicio(self, escritor) -> HorasService:
        asig = SimpleNamespace(id=ASIG, proyecto_id=PROY, activo=True,
                               empleado_empresa_id=EMPRESA_A, valor_hora=1000.0)
        return HorasService(
            repo=HorasRepo(),
            asig_repo=SimpleNamespace(find_by_id=lambda _id: asig),
            proyectos_repo=SimpleNamespace(
                find_by_id=lambda _id, _e=None: SimpleNamespace(id=PROY),
                find_empresa_for=lambda _id: EMPRESA_A),
        )

    @pytest.fixture
    def cargada(self, servicio):
        return servicio.cargar(PROY, HoraCreate(asignacion_id=ASIG, fecha=date(2026, 8, 4),
                                                horas=8.0, descripcion="sprint"))

    def test_sigue_congelando_el_snapshot_y_costeando(self, cargada) -> None:
        assert cargada.valor_hora_snapshot == 1000.0
        assert cargada.costo == 8000.0

    def test_sigue_escribiendo_asignacion_y_proyecto(self, escritor, cargada) -> None:
        payload = escritor.payloads[0]
        assert payload["asignacion_id"] == ASIG
        assert payload["proyecto_id"] == PROY
        assert payload["descripcion"] == "sprint"

    def test_el_empleado_se_sigue_resolviendo_por_la_asignacion(self, cargada) -> None:
        """No escribe `empleado_id`, así que el nombre solo puede salir de la asignación."""
        assert cargada.empleado_nombre == "Bruno Gómez"
        assert str(cargada.empleado_id) == EMP_POR_ASIG

    def test_no_inventa_campos_de_la_103(self, escritor, cargada) -> None:
        payload = escritor.payloads[0]
        assert not {"cliente_id", "modalidad", "proyecto_texto", "tarea_texto"} & set(payload)
        assert cargada.cliente_nombre is None and cargada.modalidad is None

    def test_un_snapshot_de_cero_sigue_viajando(self, escritor) -> None:
        """🔴 NO es un caso de borde: las 31 asignaciones de producción tienen `valor_hora = 0`.

        El repo filtra los opcionales con `is not None` justamente por esto. Con un filtro por
        truthiness —que es lo que hacen `descripcion` y `cargado_por`— un snapshot de 0.0 se
        caería del INSERT, la columna quedaría NULL, y la fila pasaría a tener proyecto SIN
        snapshot: el estado mixto que el CHECK `horas_proyecto_forma_check` prohíbe. O sea, hoy
        el camino viejo fallaría contra la base en TODAS las cargas reales.
        """
        asig = SimpleNamespace(id=ASIG, proyecto_id=PROY, activo=True,
                               empleado_empresa_id=EMPRESA_A, valor_hora=0.0)
        svc = HorasService(
            repo=HorasRepo(),
            asig_repo=SimpleNamespace(find_by_id=lambda _id: asig),
            proyectos_repo=SimpleNamespace(
                find_by_id=lambda _id, _e=None: SimpleNamespace(id=PROY),
                find_empresa_for=lambda _id: EMPRESA_A))
        fila = svc.cargar(PROY, HoraCreate(asignacion_id=ASIG, fecha=date(2026, 8, 4), horas=8.0))
        assert escritor.payloads[0]["valor_hora_snapshot"] == 0.0
        assert fila.valor_hora_snapshot == 0.0
        # Con snapshot 0 el costo SÍ se calcula y da 0.0 — es un dato, no un "no se puede".
        assert fila.costo == 0.0
