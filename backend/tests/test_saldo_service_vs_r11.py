"""
🔴 EL TEST QUE JUSTIFICA HABER UNIFICADO: la pantalla y el reporte R11 tienen que dar EL MISMO
NÚMERO para el mismo empleado.

Antes NO lo daban, y ninguna de las dos era obviamente la equivocada. R11 tenía cuatro
diferencias con el service, todas silenciosas:
  1. no filtraba por `tipo`, así que un permiso especial descontaba del saldo de vacaciones;
  2. no restaba los pedidos (las licencias planificadas a futuro);
  3. contaba las planificadas como tomadas;
  4. acotaba el consumo a UN MES contra un cupo ANUAL — restaba magnitudes distintas.
Ninguna daba error. Simplemente RRHH veía un número en la ficha y otro en el reporte.

Unificar el núcleo hace que no puedan divergir POR CÁLCULO, pero no impide que vuelvan a
divergir por los ADAPTADORES: los dos traducen filas a `Consumo` y lo hacen distinto (el
service con objetos Pydantic y `derive_estado`, R11 con dicts crudos y comparación de fechas).
Este test es lo que vigila esa costura. Si alguien toca un adaptador y no el otro, falla acá.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTO PUEDA FALLAR?
Los dos fakes sirven LA MISMA fila, así que cualquier asimetría que quede es del código y no
del doble. Y las fechas de los consumos están MUY en el pasado a propósito: el service corta
en `date.today()` y R11 al cierre del mes pedido, así que una licencia que cayera entre hoy y
fin de mes sería "planificada" para uno y "tomada" para el otro — una diferencia legítima que
enmascararía las ilegítimas. Con datos viejos, cualquier diferencia que aparezca es un bug.
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

from datetime import date
from types import SimpleNamespace

import services.reportes._reporte_saldos as vac
from schemas.vacaciones import SolicitudVacacionesResponse
from schemas.vacaciones_pendientes import VacacionPendienteResponse
from services._vacaciones_saldo import calcular_saldo

EMP = "e1"
INGRESO = "2019-03-10"
HOY = date.today()
# Períodos viejos pero DENTRO de la ventana de acumulación (hoy−4 … hoy), para que los
# consumos afecten saldo vigente y el test no compare dos ceros.
P_VIEJO, P_MEDIO = HOY.year - 3, HOY.year - 2

_SOLICITUDES = [
    # tomada, con período declarado
    {"empleado_id": EMP, "dias": 6, "cancelada": False, "tipo": "vacaciones",
     "periodo": P_VIEJO, "fecha_desde": f"{P_VIEJO}-04-01", "fecha_hasta": f"{P_VIEJO}-04-06"},
    # cancelada: no consume
    {"empleado_id": EMP, "dias": 3, "cancelada": True, "tipo": "vacaciones",
     "periodo": P_VIEJO, "fecha_desde": f"{P_VIEJO}-05-01", "fecha_hasta": f"{P_VIEJO}-05-03"},
    # sin período declarado (fila estilo pre-083) → la imputa el FIFO
    {"empleado_id": EMP, "dias": 4, "cancelada": False, "tipo": "vacaciones",
     "periodo": None, "fecha_desde": f"{P_MEDIO}-06-01", "fecha_hasta": f"{P_MEDIO}-06-04"},
    # 🔴 OTRO TIPO: no descuenta del saldo de VACACIONES. Esta fila la agregó el mutation check.
    # Sin ella, sacarle a R11 el `.eq("tipo", "vacaciones")` dejaba la suite entera en verde —
    # y ésa es LITERALMENTE la diferencia histórica #1 que este archivo dice vigilar. El fake
    # servía solo filas de vacaciones, así que el modo de falla que venía a cubrir no podía
    # aparecer: el caso #1 del manual, dentro del test escrito para evitarlo.
    {"empleado_id": EMP, "dias": 7, "cancelada": False, "tipo": "licencia_especial",
     "periodo": P_VIEJO, "fecha_desde": f"{P_VIEJO}-08-01", "fecha_hasta": f"{P_VIEJO}-08-07"},
]
# 10 días pendientes de los que se liquidaron 4 → consumen 4, no 10.
_PENDIENTES = [{"empleado_id": EMP, "periodo": P_MEDIO, "dias": 10, "dias_liquidados": 4,
                "empresa_id": "c1", "id": "p1", "comentario": None,
                "created_at": "2024-01-01T00:00:00Z"}]
_EMPLEADO = {"id": EMP, "estado": "activo", "area_id": "A", "nombre": "Ana", "apellido": "G",
             "fecha_ingreso": INGRESO, "fecha_ingreso_reconocida": None,
             "dias_vacaciones_asignados": None, "areas": {"nombre": "Tec"}}


class _VacRepo:
    """Sirve las MISMAS filas que el fake de R11, pero como responses Pydantic — que es la
    forma en la que las recibe el service."""

    def find_datos_para_saldo(self, empleado_id, empresa_id=None):
        return {k: _EMPLEADO[k] for k in
                ("fecha_ingreso", "fecha_ingreso_reconocida", "dias_vacaciones_asignados")}

    def find_vacaciones_empleado(self, empleado_id, empresa_id=None):
        # El repo real ya filtra cancelada=false Y tipo=vacaciones en el WHERE, así que el fake
        # los aplica los DOS. R11 no recibe esa cortesía: su fake sirve la tabla cruda y el
        # filtro lo tiene que poner su propia query — que es lo que hace comparable a los dos.
        return [SolicitudVacacionesResponse.model_validate(
            {**s, "id": f"s{i}", "empresa_id": "c1", "estado": "tomada",
             "created_at": "2024-01-01T00:00:00Z"})
            for i, s in enumerate(_SOLICITUDES)
            if not s["cancelada"] and s["tipo"] == "vacaciones"]


class _PenRepo:
    def find_by_empleado(self, empleado_id, empresa_id=None):
        return [VacacionPendienteResponse.model_validate(p) for p in _PENDIENTES]


class _Q:
    def __init__(self, rows):
        self._rows, self._eq, self._in = rows, {}, {}

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def eq(self, col, val):
        self._eq[col] = str(val)
        return self

    def in_(self, col, vals):
        self._in[col] = {str(v) for v in vals}
        return self

    def execute(self):
        data = [r for r in self._rows
                if all(str(r.get(c)) == v for c, v in self._eq.items())
                and all(str(r.get(c)) in vs for c, vs in self._in.items())]
        return SimpleNamespace(data=data, count=len(data))


class _DB:
    def __init__(self):
        self._t = {"empleados": [_EMPLEADO], "solicitudes_vacaciones": _SOLICITUDES,
                   "vacaciones_pendientes": _PENDIENTES}

    def table(self, name):
        return _Q(self._t.get(name, []))


def test_el_service_y_r11_dan_el_mismo_saldo(monkeypatch):
    """Los cuatro totales tienen que coincidir. Para que falle: reintroducir cualquiera de las
    cuatro diferencias históricas de R11, o tocar un adaptador y no el otro."""
    monkeypatch.setattr(vac, "supabase_admin", _DB())
    r11 = vac.generate_saldos_vacaciones(HOY.month, HOY.year, None, None)["saldos"][0]
    svc = calcular_saldo(_VacRepo(), EMP, None, _PenRepo())

    assert (r11["asignados"], r11["gozados"], r11["pedidos"], r11["disponibles"], r11["vencidos"]) \
        == (svc.asignados, svc.gozados, svc.pedidos, svc.disponibles, svc.vencidos), \
        f"R11 y el service divergen: {r11} vs {svc}"


def test_los_numeros_comparados_no_son_todos_cero():
    """🔴 GUARDA CONTRA EL FALSO VERDE. Comparar 0 == 0 pasaría con el cálculo entero roto.
    Los consumos del fake tienen que estar efectivamente descontando algo."""
    svc = calcular_saldo(_VacRepo(), EMP, None, _PenRepo())
    assert svc.asignados > 0, "sin cupo, la comparación no prueba nada"
    assert svc.gozados == 14, "6 declarados + 4 sin período + 4 liquidados del pendiente"
    assert svc.disponibles == svc.asignados - 14


def test_el_pendiente_aporta_solo_lo_liquidado_en_los_dos_caminos(monkeypatch):
    """La asimetría de `dias_liquidados` tiene que valer igual en R11 que en el service: el
    pendiente tiene 10 días y solo 4 liquidados, así que consume 4."""
    monkeypatch.setattr(vac, "supabase_admin", _DB())
    r11 = vac.generate_saldos_vacaciones(HOY.month, HOY.year, None, None)["saldos"][0]
    svc = calcular_saldo(_VacRepo(), EMP, None, _PenRepo())
    assert r11["gozados"] == svc.gozados == 14, "si consumiera los 10 daría 20"
