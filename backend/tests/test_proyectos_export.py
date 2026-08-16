"""
Export de proyectos: que los filtros lleguen del ROUTER al REPO, y que el listado y el export
devuelvan EL MISMO conjunto con el mismo filtro.

El modo de falla que esto cubre no rompe nada visible: el usuario filtra la pantalla, exporta, y
recibe un archivo con MÁS filas de las que estaba viendo — sin error y sin aviso.
`test_paridad_list_export.py` verifica que los dos endpoints ACEPTEN los mismos Query; lo que se
verifica acá es que esos Query terminen en la misma consulta.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL FAKE DEVUELVE CONJUNTOS DISTINTOS SEGÚN EL FILTRO, no una lista fija. Es la condición
     del archivo: un repo que ACEPTE `estado`/`area_id` y los IGNORE se lee igual que uno
     correcto, y "el filtro llegó" y "el filtro se perdió" darían el mismo resultado. Acá el fake
     filtra de verdad sobre 4 proyectos, así que un parámetro perdido cambia el conjunto.
  2. Los 4 proyectos se reparten en DOS estados y DOS áreas, y ningún filtro devuelve el total:
     si un filtro se cayera, el conteo salta a 4 y el test rojea. Con un solo proyecto, "filtró"
     y "no filtró" serían indistinguibles.
  3. `listado` y `export` se comparan CONTRA EL MISMO llamado, no contra un número escrito a
     mano: el test afirma la igualdad de los dos conjuntos, que es la invariante real.
  4. El fake REGISTRA cada llamada, así que se puede afirmar qué recibió el repo — no solo qué
     devolvió el service.
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

from starlette.requests import Request  # noqa: E402

import routers.proyectos as router_mod  # noqa: E402
from schemas.proyectos import CosteoResumen, ProyectoResponse  # noqa: E402
from services.proyectos_service import ProyectosService  # noqa: E402

EMPRESA = uuid4()
AREA_A = uuid4()
AREA_B = uuid4()


def _proy(nombre: str, estado: str, area) -> ProyectoResponse:
    return ProyectoResponse(
        id=uuid4(), empresa_id=EMPRESA, empresa_nombre="Karstec", nombre=nombre,
        descripcion=None, estado=estado, fecha_inicio=date(2026, 1, 1), fecha_fin=None,
        presupuesto=1000.0,
        costeo=CosteoResumen(costo_acumulado=100.0, presupuesto_restante=900.0, pct_consumido=10.0),
        created_at=datetime(2026, 1, 1, 9, 0, 0),
    ), area


_CATALOGO = [_proy("Alfa", "activo", AREA_A), _proy("Beta", "activo", AREA_B),
             _proy("Gamma", "cerrado", AREA_A), _proy("Delta", "pausado", AREA_B)]


class _Repo:
    """🔴 FILTRA DE VERDAD. Un fake que aceptara los parámetros y devolviera siempre los 4 dejaría
    este archivo entero sin poder desmentir nada."""

    def __init__(self) -> None:
        self.llamadas: list = []

    def find_all(self, empresa_id=None, estado=None, area_id=None, page=1, page_size=20):
        self.llamadas.append({"empresa_id": empresa_id, "estado": estado, "area_id": area_id})
        filas = [p for p, area in _CATALOGO
                 if (estado is None or p.estado == estado) and (area_id is None or area == area_id)]
        # El total es el del FILTRO (sin recortar), y el recorte se aplica después: es lo que hace
        # el repo real con `count="exact"` + `.range()`. Un fake que devolviera `len(pagina)` como
        # total no podría desmentir un export que se lleva solo la primera página.
        ini = (page - 1) * page_size
        return filas[ini:ini + page_size], len(filas)


def _svc():
    repo = _Repo()
    return ProyectosService(repo=repo), repo


def _request() -> Request:
    """Request real: `exportar_proyectos` está decorado con el rate limiter, que necesita leer
    la IP de un Request de starlette. Molde: test_reporte_area.py."""
    req = Request({"type": "http", "path": "/api/proyectos/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    req.state.empresa_id = str(EMPRESA)
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_reparte_los_proyectos_en_dos_estados_y_dos_areas() -> None:
    """Sin reparto, todo filtro devolvería el total y "filtró" sería indistinguible de "no filtró"."""
    repo = _Repo()
    # `find_all` devuelve (pagina, total) desde que el listado pagina. Se mira el TOTAL, que es
    # lo que el filtro tiene que bajar — la página con el default de 20 traería lo mismo.
    assert repo.find_all()[1] == 4
    assert repo.find_all(estado="activo")[1] == 2
    assert repo.find_all(area_id=AREA_A)[1] == 2
    assert repo.find_all(estado="activo", area_id=AREA_A)[1] == 1


# ── 1. Los filtros llegan del service al repo ─────────────────────────────────

class TestElExportPasaLosFiltros:

    def test_estado_y_area_llegan_al_repo(self) -> None:
        svc, repo = _svc()

        svc.exportar(EMPRESA, "excel", "activo", AREA_A)

        assert repo.llamadas[0] == {"empresa_id": EMPRESA, "estado": "activo", "area_id": AREA_A}

    def test_sin_filtros_el_repo_los_recibe_en_None(self) -> None:
        """Contrapeso: con valores hardcodeados, el test de arriba pasaría igual."""
        svc, repo = _svc()

        svc.exportar(EMPRESA, "excel")

        assert repo.llamadas[0] == {"empresa_id": EMPRESA, "estado": None, "area_id": None}

    def test_en_consolidado_la_empresa_viaja_como_None(self) -> None:
        svc, repo = _svc()

        svc.exportar(None, "excel")

        assert repo.llamadas[0]["empresa_id"] is None


# ── 2. 🔴 Listado y export devuelven EL MISMO conjunto ────────────────────────

class TestListadoYExportCoinciden:
    """La invariante que importa. `test_paridad_list_export` verifica que los dos ACEPTEN los
    mismos Query; esto verifica que con el mismo Query traigan las mismas filas."""

    def test_con_filtro_de_estado(self) -> None:
        svc, repo = _svc()

        listado = svc.get_all(EMPRESA, "activo", None)
        svc.exportar(EMPRESA, "excel", "activo", None)

        assert repo.llamadas[0] == repo.llamadas[1]
        assert listado.total == 2

    def test_con_filtro_de_area(self) -> None:
        svc, repo = _svc()

        listado = svc.get_all(EMPRESA, None, AREA_B)
        svc.exportar(EMPRESA, "excel", None, AREA_B)

        assert repo.llamadas[0] == repo.llamadas[1]
        assert listado.total == 2

    def test_con_los_dos_filtros_a_la_vez(self) -> None:
        svc, repo = _svc()

        listado = svc.get_all(EMPRESA, "activo", AREA_A)
        svc.exportar(EMPRESA, "excel", "activo", AREA_A)

        assert repo.llamadas[0] == repo.llamadas[1]
        assert listado.total == 1, "el filtro combinado tiene que acotar más que cada uno solo"

    def test_el_archivo_trae_EXACTAMENTE_las_filas_del_listado_filtrado(self) -> None:
        """🔴 El bug que esto cubre: filtrar la pantalla, exportar, y que el archivo traiga los 4.
        Se compara el CONTENIDO, no el conteo de la llamada."""
        from services._proyectos_export import construir_filas_export

        svc, _ = _svc()
        listado = svc.get_all(EMPRESA, "activo", None)
        esperados = {f["Proyecto"] for f in construir_filas_export(listado.items)}

        svc.exportar(EMPRESA, "excel", "activo", None)   # mismo filtro

        assert esperados == {"Alfa", "Beta"}
        assert "Gamma" not in esperados and "Delta" not in esperados


# ── 3. El router pasa lo que recibe ───────────────────────────────────────────

class TestElRouter:

    async def test_los_query_llegan_al_service(self, monkeypatch) -> None:
        """El router recibiendo un parámetro no prueba nada: hay que seguirlo hasta abajo."""
        recibido: dict = {}
        monkeypatch.setattr(router_mod, "ProyectosService", lambda: None)
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="proyectos.csv"))

        await router_mod.exportar_proyectos(request=_request(), formato="csv",
                                            estado="pausado", area_id=AREA_B, service=svc)

        assert recibido["args"] == (EMPRESA, "csv", "pausado", AREA_B)

    async def test_devuelve_el_archivo_con_su_nombre(self, monkeypatch) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="proyectos.csv"))

        out = await router_mod.exportar_proyectos(request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="proyectos.csv"' in out.headers["Content-Disposition"]


# ── 4. El límite de export ────────────────────────────────────────────────────

def test_el_export_chequea_el_limite_de_filas() -> None:
    """`test_limite_export.py::TestTodosLosExportsChequean` ya barre que la llamada exista en el
    código. Acá se verifica que MUERDA: con más filas que el techo, corta antes de armar nada."""
    import pytest

    from services._limite_export import LIMITE_FILAS_EXPORT
    from utils.errors import AppError

    muchos = [_CATALOGO[0][0]] * (LIMITE_FILAS_EXPORT + 1)
    # Devuelve (pagina, total): el corte lo dispara el TOTAL, no el largo de lo que llegó. Con
    # el service pidiendo LIMITE_FILAS_EXPORT filas, un fake que devolviera solo la página nunca
    # superaría el tope y este test no podría fallar.
    svc = ProyectosService(repo=SimpleNamespace(find_all=lambda *a, **k: (muchos, len(muchos))))

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA, "excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_un_export_normal_NO_corta() -> None:
    """Contrapeso: sin esto, un `verificar_limite_export` que rechazara siempre pasaría arriba."""
    svc, _ = _svc()

    d = svc.exportar(EMPRESA, "csv")

    assert d.content and d.filename.endswith(".csv")


def test_el_formato_llega_al_motor() -> None:
    """Los cuatro formatos del motor, por el camino real."""
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(EMPRESA, formato).filename.endswith(ext)


def test_un_formato_inventado_se_rechaza() -> None:
    import pytest

    from utils.errors import AppError

    svc, _ = _svc()
    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA, "xml")
    assert exc.value.code == "EXPORT_FORMATO_INVALIDO"
