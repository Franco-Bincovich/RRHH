"""
Las DOS superficies vivas que consultaban tablas `ev_*` y sobrevivieron al bloque J5a.

## 🔴 POR QUÉ ESTE ARCHIVO EXISTE

Borrar el módulo `ev_*` no era solo borrar sus 17 archivos: **dos features que no son de
evaluaciones le consultaban las tablas**, y ninguna de las dos degradaba.

  1. **Panel de Procesos** (`services/procesos_service.py`) — contaba `ev_ciclos` y
     `ev_instancias`. Arma los procesos en UNA list-comprehension dentro de UN try/except, así
     que una tabla que no responde no deja la fila vacía: levanta `PROCESOS_ERROR` y **se lleva
     el panel entero**. Los otros cinco procesos, que están perfectos, dejan de verse.
  2. **Reporte anual** (`services/_reporte_anual_metricas.actividad`) — contaba
     `ev_instancias` finalizadas. No tiene try/except en ningún escalón: el informe entero
     dejaba de generarse.

Las dos son el mismo bug con distinta cara: **una tabla que desaparece se lleva puesta una
pantalla que no tiene nada que ver con ella.** Estos tests son lo que impide que la migración
de J5b —que dropea las tablas de verdad— reintroduzca cualquiera de los dos.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

**`_SupabaseSoloTablasVivas` LEVANTA ante una tabla que no conoce, en vez de devolver 0.**
Es la única propiedad que hace que estos tests signifiquen algo, y es exactamente la que un
fake escrito sin pensar NO tendría: el camino cómodo es `return count 0` para cualquier tabla,
y con eso `/procesos` seguiría respondiendo 200 **con `ev_ciclos` todavía en `_META`**. O sea:
el test pasaría verde sobre el bug que vino a cubrir, que es el caso #1 de la regla transversal
del repo. Al levantar, el fake reproduce lo que hace PostgREST contra una relación inexistente,
y por eso la mutación —volver a meter una tabla muerta en `_META`— lo rojea.

**🚨 CÓMO RE-CORRER LA MUTACIÓN, QUE NO ES OBVIO.** Para reproducir el escenario real de J5b
—tabla dropeada, código que todavía la lista— hay que agregar la tabla muerta a **`_META` Y a
`_ESTADOS`**, no solo a `_META`. `_build_proceso` evalúa `_ESTADOS[tabla]` ANTES de llamar a
`_count`, así que una mutación solo en `_META` muere de `KeyError` sin llegar a consultar nada:
rojea el primer test (por el 500) pero **deja pasar el segundo**, y da la impresión falsa de que
el segundo no sirve. Con la tabla en las dos estructuras rojean los dos, cada uno por su motivo
—500 `PROCESOS_ERROR` y `assert not ['ev_ciclos']`—, que es la señal de que el fake alcanza el
camino que importa.

**Y la pregunta previa (L9): ¿el fake ES lo que estoy probando?** No. Lo que se prueba es
`_META`/`_ESTADOS` y el dict de retorno de `actividad()`, que son código real y no se tocan
acá. El fake solo ocupa el lugar de la red. Por eso los dos tests entran por **HTTP contra la
app real** —middleware, router, `require_permission`, service— y no llamando al service con un
doble: el 500 del Panel de Procesos NACE en el try/except del service, y un test que invocara
`get_procesos()` directamente lo vería igual, pero no probaría que el endpoint que el front
consume devuelve 200. La ruta importa tanto como el resultado.
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

from datetime import datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import main as main_mod  # noqa: E402
import services._reporte_anual_metricas as metricas_mod  # noqa: E402
import services.procesos_service as procesos_mod  # noqa: E402
import services.reporte_anual as anual_mod  # noqa: E402
from routers.reportes import _service as _reportes_svc  # noqa: E402
from schemas.reporte import ReporteResponse  # noqa: E402
from services.reporte_service import ReporteService  # noqa: E402
from utils.rate_limit import limiter  # noqa: E402

_USER_ID = str(uuid4())

# Las tablas VIVAS que las dos superficies consultan, con las filas que devuelve cada una.
# `ev_ciclos`/`ev_instancias` NO están: ese es el punto.
_FILAS_POR_TABLA: dict[str, int] = {
    "onboarding_instancias": 3,
    "offboarding_instancias": 2,
    "vacantes": 1,
    "empleado_capacitacion": 7,
    "objetivos": 5,
    "empleados": 31,
    "areas": 12,
    "solicitudes_vacaciones": 0,
}


class _SupabaseSoloTablasVivas:
    """Cliente falso que conoce SOLO las tablas que existen después de J5b.

    🔴 `table()` LEVANTA ante una desconocida — no devuelve 0. Ver el encabezado: si devolviera
    0, `/procesos` respondería 200 con `ev_ciclos` todavía en `_META` y el test sería vacuo.
    El mensaje imita al de PostgREST para que un fallo se lea igual que en producción.
    """

    def __init__(self) -> None:
        self.consultadas: list[str] = []

    def table(self, nombre: str):
        self.consultadas.append(nombre)
        if nombre not in _FILAS_POR_TABLA:
            raise RuntimeError(f'relation "public.{nombre}" does not exist')
        return _Query(_FILAS_POR_TABLA[nombre])


class _Query:
    """Encadenable y neutral: acá no se mide el filtrado, se mide qué tablas se tocan."""

    def __init__(self, filas: int) -> None:
        self._filas = filas

    def select(self, *a, **k):
        return self

    def eq(self, *a):
        return self

    def gte(self, *a):
        return self

    def lte(self, *a):
        return self

    def is_(self, *a):
        return self

    def execute(self):
        return SimpleNamespace(count=self._filas, data=[{"id": str(uuid4()), "nombre": "Área",
                                                         "dias": 0, "area_id": None}] * self._filas)


class _RepoReportesFalso:
    """Solo la persistencia. Devuelve el reporte que RECIBE, nunca uno prefabricado: si el
    service guardara otra cosa, el assert de abajo lo vería."""

    def save(self, nombre, tipo, datos, generado_por, empresa_id=None, **k) -> ReporteResponse:
        self.guardado = datos
        return ReporteResponse(id=uuid4(), nombre=nombre, tipo=tipo, datos=datos,
                               generado_por=generado_por, created_at=datetime.now(),
                               empresa_id=empresa_id)


@pytest.fixture
def app_autenticada(monkeypatch):
    """App REAL con la verificación de identidad falseada — no la autorización.

    Se falsea solo lo que necesita red (firma del JWT contra el JWKS, estado del usuario en la
    base). `require_permission` y el resto del middleware corren de verdad: si el gate de
    `Seccion.PROCESOS` estuviera mal, estos tests darían 403 y no 200.
    """
    import middleware.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_verificar_token", lambda *_a, **_k: _USER_ID)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda *_a: SimpleNamespace(rol="admin_rrhh", activo=True, resuelto=True))
    monkeypatch.setattr(auth_mod, "sesion_expirada", lambda *_a: False)
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda *_a: None)
    monkeypatch.setattr(auth_mod, "resolver_empresa_id", lambda *_a, **_k: None)

    limiter.reset()
    yield main_mod.app
    main_mod.app.dependency_overrides.clear()
    limiter.reset()


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": "Bearer token-de-prueba"},
    )


class TestPanelDeProcesosSobrevivioAlBorradoDeEv:
    async def test_responde_200_con_los_cinco_procesos_restantes(
        self, app_autenticada, monkeypatch
    ) -> None:
        """El panel entero, no una fila: el try/except de `get_procesos` es todo-o-nada."""
        fake = _SupabaseSoloTablasVivas()
        monkeypatch.setattr(procesos_mod, "supabase_admin", fake)

        async with _client(app_autenticada) as c:
            r = await c.get("/api/procesos")

        assert r.status_code == 200, r.text
        procesos = r.json()["procesos"]
        assert [p["proceso"] for p in procesos] == [
            "onboarding", "offboarding", "vacantes", "capacitaciones", "objetivos",
        ]

    async def test_no_consulta_ninguna_tabla_ev(self, app_autenticada, monkeypatch) -> None:
        """El reverso del anterior. Sin esto, el test de arriba pasaría igual si `_META`
        conservara una tabla `ev_*` que por casualidad estuviera en `_FILAS_POR_TABLA`."""
        fake = _SupabaseSoloTablasVivas()
        monkeypatch.setattr(procesos_mod, "supabase_admin", fake)

        async with _client(app_autenticada) as c:
            await c.get("/api/procesos")

        assert fake.consultadas, "el fake no registró ninguna consulta: el camino no se recorrió"
        assert not [t for t in fake.consultadas if t.startswith("ev_")]


class TestReporteAnualSeGeneraSinLaMetricaDeEv:
    async def test_responde_201_y_no_trae_evaluaciones_finalizadas(
        self, app_autenticada, monkeypatch
    ) -> None:
        """La métrica se sacó, no se reapuntó: la clave no tiene que existir, ni en las hojas
        del Excel ni en los campos planos del fallback PDF."""
        fake = _SupabaseSoloTablasVivas()
        monkeypatch.setattr(metricas_mod, "supabase_admin", fake)
        monkeypatch.setattr(anual_mod, "supabase_admin", fake)
        app_autenticada.dependency_overrides[_reportes_svc] = (
            lambda: ReporteService(_RepoReportesFalso())
        )

        async with _client(app_autenticada) as c:
            r = await c.post("/api/reportes/generar",
                             json={"tipo": "anual_consolidado", "anio": 2026})

        assert r.status_code == 201, r.text
        datos = r.json()["datos"]
        assert "evaluaciones_finalizadas" not in datos
        assert "Evaluaciones finalizadas" not in datos["_sheets"]["Actividad del año"]
        # el control del control: la hoja existe y trae las métricas que SÍ quedaron
        assert "Capacitaciones completadas" in datos["_sheets"]["Actividad del año"]

    async def test_no_consulta_ninguna_tabla_ev(self, app_autenticada, monkeypatch) -> None:
        fake = _SupabaseSoloTablasVivas()
        monkeypatch.setattr(metricas_mod, "supabase_admin", fake)
        monkeypatch.setattr(anual_mod, "supabase_admin", fake)
        app_autenticada.dependency_overrides[_reportes_svc] = (
            lambda: ReporteService(_RepoReportesFalso())
        )

        async with _client(app_autenticada) as c:
            await c.post("/api/reportes/generar",
                         json={"tipo": "anual_consolidado", "anio": 2026})

        assert fake.consultadas, "el fake no registró ninguna consulta: el camino no se recorrió"
        assert not [t for t in fake.consultadas if t.startswith("ev_")]
