"""
Los dos consumidores de `objetivos` que viven FUERA del módulo y cuentan filas.

🔴 POR QUÉ ESTE ARCHIVO EXISTE. Desde la migración 095 los subobjetivos son filas de la MISMA
tabla `objetivos`. Dos lugares del backend cuentan esa tabla y ninguno está en el módulo, así
que no aparecen buscando "objetivo" en `routers/`:

  · `services/procesos_service.py` — el tablero de Procesos, conteo por estado.
  · `services/_reporte_anual_metricas.py` — "objetivos cumplidos" del reporte anual.

Sin el filtro `parent_id IS NULL`, un objetivo con 3 subtareas pasa a contar 4. Ninguno de los
dos ROMPE: los dos siguen devolviendo un número. Lo que cambia es qué significa ese número, en
silencio y sin que nada avise — "12 objetivos cumplidos" pasaría a ser "12 objetivos y
subtareas" y dejaría de ser comparable con el año pasado.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL ESPÍA REGISTRA LOS `.is_()` CON SUS ARGUMENTOS. La decisión "solo raíces" viaja como
     un predicado de la query, no como un post-filtro en Python: si se verificara el número
     devuelto en vez del predicado enviado, un fake que devuelva 1 haría pasar el test con el
     filtro borrado.
  2. 🔴 SE VERIFICA TAMBIÉN QUE LAS **OTRAS** TABLAS NO LLEVEN EL FILTRO. `parent_id` solo
     existe en `objetivos`; aplicárselo a `vacantes` o a `ev_ciclos` sería un 400 de Postgres en
     producción. Sin esa mitad, un `is_("parent_id","null")` incondicional —aplicado a las 7
     tablas del tablero— pasaría el test de arriba y rompería las otras seis.
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

from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

EMPRESA = uuid4()


class _Espia:
    """Cliente de Supabase falso que registra (tabla, is_) de cada consulta."""

    def __init__(self) -> None:
        self.consultas: list[dict] = []

    def table(self, nombre: str):
        registro = {"tabla": nombre, "is_": [], "eq": []}
        self.consultas.append(registro)
        espia = self

        class _Q:
            def select(self, *a, **k):
                return self

            def eq(self, col, val):
                registro["eq"].append((col, val))
                return self

            def is_(self, col, val):
                registro["is_"].append((col, val))
                return self

            def gte(self, *a, **k):
                return self

            def lte(self, *a, **k):
                return self

            def execute(self):
                return SimpleNamespace(data=[], count=0)

        del espia
        return _Q()

    def de(self, tabla: str) -> list[dict]:
        return [c for c in self.consultas if c["tabla"] == tabla]


@pytest.fixture
def espia(monkeypatch) -> _Espia:
    import services._reporte_anual_metricas as rep_mod
    import services.procesos_service as proc_mod

    fake = _Espia()
    monkeypatch.setattr(proc_mod, "supabase_admin", fake)
    monkeypatch.setattr(rep_mod, "supabase_admin", fake)
    return fake


# ── El tablero de Procesos ────────────────────────────────────────────────────

class TestProcesos:

    def test_las_consultas_a_objetivos_llevan_parent_id_null(self, espia) -> None:
        """🔴 Solo raíces: un objetivo con 3 subtareas no puede contar 4."""
        from services.procesos_service import ProcesosService

        ProcesosService().get_procesos(EMPRESA)

        de_objetivos = espia.de("objetivos")
        assert de_objetivos, "el tablero dejó de consultar objetivos"
        assert all(("parent_id", "null") in c["is_"] for c in de_objetivos)

    def test_las_OTRAS_tablas_NO_llevan_ese_filtro(self, espia) -> None:
        """🔴 `parent_id` solo existe en `objetivos`. Aplicárselo a las otras seis tablas del
        tablero sería un 400 de Postgres en producción, y el fake de Supabase no lo vería."""
        from services.procesos_service import ProcesosService

        ProcesosService().get_procesos(EMPRESA)

        otras = [c for c in espia.consultas if c["tabla"] != "objetivos"]
        assert len(otras) >= 6, "el barrido no miró las demás tablas del tablero"
        assert all(c["is_"] == [] for c in otras)

    def test_los_tres_estados_de_objetivos_se_cuentan_por_raiz(self, espia) -> None:
        """El tablero cuenta por_hacer / haciendo / terminado: los tres tienen que filtrar."""
        from services.procesos_service import ProcesosService

        ProcesosService().get_procesos(EMPRESA)

        estados = {e[1] for c in espia.de("objetivos") for e in c["eq"] if e[0] == "estado"}
        assert estados == {"por_hacer", "haciendo", "terminado"}
        assert len(espia.de("objetivos")) == 3

    def test_la_empresa_sigue_viajando(self, espia) -> None:
        """Contrapeso: el filtro nuevo no puede haber desplazado al que ya estaba."""
        from services.procesos_service import ProcesosService

        ProcesosService().get_procesos(EMPRESA)

        assert all(("empresa_id", str(EMPRESA)) in c["eq"] for c in espia.de("objetivos"))


# ── El reporte anual ──────────────────────────────────────────────────────────

class TestReporteAnual:

    def test_objetivos_cumplidos_cuenta_solo_raices(self, espia) -> None:
        """🔴 "12 objetivos cumplidos" tiene que seguir queriendo decir lo mismo que el año
        pasado. Con las subtareas adentro, el número deja de ser comparable consigo mismo."""
        from services._reporte_anual_metricas import actividad

        actividad(str(EMPRESA), "2026-01-01", "2026-12-31",
                  "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")

        de_objetivos = espia.de("objetivos")
        assert de_objetivos, "el reporte anual dejó de consultar objetivos"
        assert ("parent_id", "null") in de_objetivos[0]["is_"]

    def test_sigue_contando_solo_los_TERMINADOS(self, espia) -> None:
        """Contrapeso: el filtro nuevo no puede haber desplazado al de estado."""
        from services._reporte_anual_metricas import actividad

        actividad(str(EMPRESA), "2026-01-01", "2026-12-31",
                  "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")

        assert ("estado", "terminado") in espia.de("objetivos")[0]["eq"]

    def test_las_otras_metricas_del_reporte_no_llevan_parent_id(self, espia) -> None:
        from services._reporte_anual_metricas import actividad

        actividad(str(EMPRESA), "2026-01-01", "2026-12-31",
                  "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")

        otras = [c for c in espia.consultas if c["tabla"] != "objetivos"]
        assert otras and all(c["is_"] == [] for c in otras)
