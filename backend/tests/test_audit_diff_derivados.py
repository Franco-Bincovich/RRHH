"""
🔴 Un diff de auditoría NUNCA registra campos derivados de joins. Con el fake ASIMÉTRICO.

POR QUÉ ESTE ARCHIVO EXISTE. Durante meses, cada edición de un empleado grabó un cambio que
no ocurrió: `area_nombre: "SALUD" → null`, `empresa_nombre: "..." → null`. 93 de 113 eventos
de producción eran exactamente eso y nada más, y la pantalla se lo afirmaba al usuario sobre
empleados reales. La causa era que el diff comparaba los *Response completos: `prior` sale de
un SELECT con joins (nombres resueltos) y `nuevo` de un `UPDATE ... RETURNING` (sin joins,
nombres en null).

🚨 POR QUÉ 899 TESTS NO LO VIERON, que es lo que hay que llevarse: el fake de empleados
construía `prior` y `updated` **con la misma factory**, así que los dos lados tenían los
nombres igual (ambos None) y el fantasma NO PODÍA aparecer. El fake no mentía sobre la
lógica: no modelaba la única diferencia que importaba. Es la misma clase de falso verde que
los fakes que aceptaban `empresa_id` y lo ignoraban.

**Todo fake de un repo con lecturas enriquecidas modela la asimetría**: `find_by_id` devuelve
la fila CON los campos de join, la escritura la devuelve SIN ellos. Si un fake nuevo no lo
hace, este bug puede volver sin que nada se ponga en rojo.
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

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from schemas.ausencias import AusenciaResponse
from schemas.empleado import EmpleadoResponse, EmpleadoUpdate
from schemas.vacaciones import SolicitudVacacionesResponse
from services._audit_payloads import payload_cancelacion_vacacion, payload_update_ausencia
from services._audit_payloads_rrhh import payload_update_empleado
from services.empleado_service import EmpleadoService

# Los campos que un *Response trae resueltos por join o calculados: NINGUNO puede aparecer
# jamás en un diff, en ninguna entidad.
DERIVADOS = {"area_nombre", "empresa_nombre", "empleado_nombre", "manager_nombre",
             "tipo_nombre", "estado_calculado"}


# ─── Empleado: el bug real, de punta a punta ──────────────────────────────────


def _empleado(*, con_joins: bool, **over) -> EmpleadoResponse:
    """Un empleado leído CON joins (nombres resueltos) o devuelto por un UPDATE (sin ellos)."""
    base = dict(
        id="emp1", nombre="Ana", apellido="Lopez", email_corporativo="a@x.com",
        empresa_id="e1", area_id="ar1", roles=["Dev"], cargo="Dev", seniority="Ssr",
        modalidad_trabajo="remoto", tipo_contrato="indefinido",
        fecha_ingreso=date(2025, 1, 1), estado="activo", created_at=datetime(2026, 1, 1, 9, 0),
    )
    base.update(over)
    if con_joins:
        base.update(area_nombre="SALUD", empresa_nombre="KARSTEC", manager_nombre="Perez, Juan")
    return EmpleadoResponse(**base)


class _RepoAsimetrico:
    """🚨 Modela la asimetría REAL del repo, que es lo que el fake viejo no hacía:

    · `find_by_id` → SELECT con joins  → area_nombre/empresa_nombre/manager_nombre RESUELTOS
    · `update`     → UPDATE ... RETURNING → esos tres en None

    Con un fake simétrico el fantasma no puede reproducirse y el test da verde sobre el bug.
    """

    def __init__(self, **cambios) -> None:
        self.prior = _empleado(con_joins=True)
        self.updated = _empleado(con_joins=False, **cambios)
        self.find_by_id_calls = 0

    def find_by_legajo(self, *a, **k):
        return None

    def find_by_id(self, _id, _empresa=None):
        self.find_by_id_calls += 1
        return self.prior

    def update(self, _id, _data, _empresa=None):
        return self.updated

    def save(self, _data, _empresa):
        return self.prior

    def soft_delete(self, _id, _empresa=None):
        return True


class _Audit:
    def __init__(self) -> None:
        self.calls: list = []

    def registrar(self, **kw) -> None:
        self.calls.append(kw)


class _AreaRepoPermisivo:
    """Permisivo A PROPÓSITO: este archivo cubre el diff de auditoría, no el gate de área
    (ese vive en test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


def _editar(repo, **campos) -> dict:
    audit = _Audit()
    svc = EmpleadoService(repo=repo, audit=audit, area_repo=_AreaRepoPermisivo())
    svc.update_empleado(uuid4(), EmpleadoUpdate(**campos), empresa_id=None, usuario_id="u1")
    return audit.calls[0]


class TestNoFabricaCambios:
    def test_un_update_que_no_toca_nada_no_registra_cambios(self) -> None:
        """EL TEST DEL BUG. Antes del fix esto grababa area_nombre y empresa_nombre pasando a
        null: un cambio que nadie hizo, mostrado como si alguien hubiera vaciado el área."""
        evento = _editar(_RepoAsimetrico())
        assert evento["datos_anteriores"] == {} and evento["datos_nuevos"] == {}

    def test_ningun_nombre_resuelto_por_join_entra_al_diff(self) -> None:
        evento = _editar(_RepoAsimetrico(roles=["Lead"]))
        assert not (DERIVADOS & set(evento["datos_nuevos"]))
        assert not (DERIVADOS & set(evento["datos_anteriores"]))


class TestRegistraLoQueSiCambio:
    """Los tres campos que el compromiso da por trackeados."""

    @pytest.mark.parametrize("campo,valor", [
        ("roles", ["Lead"]), ("area_id", "ar2"), ("seniority", "Sr"),
    ])
    def test_el_campo_cambiado_queda_registrado(self, campo: str, valor) -> None:
        evento = _editar(_RepoAsimetrico(**{campo: valor}))
        assert evento["datos_nuevos"][campo] == valor

    @pytest.mark.parametrize("campo,valor", [
        ("roles", ["Lead"]), ("area_id", "ar2"), ("seniority", "Sr"),
    ])
    def test_y_SOLO_ese_campo(self, campo: str, valor) -> None:
        """Que aparezca el campo no alcanza: si además viene el fantasma, el usuario sigue
        leyendo un cambio inventado al lado del real."""
        evento = _editar(_RepoAsimetrico(**{campo: valor}))
        assert set(evento["datos_nuevos"]) == {campo}

    def test_el_valor_anterior_es_el_verdadero(self) -> None:
        evento = _editar(_RepoAsimetrico(seniority="Sr"))
        assert evento["datos_anteriores"]["seniority"] == "Ssr"

    def test_no_se_pierden_las_columnas_fuera_de_la_lista_curada(self) -> None:
        """`_CAMPOS_EMPLEADO` (que usan alta y baja) cubre 7 campos; `empleados` tiene 29
        columnas editables más. Enumerar en vez de excluir dejaría de auditarlas EN SILENCIO."""
        evento = _editar(_RepoAsimetrico(manager_id="mgr9", dni="30111222"))
        assert {"manager_id", "dni"} <= set(evento["datos_nuevos"])


# ─── La regla vale para TODAS las entidades, no solo empleados ────────────────


def _ausencia(*, con_joins: bool, **over) -> AusenciaResponse:
    base = dict(
        id="a1", empresa_id="e1", empleado_id="emp1", tipo_id="t1",
        fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 3, 2), dias=2,
        justificada=True, motivo="Trámite", created_at=datetime(2026, 3, 1, 9, 0),
    )
    base.update(over)
    if con_joins:
        base.update(empresa_nombre="KARSTEC", empleado_nombre="Ana Lopez",
                    area_id="ar1", area_nombre="SALUD", tipo_nombre="Personal")
    return AusenciaResponse(**base)


