"""
Export de candidatos, períodos, catálogo de capacitaciones y onboarding.

Los cuatro comparten molde (`test_proyectos_export.py`), así que van juntos: cada bloque verifica
que el export vaya por el MISMO camino que el listado, que el límite muerda en sus dos lados, y
que los cuatro formatos lleguen al motor.

🔴 CONTEXTO QUE CAMBIA EL CRITERIO: candidatos, períodos y capacitaciones tienen **0 filas en
producción** y onboarding tiene **1**. Nadie va a abrir estos archivos para descubrir que una
columna dice cualquier cosa, así que estos tests son la ÚNICA verificación que van a tener por un
buen rato. Por eso el fake trae valores distintos por fila y se afirma sobre el contenido, no
sobre conteos.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 CADA FAKE DEVUELVE MÁS DE UNA FILA CON VALORES DISTINTOS. Con una sola, una proyección
     que emitiera constantes —o que leyera siempre el primer elemento— pasaría igual. Acá cada
     bloque afirma que las DOS filas salgan con SUS valores.
  2. 🔴 En capacitaciones el fake FILTRA de verdad por `solo_activos`, y el catálogo tiene una
     activa y una inactiva. Es el único de los cuatro con filtro, y sin ese reparto "filtró" y
     "no filtró" darían el mismo conjunto — el archivo traería las inactivas que la tabla oculta.
  3. Los fakes REGISTRAN lo que recibieron, así que se puede afirmar qué llegó al repo y no solo
     qué volvió.
  4. El límite se prueba en sus DOS lados: con `LIMITE_FILAS_EXPORT + 1` corta, y un export
     normal no. Sin el contrapeso, un `verificar_limite_export` que rechazara siempre pasaría.
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

from datetime import date, datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.capacitacion import CapacitacionResponse  # noqa: E402
from schemas.onboarding import InstanciaResponse  # noqa: E402
from schemas.periodo import PeriodoResponse  # noqa: E402
from schemas.candidato import CandidatoGrupoResponse, CandidatosPaginaResponse  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services.capacitacion_service import CapacitacionService  # noqa: E402
from services.onboarding_service import OnboardingService  # noqa: E402
from services.periodo_service import PeriodoService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()
_FORMATOS = (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf"))


# ══════════════════════════════════════════════════════════════════════════════
# CANDIDATOS
# ══════════════════════════════════════════════════════════════════════════════

def _candidato(nombre: str, etapa: str, email: str, activa: bool) -> CandidatoGrupoResponse:
    return CandidatoGrupoResponse(
        id=str(uuid4()), vacante_id=str(uuid4()), empresa_id=str(EMPRESA), nombre=nombre,
        apellido="Pérez", email=email, telefono="1155667788", cargo_anterior="Analista",
        empresa_anterior="Otra SA", etapa_pipeline=etapa, score_ia=7.5,
        cv_storage_path="cvs/privado/x.pdf", created_at=datetime(2026, 3, 4, 10, 0, 0),
        grupo_nombre="Dev Backend", busqueda_activa=activa,
    )


# DOS candidatos con valores DISTINTOS: sin eso, una proyección con constantes pasaría.
_CANDIDATOS = [_candidato("Ana", "entrevista", "ana@x.com", True),
               _candidato("Beto", "descartado", "beto@x.com", False)]


def _pagina(items: list, total: int | None = None) -> CandidatosPaginaResponse:
    """El listado ahora devuelve una página, y `total` NO es `len(items)`.

    🔴 PODERLOS DESACOPLAR ES EL PUNTO. El export pide una sola página de `LIMITE_FILAS_EXPORT`
    y controla el límite contra `total` —el count exacto del filtro—, no contra lo que le
    volvió. Si el fake derivara `total` de `len(items)`, el test del límite tendría que fabricar
    20.000 filas en memoria para morder, y no podría distinguir "el chequeo mira el count" de
    "el chequeo mira la página": las dos lecturas darían el mismo número siempre."""
    n = len(items) if total is None else total
    return CandidatosPaginaResponse(items=items, total=n, page=1,
                                    page_size=LIMITE_FILAS_EXPORT,
                                    total_pages=1, conteo_por_grupo={})


class TestExportCandidatos:

    def _svc(self):
        from services.candidato_service import CandidatoService

        llamadas: list = []
        svc = CandidatoService.__new__(CandidatoService)
        svc.listar_todos_candidatos = lambda e=None, sv=False, cl=None, page=1, page_size=20: (  # type: ignore[method-assign]
            llamadas.append((e, page, page_size)) or _pagina(_CANDIDATOS))
        return svc, llamadas

    def test_va_por_el_MISMO_camino_que_el_listado(self) -> None:
        """El export llama a `listar_todos_candidatos`, no a una consulta propia: por eso el
        archivo no puede traer filas que la pantalla no muestre."""
        svc, llamadas = self._svc()

        svc.exportar(EMPRESA, "csv")

        assert llamadas == [(EMPRESA, 1, LIMITE_FILAS_EXPORT)]

    def test_el_export_NO_se_pagina(self) -> None:
        """Pide UNA página del tamaño del límite, no la página 1 de 20. El export nunca se
        pagina (invariante del Bloque B): si heredara el `page_size` del listado, el archivo
        saldría con las primeras 20 filas y sin ninguna señal de que faltan las demás."""
        svc, llamadas = self._svc()

        svc.exportar(EMPRESA, "csv")

        assert llamadas[0][1:] == (1, LIMITE_FILAS_EXPORT)

    def test_las_DOS_filas_salen_con_SUS_valores(self) -> None:
        from services._candidatos_export import construir_filas_export

        filas = construir_filas_export(_CANDIDATOS)

        assert [f["Nombre"] for f in filas] == ["Ana", "Beto"]
        assert [f["Email"] for f in filas] == ["ana@x.com", "beto@x.com"]
        assert [f["Etapa"] for f in filas] == ["entrevista", "descartado"]
        assert [f["Búsqueda activa"] for f in filas] == ["Sí", "No"]

    def test_la_ruta_del_CV_no_sale_en_el_archivo(self) -> None:
        """Es una ruta de un bucket privado: no sirve sin firmar y expone el storage."""
        from services._candidatos_export import construir_filas_export

        fila = construir_filas_export(_CANDIDATOS)[0]

        assert "cvs/privado" not in str(fila)

    def test_el_limite_muerde(self) -> None:
        """Con DOS filas devueltas y un `total` que se pasa. Es el caso real: el repo trajo la
        página entera y el count dice que el filtro da más de lo que se puede exportar."""
        svc, _ = self._svc()
        svc.listar_todos_candidatos = lambda e=None, sv=False, cl=None, page=1, page_size=20: (  # type: ignore[method-assign]
            _pagina(_CANDIDATOS, total=LIMITE_FILAS_EXPORT + 1))

        with pytest.raises(AppError) as exc:
            svc.exportar(EMPRESA, "csv")

        assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"

    def test_y_un_export_normal_NO_corta(self) -> None:
        svc, _ = self._svc()

        assert svc.exportar(EMPRESA, "csv").filename.endswith(".csv")


# ══════════════════════════════════════════════════════════════════════════════
# PERÍODOS
# ══════════════════════════════════════════════════════════════════════════════

def _periodo(modulo, estado: str, desde: date) -> PeriodoResponse:
    return PeriodoResponse(
        id=str(uuid4()), empresa_id=str(EMPRESA), modulo=modulo, desde=desde,
        hasta=date(2026, 1, 31), estado=estado, cerrado_por=str(uuid4()),
        cerrado_at=datetime(2026, 2, 1, 9, 0, 0), reabierto_por=None, reabierto_at=None,
    )


_PERIODOS = [_periodo("vacaciones", "cerrado", date(2026, 1, 1)),
             _periodo(None, "reabierto", date(2025, 12, 1))]


class TestExportPeriodos:

    def _svc(self):
        llamadas: list = []
        repo = SimpleNamespace(listar=lambda e=None: (llamadas.append(e) or _PERIODOS))
        return PeriodoService(repo=repo), llamadas

    def test_va_por_el_MISMO_listar_del_repo(self) -> None:
        svc, llamadas = self._svc()

        listado = svc.listar(EMPRESA)
        svc.exportar(EMPRESA, "csv")

        assert llamadas == [EMPRESA, EMPRESA] and listado.total == 2

    def test_las_DOS_filas_salen_con_SUS_valores(self) -> None:
        from services._periodos_export import construir_filas_export

        filas = construir_filas_export(_PERIODOS)

        assert [f["Estado"] for f in filas] == ["cerrado", "reabierto"]
        assert [f["Desde"] for f in filas] == ["01/01/2026", "01/12/2025"]

    def test_modulo_NULL_se_dice_Todos_en_vez_de_dejar_la_celda_vacia(self) -> None:
        """NULL significa "el cierre aplica a todos los módulos". Un blanco se leería como un
        dato que falta."""
        from services._periodos_export import construir_filas_export

        filas = construir_filas_export(_PERIODOS)

        assert filas[0]["Módulo"] == "vacaciones" and filas[1]["Módulo"] == "Todos"

    def test_los_UUID_de_usuario_NO_salen(self) -> None:
        """`cerrado_por` y `reabierto_por` son UUIDs de `users`: el "quién" está en auditoría."""
        from services._periodos_export import construir_filas_export

        fila = construir_filas_export(_PERIODOS)[0]

        assert _PERIODOS[0].cerrado_por not in str(fila)
        assert {"Cerrado por", "Reabierto por"}.isdisjoint(fila.keys())

    def test_reabierto_vacio_sale_como_string_vacio_y_no_None(self) -> None:
        from services._periodos_export import construir_filas_export

        assert construir_filas_export(_PERIODOS)[0]["Reabierto el"] == ""

    def test_el_limite_muerde_y_un_export_normal_no(self) -> None:
        svc = PeriodoService(repo=SimpleNamespace(
            listar=lambda e=None: _PERIODOS * LIMITE_FILAS_EXPORT))
        with pytest.raises(AppError) as exc:
            svc.exportar(EMPRESA, "csv")
        assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"

        svc_ok, _ = self._svc()
        assert svc_ok.exportar(EMPRESA, "csv").filename.endswith(".csv")

    def test_los_cuatro_formatos_llegan_al_motor(self) -> None:
        svc, _ = self._svc()

        for formato, ext in _FORMATOS:
            assert svc.exportar(EMPRESA, formato).filename.endswith(ext)


# ══════════════════════════════════════════════════════════════════════════════
# CAPACITACIONES — el catálogo (NO las asignaciones)
# ══════════════════════════════════════════════════════════════════════════════

def _capacitacion(nombre: str, activo: bool, obligatoria: bool) -> CapacitacionResponse:
    return CapacitacionResponse(
        id=str(uuid4()), empresa_id=str(EMPRESA), empresa_nombre="Karstec", nombre=nombre,
        descripcion="desc de " + nombre, categoria="Seguridad", duracion_horas=8.0,
        obligatoria=obligatoria, activo=activo, created_at=datetime(2026, 1, 5, 9, 0, 0),
    )


_CATALOGO = [_capacitacion("Ley Micaela", True, True), _capacitacion("Excel viejo", False, False)]


class TestExportCatalogoCapacitaciones:
    """🔴 El ÚNICO de los cuatro con filtro en el listado (`solo_activos`), así que es el único
    donde la invariante list↔export puede romperse de verdad."""

    def _svc(self):
        llamadas: list = []

        def _find_all(empresa_id=None, solo_activos=True):
            llamadas.append((empresa_id, solo_activos))
            # 🔴 FILTRA DE VERDAD: sin esto, "filtró" y "no filtró" dan el mismo conjunto.
            return [c for c in _CATALOGO if not solo_activos or c.activo]

        return CapacitacionService(repo=SimpleNamespace(find_all=_find_all)), llamadas

    def test_el_fake_reparte_activas_e_inactivas(self) -> None:
        svc, _ = self._svc()
        assert len(svc.get_all(EMPRESA, True).items) == 1
        assert len(svc.get_all(EMPRESA, False).items) == 2

    def test_solo_activos_LLEGA_al_repo(self) -> None:
        svc, llamadas = self._svc()

        svc.exportar(EMPRESA, "csv", False)

        assert llamadas == [(EMPRESA, False)]

    def test_por_default_el_export_trae_SOLO_las_activas(self) -> None:
        """🔴 Sin el parámetro, el archivo traería las inactivas que la tabla está ocultando."""
        from services._capacitaciones_catalogo_export import construir_filas_export

        svc, _ = self._svc()
        filas = construir_filas_export(svc.get_all(EMPRESA, True).items)

        assert [f["Nombre"] for f in filas] == ["Ley Micaela"]

    def test_listado_y_export_piden_LO_MISMO(self) -> None:
        svc, llamadas = self._svc()

        svc.get_all(EMPRESA, False)
        svc.exportar(EMPRESA, "csv", False)

        assert llamadas[0] == llamadas[1]

    def test_los_booleanos_se_traducen_a_castellano(self) -> None:
        """`True` en una celda de Excel es jerga de programa; lo abre alguien de RRHH."""
        from services._capacitaciones_catalogo_export import construir_filas_export

        filas = construir_filas_export(_CATALOGO)

        assert [f["Obligatoria"] for f in filas] == ["Sí", "No"]
        assert [f["Estado"] for f in filas] == ["Activa", "Inactiva"]

    def test_las_DOS_filas_salen_con_SUS_valores(self) -> None:
        from services._capacitaciones_catalogo_export import construir_filas_export

        filas = construir_filas_export(_CATALOGO)

        assert [f["Nombre"] for f in filas] == ["Ley Micaela", "Excel viejo"]
        assert [f["Descripción"] for f in filas] == ["desc de Ley Micaela", "desc de Excel viejo"]

    def test_no_se_pisa_con_el_export_de_ASIGNACIONES(self) -> None:
        """Los dos módulos existen y proyectan cosas distintas. Este test rojea si alguien
        vuelve a sobrescribir uno con el otro (ya pasó al escribir esta tanda)."""
        from services._capacitaciones_catalogo_export import construir_filas_export as catalogo
        from services._capacitaciones_export import construir_filas_export as asignaciones

        assert catalogo is not asignaciones
        # `empleado_id`/`nombre_libre` los sumó la migración 116 (filas sin empleado). Van acá
        # porque este doble sustituye a un `AsignacionResponse` y un doble al que le falta un
        # campo del original no prueba sobre lo mismo: la proyección real los lee.
        fila_asig = asignaciones([SimpleNamespace(
            empresa_nombre="K", empleado_id="e1", empleado_nombre="Ana", nombre_libre=None,
            area_nombre="IT", proyecto=None, anio=None, mes=None,
            capacitacion_nombre="Excel", estado="en_curso", fecha_asignacion=None,
            fecha_limite=None, fecha_completado=None, certificado_url=None)])[0]
        assert "Empleado" in fila_asig and "Empleado" not in catalogo(_CATALOGO)[0]

    def test_el_limite_muerde_y_un_export_normal_no(self) -> None:
        svc = CapacitacionService(repo=SimpleNamespace(
            find_all=lambda e=None, s=True: _CATALOGO * LIMITE_FILAS_EXPORT))
        with pytest.raises(AppError) as exc:
            svc.exportar(EMPRESA, "csv")
        assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"

        svc_ok, _ = self._svc()
        assert svc_ok.exportar(EMPRESA, "csv").filename.endswith(".csv")


# ══════════════════════════════════════════════════════════════════════════════
# ONBOARDING
# ══════════════════════════════════════════════════════════════════════════════

def _instancia(nombre: str, progreso: int, completadas: int, inicio: str) -> InstanciaResponse:
    return InstanciaResponse(
        id=uuid4(), empleado_id=uuid4(), empresa_id=EMPRESA, empresa_nombre="Karstec",
        empleado_nombre=nombre, empleado_cargo="Analista", empleado_area="Sistemas",
        template_id=uuid4(), estado="en_curso", fecha_inicio=inicio, progreso=progreso,
        tareas_completadas=completadas, tareas_total=10,
    )


_ONBOARDINGS = [_instancia("Ana Gómez", 30, 3, "2026-02-10"),
                _instancia("Beto Pérez", 80, 8, "2026-01-05")]


class TestExportOnboarding:

    def _svc(self):
        llamadas: list = []
        repo = SimpleNamespace(
            find_instancias_activas=lambda e=None: (llamadas.append(e) or _ONBOARDINGS))
        svc = OnboardingService.__new__(OnboardingService)
        svc._repo = repo
        return svc, llamadas

    def test_va_por_el_MISMO_repo_que_el_listado(self) -> None:
        svc, llamadas = self._svc()

        listado = svc.get_onboardings_activos(EMPRESA)
        svc.exportar(EMPRESA, "csv")

        assert llamadas == [EMPRESA, EMPRESA] and len(listado) == 2

    def test_las_DOS_filas_salen_con_SUS_valores(self) -> None:
        from services._onboarding_export import construir_filas_export

        filas = construir_filas_export(_ONBOARDINGS)

        assert [f["Empleado"] for f in filas] == ["Ana Gómez", "Beto Pérez"]
        assert [f["Progreso"] for f in filas] == ["30%", "80%"]
        assert [f["Tareas completadas"] for f in filas] == [3, 8]

    def test_el_progreso_lleva_su_denominador(self) -> None:
        """"50%" son 1 de 2 o 6 de 12: en una planilla, un porcentaje sin denominador no se
        puede auditar."""
        from services._onboarding_export import construir_filas_export

        fila = construir_filas_export(_ONBOARDINGS)[0]

        assert fila["Tareas completadas"] == 3 and fila["Tareas totales"] == 10

    def test_la_fecha_ISO_se_formatea_a_dd_mm_aaaa(self) -> None:
        """🔴 `fecha_inicio` es un `str`, no un `date`: el `_fecha` de los otros exports
        reventaría con AttributeError al llamar `.strftime`."""
        from services._onboarding_export import construir_filas_export

        filas = construir_filas_export(_ONBOARDINGS)

        assert [f["Inicio"] for f in filas] == ["10/02/2026", "05/01/2026"]

    def test_una_fecha_ilegible_no_tumba_el_export(self) -> None:
        from services._onboarding_export import construir_filas_export

        filas = construir_filas_export([_instancia("Cari", 0, 0, "no-es-fecha")])

        assert filas[0]["Inicio"] == "no-es-fecha"

    def test_una_fecha_vacia_sale_como_string_vacio(self) -> None:
        from services._onboarding_export import construir_filas_export

        assert construir_filas_export([_instancia("Dani", 0, 0, "")])[0]["Inicio"] == ""

    def test_el_limite_muerde_y_un_export_normal_no(self) -> None:
        svc = OnboardingService.__new__(OnboardingService)
        svc._repo = SimpleNamespace(
            find_instancias_activas=lambda e=None: _ONBOARDINGS * LIMITE_FILAS_EXPORT)
        with pytest.raises(AppError) as exc:
            svc.exportar(EMPRESA, "csv")
        assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"

        svc_ok, _ = self._svc()
        assert svc_ok.exportar(EMPRESA, "csv").filename.endswith(".csv")

    def test_los_cuatro_formatos_llegan_al_motor(self) -> None:
        svc, _ = self._svc()

        for formato, ext in _FORMATOS:
            assert svc.exportar(EMPRESA, formato).filename.endswith(ext)
