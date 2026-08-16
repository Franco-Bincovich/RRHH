"""
Filtros que el backend ya aceptaba y recién ahora tienen control en la UI.

Los tres (`es_lider` en empleados, `empleado_id` + `capacitacion_id` en asignaciones de
capacitación, `empleado_id` en asignaciones de inventario) llegaban a la query desde antes,
pero **no tenían un solo test**: nadie los había ejercitado nunca, así que un refactor podía
romperlos sin que se notara. Ahora que además son alcanzables desde la pantalla, la
regresión sería visible para el usuario.

Lo que se fija en cada caso:
  · el filtro VIAJA del service al repo (no se pierde en el camino);
  · el EXPORT manda exactamente lo mismo que el listado, que es donde el invariante ya se
    había roto una vez en el front;
  · dos filtros a la vez se COMPONEN (AND), no se pisan.

Los repos son espías: registran los argumentos con los que se los llamó. El objetivo no es
verificar que Supabase filtre bien, sino que el filtro llegue hasta la query — que es donde
el barrido de la Fase 2 encontró tres falsos positivos.
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

from uuid import uuid4

import pytest

from services.asignacion_service import AsignacionService
from services.empleado_service import EmpleadoService
from services.inventario_asignaciones_service import InventarioAsignacionesService

EMPRESA = uuid4()
EMPLEADO = uuid4()
CAPACITACION = uuid4()
AREA = uuid4()


# ─── es_lider (empleados) ─────────────────────────────────────────────────────


class _EmpleadoRepoEspia:
    def __init__(self) -> None:
        self.args: dict = {}

    def find_all(self, page, page_size, empresa_id=None, area_id=None, estado=None,
                 search=None, es_lider=None, proyecto_ids=None, sin_manager=None):
        self.args = {"empresa_id": empresa_id, "area_id": area_id, "estado": estado,
                     "search": search, "es_lider": es_lider, "proyecto_ids": proyecto_ids,
                     "sin_manager": sin_manager}
        return [], 0


class TestEsLider:
    def _listar(self, **kw) -> dict:
        repo = _EmpleadoRepoEspia()
        EmpleadoService(repo=repo).get_empleados(1, 20, **kw)
        return repo.args

    def _exportar(self, **kw) -> dict:
        repo = _EmpleadoRepoEspia()
        EmpleadoService(repo=repo).exportar(**kw)
        return repo.args

    @pytest.mark.parametrize("valor", [True, False])
    def test_viaja_hasta_el_repo(self, valor: bool) -> None:
        """`False` es un filtro válido (solo NO líderes), no un 'sin filtro'."""
        assert self._listar(es_lider=valor)["es_lider"] is valor

    def test_sin_filtro_llega_como_none(self) -> None:
        assert self._listar()["es_lider"] is None

    @pytest.mark.parametrize("valor", [True, False])
    def test_el_export_manda_lo_mismo(self, valor: bool) -> None:
        assert self._exportar(es_lider=valor)["es_lider"] is valor

    def test_se_compone_con_los_otros_filtros(self) -> None:
        """AND, no reemplazo: liderazgo + área + estado llegan los tres juntos."""
        args = self._listar(es_lider=True, area_id=str(AREA), estado="activo")
        assert (args["es_lider"], args["area_id"], args["estado"]) == (True, str(AREA), "activo")

    def test_listado_y_export_mandan_lo_mismo(self) -> None:
        kw = {"es_lider": True, "area_id": str(AREA), "estado": "activo", "search": "ana"}
        assert self._exportar(**kw) == self._listar(**kw)


# ─── empleado_id + capacitacion_id (asignaciones de capacitación) ─────────────


class _AsignacionRepoEspia:
    def __init__(self) -> None:
        self.args: dict = {}

    def find_all(self, empresa_id=None, empleado_id=None, capacitacion_id=None,
                 estado=None, area_id=None, page=1, page_size=20):
        self.args = {"empresa_id": empresa_id, "empleado_id": empleado_id,
                     "capacitacion_id": capacitacion_id, "estado": estado, "area_id": area_id}
        # `page`/`page_size` + tupla `(filas, total)`: es el contrato del repo desde que el
        # listado pagina. Un fake que devuelva la lista pelada rompe con TypeError en vez de
        # mentir, que es lo correcto — pero tiene que modelar el contrato para poder desmentir.
        return [], 0


class TestAsignacionesCapacitacion:
    def _listar(self, **kw) -> dict:
        repo = _AsignacionRepoEspia()
        AsignacionService(repo=repo).get_all(**kw)
        return repo.args

    def _exportar(self, **kw) -> dict:
        repo = _AsignacionRepoEspia()
        AsignacionService(repo=repo).exportar(**kw)
        return repo.args

    def test_empleado_viaja_hasta_el_repo(self) -> None:
        assert self._listar(empleado_id=EMPLEADO)["empleado_id"] == EMPLEADO

    def test_capacitacion_viaja_hasta_el_repo(self) -> None:
        assert self._listar(capacitacion_id=CAPACITACION)["capacitacion_id"] == CAPACITACION

    def test_los_dos_juntos_se_componen(self) -> None:
        """Filtrar por empleado Y capacitación es 'esta persona en este curso', no uno u otro."""
        args = self._listar(empleado_id=EMPLEADO, capacitacion_id=CAPACITACION)
        assert (args["empleado_id"], args["capacitacion_id"]) == (EMPLEADO, CAPACITACION)

    def test_se_componen_con_area_y_estado(self) -> None:
        args = self._listar(empleado_id=EMPLEADO, capacitacion_id=CAPACITACION,
                            area_id=AREA, estado="completado")
        assert all(args[k] is not None for k in ("empleado_id", "capacitacion_id", "area_id", "estado"))

    @pytest.mark.parametrize("campo,valor", [
        ("empleado_id", EMPLEADO), ("capacitacion_id", CAPACITACION),
    ])
    def test_el_export_manda_lo_mismo(self, campo: str, valor) -> None:
        assert self._exportar(**{campo: valor})[campo] == valor

    def test_listado_y_export_mandan_lo_mismo(self) -> None:
        kw = {"empleado_id": EMPLEADO, "capacitacion_id": CAPACITACION,
              "area_id": AREA, "estado": "completado"}
        assert self._exportar(**kw) == self._listar(**kw)


# ─── empleado_id (asignaciones de inventario) ─────────────────────────────────


class _InventarioRepoEspia:
    def __init__(self) -> None:
        self.args: dict = {}

    def find_all(self, empresa_id=None, empleado_id=None, area_id=None, page=1, page_size=20):
        self.args = {"empresa_id": empresa_id, "empleado_id": empleado_id, "area_id": area_id}
        return [], 0


class TestAsignacionesInventario:
    def _listar(self, **kw) -> dict:
        repo = _InventarioRepoEspia()
        InventarioAsignacionesService(repo=repo).get_all(**kw)
        return repo.args

    def _exportar(self, **kw) -> dict:
        repo = _InventarioRepoEspia()
        InventarioAsignacionesService(repo=repo).exportar(**kw)
        return repo.args

    def test_empleado_viaja_hasta_el_repo(self) -> None:
        assert self._listar(empleado_id=str(EMPLEADO))["empleado_id"] == str(EMPLEADO)

    def test_sin_filtro_llega_como_none(self) -> None:
        assert self._listar()["empleado_id"] is None

    def test_se_compone_con_empresa(self) -> None:
        args = self._listar(empresa_id=EMPRESA, empleado_id=str(EMPLEADO))
        assert (args["empresa_id"], args["empleado_id"]) == (EMPRESA, str(EMPLEADO))

    def test_el_export_manda_lo_mismo(self) -> None:
        assert self._exportar(empleado_id=str(EMPLEADO))["empleado_id"] == str(EMPLEADO)

    def test_listado_y_export_mandan_lo_mismo(self) -> None:
        kw = {"empresa_id": EMPRESA, "empleado_id": str(EMPLEADO)}
        assert self._exportar(**kw) == self._listar(**kw)