def _vacacion(*, con_joins: bool, **over) -> SolicitudVacacionesResponse:
    base = dict(
        id="v1", empresa_id="e1", empleado_id="emp1", fecha_desde=date(2026, 3, 1),
        fecha_hasta=date(2026, 3, 5), dias=5, tipo="vacaciones", comentario=None,
        cancelada=False, estado="planificada", created_at=datetime(2026, 3, 1, 9, 0),
    )
    base.update(over)
    if con_joins:
        base.update(empresa_nombre="KARSTEC", empleado_nombre="Ana Lopez",
                    area_id="ar1", area_nombre="SALUD")
    return SolicitudVacacionesResponse(**base)


# (nombre, payload, prior, nuevo-sin-joins) — el barrido es explícito para que un payload
# nuevo tenga que sumarse a mano y no pase inadvertido.
ENTIDADES = [
    ("empleado", lambda: payload_update_empleado(
        _empleado(con_joins=True), _empleado(con_joins=False), "u1", "e1")),
    ("ausencia", lambda: payload_update_ausencia(
        _ausencia(con_joins=True), _ausencia(con_joins=False), "u1", "e1")),
    ("vacacion", lambda: payload_cancelacion_vacacion(
        _vacacion(con_joins=True), _vacacion(con_joins=False, cancelada=True), "u1", "e1")),
]


class TestTodasLasEntidades:
    def test_el_barrido_no_esta_vacio(self) -> None:
        assert len(ENTIDADES) >= 3

    @pytest.mark.parametrize("nombre,armar", ENTIDADES, ids=lambda v: v if isinstance(v, str) else "")
    def test_ningun_derivado_en_el_diff(self, nombre: str, armar) -> None:
        ev = armar()
        sucios = DERIVADOS & (set(ev["datos_anteriores"] or {}) | set(ev["datos_nuevos"] or {}))
        assert not sucios, f"{nombre} filtró campos de join al diff: {sorted(sucios)}"

    @pytest.mark.parametrize("nombre,armar", ENTIDADES[:2], ids=lambda v: v if isinstance(v, str) else "")
    def test_sin_cambios_reales_el_diff_queda_vacio(self, nombre: str, armar) -> None:
        """Las dos primeras entidades no cambian nada entre prior y nuevo: solo difieren en
        cómo se leyeron. Eso no es un cambio."""
        ev = armar()
        assert ev["datos_anteriores"] == {} and ev["datos_nuevos"] == {}

    def test_la_vacacion_cancelada_si_registra_su_cambio(self) -> None:
        """Contraprueba del test de arriba: cuando SÍ cambia algo real, se registra."""
        ev = ENTIDADES[2][1]()
        assert ev["datos_nuevos"] == {"cancelada": True}

    def test_el_estado_calculado_no_entra(self) -> None:
        """`estado` sale de las fechas y de `cancelada`: cambia solo con el paso del tiempo, y
        eso se leería como una edición que nadie hizo."""
        ev = ENTIDADES[2][1]()
        assert "estado" not in (ev["datos_nuevos"] or {})
