"""
El panel "Requiere tu atención" (A6), por HTTP: las dos clases de alerta en una respuesta, los
dos ciclos de vida, y la barrera de empresa.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El doble es el `Almacen` de `test_eventos_agenda` — SE IMPORTA en vez de reescribirse, porque ya
modela lo que acá importa poder desmentir: el `or_` de visibilidad ejecutado de verdad, el CHECK
de resuelta, los defaults de columna y comparaciones `gte`/`lte` como strings ISO. Un segundo
doble más permisivo dejaría estos tests en verde con la visibilidad o la ventana rotas. (Moverlo
a un helper `tests/_*.py` es un refactor pendiente del módulo de eventos, no de esta sesión.)

Cada criterio lleva su CONTRASTE en el padrón: preingreso a 3 días Y a 30 (la ventana corta en
los dos sentidos), activo con ingreso reciente (el filtro de estado), fin de prueba a 2 días Y
uno viejo (el piso), evento resuelto (el ciclo manual), y empresa B entera (la barrera, con su
contracara consolidada). Un cálculo que devuelva todo o nada no puede acertar los conteos.

Verificado por reversión el 19/8/2026 (editar → correr → restaurar): sin `eq(estado,
'preingreso')` rojea (b); con la ventana en 60 días rojea el contraste de (a); sin el rechazo de
calculadas rojea (e); sin `creado_por_nombre` rojea (c); sin `_con_empresa` rojea (f); sin el
piso del fin de prueba rojea su contraste.
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

from datetime import date, timedelta  # noqa: E402
from typing import Optional  # noqa: E402
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import middleware.auth as auth_mod  # noqa: E402
import repositories._evento_agenda_row as ev_row_mod  # noqa: E402
import repositories._evento_agenda_write_repo as ev_write_mod  # noqa: E402
import repositories.configuracion_repo as config_mod  # noqa: E402
import repositories.evento_agenda_repo as ev_repo_mod  # noqa: E402
import services._dashboard_atencion_calculadas as calc_mod  # noqa: E402
from main import app  # noqa: E402
from tests.test_eventos_agenda import _PARAMETROS_GLOBAL, Almacen, _evento  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

_RUTA = "/api/dashboard/atencion"
_HOY = date.today()  # el endpoint no recibe fecha: toma el día real, así que se siembra relativo

YO, OTRO = str(uuid4()), str(uuid4())
EMPRESA, OTRA_EMPRESA = str(uuid4()), str(uuid4())
EV_MIO = "11111111-1111-1111-1111-11111111aaaa"
EV_OTRO = "11111111-1111-1111-1111-11111111bbbb"
EV_RESUELTO = "11111111-1111-1111-1111-11111111cccc"
EV_EMPRESA_B = "11111111-1111-1111-1111-11111111dddd"


def _empleado(nombre, apellido, estado, fecha_ingreso, empresa=EMPRESA):
    return {"id": str(uuid4()), "empresa_id": empresa, "nombre": nombre, "apellido": apellido,
            "estado": estado, "fecha_ingreso": str(fecha_ingreso)}


def _dias(n: int) -> date:
    return _HOY + timedelta(days=n)


# El padrón: cada fila es un criterio o su contraste (ver el encabezado).
def _padron() -> list:
    return [
        _empleado("Nadia", "Preingreso", "preingreso", _dias(3)),          # (a) aparece
        _empleado("Franco", "Lejano", "preingreso", _dias(30)),            # (a) contraste
        _empleado("Iris", "Activa", "activo", _dias(0)),                   # (b) no es ingreso
        _empleado("Pedro", "EnPrueba", "activo", _dias(-88)),              # prueba: fin en +2
        _empleado("Vera", "Antigua", "activo", _dias(-300)),               # prueba: contraste
        _empleado("Boris", "DeOtraEmpresa", "preingreso", _dias(3), OTRA_EMPRESA),  # (f)
        # Solo para el KPI de 30 días: fuera de LAS DOS ventanas. En el panel no cambia nada
        # (ya estaba afuera a los 7), y sin él "30 días" y "sin ventana" darían el mismo número.
        _empleado("Ulises", "Lejanisimo", "preingreso", _dias(45)),
    ]


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    a = Almacen(
        {
            "empleados": _padron(),
            # ⚠️ `empresa=` va EXPLÍCITA en las cuatro: el default de `_evento` es la EMPRESA
            # del módulo que lo define (test_eventos_agenda), no la de este archivo — sin esto,
            # los eventos quedan en una empresa fantasma y el panel sale vacío de manuales.
            "eventos_agenda": [
                _evento(EV_MIO, YO, True, str(_dias(2)), dias_aviso=7, empresa=EMPRESA,
                        nombre="Entrega ART"),
                _evento(EV_OTRO, OTRO, True, str(_dias(1)), dias_aviso=7, empresa=EMPRESA,
                        nombre="Auditoría anual"),
                _evento(EV_RESUELTO, YO, True, str(_dias(1)), dias_aviso=7, resuelta=True,
                        empresa=EMPRESA, nombre="Ya resuelto"),
                _evento(EV_EMPRESA_B, OTRO, True, str(_dias(1)), dias_aviso=7,
                        empresa=OTRA_EMPRESA, nombre="Evento de B"),
            ],
            "empresas": [{"id": EMPRESA, "nombre": "KARSTEC"},
                         {"id": OTRA_EMPRESA, "nombre": "DOSUBA"}],
            "users": [{"id": YO, "nombre": "Sofía", "apellido": "Gómez"},
                      {"id": OTRO, "nombre": "Julián", "apellido": "Paz"}],
            "parametros_empresa": [dict(_PARAMETROS_GLOBAL)],   # periodo_prueba_dias: 90
        },
        defaults={"eventos_agenda": {"resuelta": False, "resuelta_at": None,
                                     "resuelta_por": None, "descripcion": None}},
    )
    for mod in (calc_mod, ev_repo_mod, ev_row_mod, ev_write_mod, config_mod):
        monkeypatch.setattr(mod, "supabase_admin", a, raising=False)
    return a


@pytest.fixture
def como(monkeypatch, almacen):
    """Cliente HTTP autenticado. Se falsea la RESOLUCIÓN DE IDENTIDAD, nunca los gates ni el
    ruteo (molde: el `como` de test_eventos_agenda)."""
    def _fabrica(rol: str = "admin_rrhh", usuario: str = YO,
                 empresa_header: Optional[str] = EMPRESA):
        monkeypatch.setattr(auth_mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(auth_mod, "_verificar_token", lambda t, p: (usuario, "smoke@x.test"))
        monkeypatch.setattr(auth_mod, "estado_usuario",
                            lambda uid: EstadoUsuario(rol=rol, activo=True, resuelto=True))
        monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
        monkeypatch.setattr(auth_mod, "sesion_expirada", lambda e: False)
        monkeypatch.setattr(auth_mod, "resolver_empresa_id", lambda h, p: empresa_header)
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test")
    return _fabrica


async def _panel(como, **kw) -> list:
    async with como(**kw) as c:
        r = await c.get(_RUTA)
    assert r.status_code == 200, r.text
    return r.json()["alertas"]


def _mensajes(alertas) -> str:
    return " | ".join(a["mensaje"] for a in alertas)


# ─── (a) y (b): ingresos próximos ────────────────────────────────────────────

class TestIngresosProximos:
    async def test_a_3_dias_aparece_y_a_30_no(self, como) -> None:
        alertas = await _panel(como)
        ingresos = [a for a in alertas if a["tipo"] == "ingreso_proximo"]
        assert len(ingresos) == 1, _mensajes(alertas)
        assert "Nadia Preingreso" in ingresos[0]["mensaje"]
        assert "Franco Lejano" not in _mensajes(alertas), "la ventana dejó de cortar a los 7 días"

    async def test_un_activo_no_aparece_como_ingreso(self, como) -> None:
        """(b): el filtro es por ESTADO, no por fecha — Iris entró HOY y ya está activa."""
        alertas = await _panel(como)
        assert "Iris Activa" not in _mensajes([a for a in alertas
                                               if a["tipo"] == "ingreso_proximo"])

    async def test_la_calculada_es_calculada_y_sin_autor(self, como) -> None:
        ingreso = next(a for a in await _panel(como) if a["tipo"] == "ingreso_proximo")
        assert ingreso["origen"] == "calculada"
        assert ingreso["creado_por_nombre"] is None
        assert ingreso["evento_id"] is None, "una calculada no tiene fila que resolver"


class TestElKPIDeIngresosProximos:
    """El KPI "Ingresos próximos 30 días" (§6) — `contar_ingresos_proximos`.

    🔴 Vive en este archivo y no en uno del dashboard porque comparte MÓDULO y PREDICADO con el
    panel de arriba: son la misma query con otra ventana (`_preingresos_hasta`). Probarlo aparte
    con su propio padrón dejaría que las dos ventanas se separaran sin que ningún test lo viera,
    que es exactamente lo que el módulo se ocupa de impedir.

    El padrón discrimina en los tres ejes: +3 y +30 adentro, +45 afuera (la ventana), Iris activa
    con ingreso HOY afuera (el estado) y Boris en la otra empresa (la barrera).
    """

    def test_cuenta_los_de_30_dias_y_no_a_los_que_ya_entraron(self, almacen) -> None:
        """El test (d) de la sesión.

        Para que falle: perder el `eq(estado, 'preingreso')` —entraría Iris, que YA entró, y
        también los cuatro activos del padrón—, o ensanchar la ventana (entraría Ulises).
        """
        assert calc_mod.contar_ingresos_proximos(EMPRESA, _HOY) == 2

    def test_la_ventana_del_KPI_es_MAS_ANCHA_que_la_del_panel(self, almacen) -> None:
        """El contraste: Franco (+30) está afuera del panel y adentro del KPI. Si alguien
        cableara el KPI a `VENTANA_DIAS`, los dos números se igualarían y esto rojea."""
        panel = len(calc_mod.ingresos_proximos(EMPRESA, _HOY))
        assert calc_mod.contar_ingresos_proximos(EMPRESA, _HOY) > panel == 1

    def test_respeta_la_empresa_del_sidebar(self, almacen) -> None:
        """Boris es preingreso a +3 en la otra empresa: suma en consolidado, no en EMPRESA."""
        assert calc_mod.contar_ingresos_proximos(None, _HOY) == 3
        assert calc_mod.contar_ingresos_proximos(OTRA_EMPRESA, _HOY) == 1


# ─── Fin de período de prueba ────────────────────────────────────────────────

class TestFinDePrueba:
    async def test_a_2_dias_del_fin_aparece(self, como) -> None:
        """Pedro entró hace 88 días; con `periodo_prueba_dias=90` (parámetro de empresa, mig
        114) su fin cae en 2 días — dentro de la ventana."""
        pruebas = [a for a in await _panel(como) if a["tipo"] == "fin_periodo_prueba"]
        assert len(pruebas) == 1 and "Pedro EnPrueba" in pruebas[0]["mensaje"]

    async def test_un_periodo_ya_vencido_no_aparece(self, como) -> None:
        """El PISO (la asimetría con ingresos): el fin de prueba de Vera pasó hace 210 días —
        terminó solo, no hay acción pendiente que recordar."""
        assert "Vera Antigua" not in _mensajes(await _panel(como))


# ─── (c) y (g): las dos clases conviven, distinguibles ───────────────────────

class TestLasDosClases:
    async def test_una_sola_respuesta_con_los_dos_origenes(self, como) -> None:
        alertas = await _panel(como)
        origenes = {a["origen"] for a in alertas}
        assert origenes == {"calculada", "manual"}, _mensajes(alertas)

    async def test_las_manuales_traen_el_autor_y_las_calculadas_no(self, como) -> None:
        alertas = await _panel(como)
        por_nombre = {a["mensaje"]: a for a in alertas}
        assert por_nombre["Entrega ART"]["creado_por_nombre"] == "Sofía Gómez"
        assert por_nombre["Auditoría anual"]["creado_por_nombre"] == "Julián Paz"
        assert all(a["creado_por_nombre"] is None for a in alertas
                   if a["origen"] == "calculada")

    async def test_el_evento_resuelto_no_esta(self, como) -> None:
        assert "Ya resuelto" not in _mensajes(await _panel(como))


# ─── (d) y (e): los dos ciclos de vida ───────────────────────────────────────

class TestResolver:
    async def test_resolver_una_manual_la_saca_de_la_lista(self, como) -> None:
        async with como() as c:
            antes = (await c.get(_RUTA)).json()["alertas"]
            r = await c.post(f"{_RUTA}/resolver", json={"origen": "manual",
                                                        "evento_id": EV_MIO})
            assert r.status_code == 200, r.text
            despues = (await c.get(_RUTA)).json()["alertas"]
        assert "Entrega ART" in _mensajes(antes)
        assert "Entrega ART" not in _mensajes(despues)
        assert "Auditoría anual" in _mensajes(despues), \
            "el contraste: resolvió UNA, no vació el panel"

    async def test_una_calculada_no_se_resuelve_a_mano(self, como) -> None:
        """(e) El otro ciclo de vida, con código PROPIO: una calculada no tiene fila — su
        'resuelto' no se puede persistir y la misma causa la levantaría mañana."""
        async with como() as c:
            r = await c.post(f"{_RUTA}/resolver", json={"origen": "calculada"})
        assert r.status_code == 409
        assert r.json()["code"] == "ALERTA_NO_RESOLUBLE"  # contrato plano {error, message, code}

    async def test_manual_sin_evento_id_es_422(self, como) -> None:
        async with como() as c:
            r = await c.post(f"{_RUTA}/resolver", json={"origen": "manual"})
        assert r.status_code == 422

    async def test_gerencia_lectura_no_resuelve(self, como) -> None:
        """El gate del resolver es EVENTOS + WRITE (resuelve un evento, no 'usa el dashboard')."""
        async with como(rol="gerencia_lectura") as c:
            r = await c.post(f"{_RUTA}/resolver", json={"origen": "manual",
                                                        "evento_id": EV_MIO})
        assert r.status_code == 403


# ─── (f) la barrera de empresa, con su contracara consolidada ────────────────

class TestBarreraDeEmpresa:
    async def test_con_header_de_empresa_no_se_ve_nada_de_la_otra(self, como) -> None:
        textos = _mensajes(await _panel(como, empresa_header=EMPRESA))
        assert "Boris DeOtraEmpresa" not in textos
        assert "Evento de B" not in textos

    async def test_consolidado_ve_las_dos_empresas(self, como) -> None:
        """Header None = vista consolidada: NO es un fallo de validación, es 'todas'."""
        textos = _mensajes(await _panel(como, empresa_header=None))
        assert "Boris DeOtraEmpresa" in textos and "Nadia Preingreso" in textos
        assert "Evento de B" in textos and "Entrega ART" in textos
