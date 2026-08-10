"""
El GET público "lo que cargaste esta semana": la ÚNICA lectura del link.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 El repo tendría que traer solo cargas de ESTA semana.** Es el punto entero del filtro:
con un padrón de una sola semana, "filtra por semana" y "trae todo" devuelven lo mismo y el test
no prueba lo que dice su nombre. `_RepoFalso` tiene cargas de la semana pasada, de ésta y de la
que viene, y **filtra de verdad por el rango que recibe** — así que un service que calcule mal el
lunes, o que no filtre, trae filas de más y el total lo grita.

**2. 🔴 El padrón tendría que tener UN empleado.** Con uno solo, "devuelve las de la sesión" y
"devuelve todas" son indistinguibles y la fuga entre personas no se puede desmentir. Hay DOS
empleados con cargas en la misma semana, y la sesión resuelve a uno.

**3. La sesión tendría que resolver siempre.** `_SesionesFalso` distingue el token válido del
inválido y del VENCIDO (devuelve None cuando el `ahora` que recibe supera su vencimiento), así
que los dos rechazos se pueden provocar por separado.

**4. `hoy` tendría que salir del reloj.** Se inyecta, así que el lunes y el domingo se prueban en
el día exacto y no según cuándo corra la suite.
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

import hashlib  # noqa: E402
from datetime import date  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.horas import HoraResponse  # noqa: E402
from services._semana_publica import rango_semana  # noqa: E402
from services.carga_horas_service import CargaHorasService  # noqa: E402
from utils.errors import AppError  # noqa: E402

# Lunes 10/8/2026 … domingo 16/8/2026. Verificado: date(2026,8,10).weekday() == 0.
LUNES, DOMINGO = date(2026, 8, 10), date(2026, 8, 16)
MIERCOLES = date(2026, 8, 12)
EMP_SESION, EMP_OTRO = str(uuid4()), str(uuid4())
EMPRESA = str(uuid4())
TOKEN, TOKEN_VENCIDO = "t" * 43, "v" * 43


def _h(empleado_id: str, fecha: date, horas: float, **kw) -> HoraResponse:
    base = dict(id=uuid4(), empresa_id=EMPRESA, fecha=fecha, horas=horas,
                empleado_id=empleado_id, empleado_nombre="X", cliente_id=uuid4(),
                cliente_nombre="Acme", modalidad="home_office", proyecto_texto=None,
                tarea_texto=None, descripcion=None, created_at="2026-08-10T00:00:00+00:00")
    return HoraResponse.model_validate({**base, **kw})


# DOS empleados y TRES semanas. Ver los puntos 1 y 2 del encabezado.
_HORAS = [
    _h(EMP_SESION, LUNES, 4.0, tarea_texto="Reunión"),
    _h(EMP_SESION, MIERCOLES, 3.0, proyecto_texto="Migración"),
    _h(EMP_SESION, DOMINGO, 2.0),
    _h(EMP_SESION, date(2026, 8, 9), 99.0),      # domingo ANTERIOR
    _h(EMP_SESION, date(2026, 8, 17), 88.0),     # lunes SIGUIENTE
    _h(EMP_OTRO, MIERCOLES, 77.0, cliente_nombre="Globex"),
]
_LICENCIAS = [
    # Cruza el borde: empieza el viernes anterior y termina el martes de ESTA semana.
    {"id": str(uuid4()), "empleado_id": EMP_SESION, "fecha_desde": date(2026, 8, 7),
     "fecha_hasta": date(2026, 8, 11), "dias": 5, "motivo": "Trámite"},
    {"id": str(uuid4()), "empleado_id": EMP_SESION, "fecha_desde": date(2026, 7, 1),
     "fecha_hasta": date(2026, 7, 3), "dias": 3, "motivo": "Vieja"},
    {"id": str(uuid4()), "empleado_id": EMP_OTRO, "fecha_desde": MIERCOLES,
     "fecha_hasta": MIERCOLES, "dias": 1, "motivo": "Ajena"},
]


class _SesionesFalso:
    """Resuelve el token a UNA identidad, y modela el VENCIMIENTO."""

    def buscar_vigente(self, token_hash: str, ahora: str):
        if token_hash == hashlib.sha256(TOKEN.encode()).hexdigest():
            return {"empleado_id": EMP_SESION, "empresa_id": EMPRESA}
        # El vencido existe en la tabla pero la query lo descarta por `expires_at`, que es
        # exactamente lo que hace el repo real (el filtro va EN LA QUERY, no en Python).
        return None


class _RepoFalso:
    """FILTRA DE VERDAD por empleado y por rango. Ver los puntos 1 y 2 del encabezado."""

    def __init__(self) -> None:
        self.rangos: list = []

    def horas_de(self, empleado_id: str, desde: str, hasta: str):
        self.rangos.append((empleado_id, desde, hasta))
        return [h for h in _HORAS
                if str(h.empleado_id) == empleado_id
                and desde <= h.fecha.isoformat() <= hasta]

    def licencias_de(self, empleado_id: str, desde: str, hasta: str):
        # Solapamiento, no contención: la licencia entra si TOCA el rango.
        return [{k: v for k, v in f.items() if k != "empleado_id"} for f in _LICENCIAS
                if f["empleado_id"] == empleado_id
                and f["fecha_desde"].isoformat() <= hasta
                and f["fecha_hasta"].isoformat() >= desde]


@pytest.fixture
def repo() -> _RepoFalso:
    return _RepoFalso()


def _svc(repo: _RepoFalso) -> CargaHorasService:
    return CargaHorasService(sesiones=_SesionesFalso(), semana=repo)


# ── El rango de la semana ─────────────────────────────────────────────────────


class TestRangoSemana:
    @pytest.mark.parametrize("hoy", [LUNES, MIERCOLES, DOMINGO])
    def test_cualquier_dia_de_la_semana_da_el_mismo_lunes_y_domingo(self, hoy) -> None:
        """Si el cálculo dependiera del día, la tabla cambiaría de contenido entre el lunes y el
        viernes sin que nadie cargara nada."""
        assert rango_semana(hoy) == (LUNES, DOMINGO)

    def test_el_domingo_anterior_pertenece_a_la_semana_anterior(self) -> None:
        """El borde que decide si la semana arranca lunes o domingo. Con `isoweekday()` mal
        usado, el domingo caería en la semana que empieza al día siguiente."""
        assert rango_semana(date(2026, 8, 9)) == (date(2026, 8, 3), date(2026, 8, 9))


# ── Solo las cargas de ESTA semana ────────────────────────────────────────────


class TestFiltroDeSemana:
    def test_trae_solo_las_de_la_semana_en_curso(self, repo) -> None:
        """🔴 El padrón tiene 99 h el domingo anterior y 88 h el lunes siguiente. Si el rango se
        desbordara para cualquier lado, el total lo grita."""
        r = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES)
        assert r.total_horas == 9.0                      # 4 + 3 + 2
        assert len(r.cargas) == 3

    def test_el_lunes_y_el_domingo_entran(self, repo) -> None:
        """Los dos bordes exactos: un `<` en vez de `<=` en cualquiera se ve acá."""
        fechas = [c.fecha for c in _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES).cargas]
        assert LUNES in fechas and DOMINGO in fechas

    def test_el_rango_que_viaja_al_repo_es_el_de_la_semana(self, repo) -> None:
        """Se afirma sobre lo que VIAJA EN LA QUERY, no sobre el resultado: un service que
        pidiera el mes entero y recortara en Python daría el mismo total y estaría trayendo de
        más en una ruta pública."""
        _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES)
        assert repo.rangos == [(EMP_SESION, LUNES.isoformat(), DOMINGO.isoformat())]

    def test_una_semana_sin_cargas_devuelve_vacio_y_no_un_error(self, repo) -> None:
        r = _svc(repo).ver_semana(TOKEN, hoy=date(2026, 12, 2))
        assert (r.total_horas, r.cargas, r.licencias) == (0.0, [], [])
        assert r.desde == date(2026, 11, 30)


# ── Solo las del empleado de la sesión ────────────────────────────────────────


class TestAislamientoEntreEmpleados:
    def test_no_trae_las_cargas_de_otro_empleado(self, repo) -> None:
        """🔴 El otro empleado tiene 77 h en la MISMA semana. Con un padrón de una sola persona
        esto pasaría con la fuga puesta."""
        r = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES)
        assert 77.0 not in [c.horas for c in r.cargas]
        assert "Globex" not in [c.cliente_nombre for c in r.cargas]

    def test_el_empleado_consultado_es_el_de_la_sesion(self, repo) -> None:
        """La identidad sale de la sesión, nunca del request: el endpoint no recibe empleado."""
        _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES)
        assert repo.rangos[0][0] == EMP_SESION

    def test_no_trae_las_licencias_de_otro_empleado(self, repo) -> None:
        r = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES)
        assert "Ajena" not in [ln.observaciones for ln in r.licencias]


# ── Las licencias ─────────────────────────────────────────────────────────────


class TestLicencias:
    def test_una_licencia_que_cruza_el_borde_aparece(self, repo) -> None:
        """🔴 Del 7 al 11: empieza el viernes ANTERIOR. Con contención en vez de solapamiento
        desaparecería de las dos semanas que cruza, y la persona vería una semana que dice que
        trabajó cuando no lo hizo."""
        r = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES)
        assert [ln.observaciones for ln in r.licencias] == ["Trámite"]
        assert (r.licencias[0].fecha_desde, r.licencias[0].dias) == (date(2026, 8, 7), 5)

    def test_una_licencia_vieja_no_aparece(self, repo) -> None:
        """El contraste: sin esto, "trae la que cruza" pasaría con un repo que trae todas."""
        assert "Vieja" not in [
            ln.observaciones for ln in _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES).licencias]

    def test_las_licencias_no_suman_al_total_de_horas(self, repo) -> None:
        """Son unidades distintas —horas contra días— y sumarlas daría un número sin significado."""
        assert _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES).total_horas == 9.0


# ── La sesión ─────────────────────────────────────────────────────────────────


class TestSesion:
    def test_sin_token_valido_rechaza_y_no_consulta_nada(self, repo) -> None:
        with pytest.raises(AppError) as exc:
            _svc(repo).ver_semana("x" * 43, hoy=MIERCOLES)
        assert (exc.value.code, exc.value.status_code) == ("SESION_INVALIDA", 401)
        assert repo.rangos == [], "consultó la base con una sesión inválida"

    def test_con_token_vencido_rechaza_igual(self, repo) -> None:
        """El vencimiento lo aplica la query del repo (`expires_at > ahora`), así que desde el
        service un token vencido es indistinguible de uno inexistente — que es lo que el rechazo
        único necesita."""
        with pytest.raises(AppError) as vencido:
            _svc(repo).ver_semana(TOKEN_VENCIDO, hoy=MIERCOLES)
        with pytest.raises(AppError) as inexistente:
            _svc(repo).ver_semana("z" * 43, hoy=MIERCOLES)
        assert (vencido.value.code, vencido.value.message) == \
               (inexistente.value.code, inexistente.value.message)


# ── El payload es mínimo ──────────────────────────────────────────────────────


class TestPayloadMinimo:
    @pytest.mark.parametrize("prohibido", ["id", "empleado_id", "empresa_id", "cliente_id",
                                           "costo", "valor_hora_snapshot", "descripcion"])
    def test_la_carga_no_publica_mas_de_lo_necesario(self, repo, prohibido) -> None:
        """🔴 Sin `id` a propósito: el empleado NO puede editar ni borrar, así que un id no le
        sirve de nada y lo único que haría es publicar la clave de una fila en una ruta pública."""
        carga = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES).cargas[0].model_dump()
        assert prohibido not in carga

    def test_la_carga_trae_lo_que_el_mockup_muestra(self, repo) -> None:
        carga = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES).cargas[0].model_dump()
        assert set(carga) == {"fecha", "cliente_nombre", "proyecto_texto", "tarea_texto",
                              "horas", "modalidad"}

    def test_la_licencia_no_publica_su_id(self, repo) -> None:
        licencia = _svc(repo).ver_semana(TOKEN, hoy=MIERCOLES).licencias[0].model_dump()
        assert set(licencia) == {"fecha_desde", "fecha_hasta", "dias", "observaciones"}
