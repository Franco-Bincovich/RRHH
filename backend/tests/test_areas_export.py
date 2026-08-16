"""
Export de áreas: que el filtro de empresa llegue del ROUTER al REPO, y que el listado y el export
devuelvan EL MISMO conjunto con el mismo filtro.

El modo de falla que cubre no rompe nada visible: RRHH filtra por empresa, exporta, y el archivo
trae las áreas de las dos. `test_paridad_list_export.py` verifica que los dos endpoints ACEPTEN
los mismos Query; lo de acá verifica que ese Query termine en la misma consulta.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL FAKE FILTRA DE VERDAD Y REPARTE LAS ÁREAS EN DOS EMPRESAS. Es la condición del
     archivo: con todas en la misma empresa, "filtró" y "no filtró" devuelven el mismo conjunto y
     un `empresa_id` perdido pasaría desapercibido. Y un repo que ACEPTE el parámetro y lo IGNORE
     se lee igual que uno correcto — es el caso #1 de la regla del repo.
  2. 🔴 DOS ÁREAS COMPARTEN NOMBRE EXACTO, a propósito. En producción hay dos que son casi la
     misma ("GESTION DE DEUDA" y "GD - GESTION DE DEUDA") y nada garantiza unicidad: ni el schema
     ni la práctica. Ningún test de acá indexa por nombre ni asume que sean únicos, y hay un caso
     que verifica que el export emita las DOS filas en vez de colapsarlas.
  3. `listado` y `export` se comparan CONTRA EL MISMO llamado registrado, no contra un número
     escrito a mano: lo que se afirma es la igualdad de las dos consultas.
  4. Ningún filtro devuelve el total: si uno se cayera, el conteo salta y el test rojea.
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

from datetime import datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
from starlette.requests import Request  # noqa: E402

import routers.areas as router_mod  # noqa: E402
from schemas.area import AreaResponse  # noqa: E402
from services._areas_export import construir_filas_export  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services.area_service import AreaService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A = str(uuid4())
EMPRESA_B = str(uuid4())


def _area(nombre: str, empresa: str, empleados: int = 3) -> AreaResponse:
    return AreaResponse(
        id=str(uuid4()), empresa_id=empresa, nombre=nombre, descripcion="desc",
        responsable_id=str(uuid4()), responsable_nombre="Ana Gómez",
        cantidad_empleados=empleados, created_at=datetime(2026, 1, 15, 8, 45, 0),
    )


# 🔴 Cinco áreas, DOS empresas, y "Sistemas" REPETIDO en las dos. El nombre no es único.
_CATALOGO = [
    _area("Sistemas", EMPRESA_A, 5),
    _area("Sistemas", EMPRESA_B, 2),        # ← mismo nombre, otra empresa
    _area("GESTION DE DEUDA", EMPRESA_A, 4),
    _area("GD - GESTION DE DEUDA", EMPRESA_A, 1),
    _area("Legales", EMPRESA_B, 3),
]


class _Repo:
    """🔴 FILTRA DE VERDAD. Un fake que devolviera siempre las 5 dejaría este archivo sin poder
    desmentir nada."""

    def __init__(self) -> None:
        self.llamadas: list = []
        self.busquedas: list = []

    def _filtradas(self, empresa_id, search):
        filas = [a for a in _CATALOGO if empresa_id is None or a.empresa_id == empresa_id]
        # El `search` filtra DE VERDAD: si lo ignorara, "el export respeta la búsqueda" sería
        # indistinguible de "el export trae todo".
        if search:
            filas = [a for a in filas if search.lower() in a.nombre.lower()]
        return filas

    def find_all(self, empresa_id=None, search=None):
        """El catálogo completo (`/api/areas/opciones`). No pagina."""
        self.llamadas.append(empresa_id)
        return self._filtradas(empresa_id, search)

    def find_pagina(self, empresa_id=None, search=None, page=1, page_size=20):
        """El listado de gestión. (página, total) — el total es el del FILTRO, sin recortar."""
        self.llamadas.append(empresa_id)
        self.busquedas.append(search)
        filas = self._filtradas(empresa_id, search)
        ini = (page - 1) * page_size
        return filas[ini:ini + page_size], len(filas)


def _svc():
    repo = _Repo()
    return AreaService(repo=repo), repo


def _request() -> Request:
    """Request real: `exportar_areas` está decorado con el rate limiter, que necesita leer la IP
    de un Request de starlette. Molde: test_reporte_area.py."""
    req = Request({"type": "http", "path": "/api/areas/exportar", "headers": [],
                   "client": ("6.6.6.6", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    req.state.empresa_id = EMPRESA_A
    return req


# ── 0. Los guardianes del fake ────────────────────────────────────────────────

def test_el_fake_reparte_las_areas_en_dos_empresas() -> None:
    """Sin reparto, todo filtro devolvería el total y "filtró" sería indistinguible."""
    repo = _Repo()
    assert len(repo.find_all()) == 5
    assert len(repo.find_all(EMPRESA_A)) == 3
    assert len(repo.find_all(EMPRESA_B)) == 2


def test_el_fake_tiene_nombres_REPETIDOS() -> None:
    """Producción tiene dos áreas casi homónimas y el nombre no es único en ningún lado. Ningún
    test de este archivo puede asumir unicidad."""
    nombres = [a.nombre for a in _CATALOGO]
    assert len(nombres) != len(set(nombres)), "el fake dejó de modelar el nombre repetido"


# ── 1. El filtro llega del service al repo ────────────────────────────────────

class TestElExportPasaElFiltro:

    def test_la_empresa_llega_al_repo(self) -> None:
        svc, repo = _svc()

        svc.exportar(EMPRESA_A, "excel")

        assert repo.llamadas == [EMPRESA_A]

    def test_con_OTRA_empresa_llega_esa_otra(self) -> None:
        """Contrapeso: sin esto, un valor hardcodeado pasaría el test de arriba."""
        svc, repo = _svc()

        svc.exportar(EMPRESA_B, "excel")

        assert repo.llamadas == [EMPRESA_B]

    def test_sin_filtro_el_repo_lo_recibe_en_None(self) -> None:
        svc, repo = _svc()

        svc.exportar(None, "excel")

        assert repo.llamadas == [None]


# ── 2. 🔴 Listado y export devuelven EL MISMO conjunto ────────────────────────

class TestListadoYExportCoinciden:

    def test_con_filtro_de_empresa(self) -> None:
        svc, repo = _svc()

        listado = svc.get_areas(EMPRESA_A)
        svc.exportar(EMPRESA_A, "excel")

        assert repo.llamadas[0] == repo.llamadas[1]
        assert len(listado) == 3

    def test_sin_filtro(self) -> None:
        svc, repo = _svc()

        listado = svc.get_areas(None)
        svc.exportar(None, "excel")

        assert repo.llamadas[0] == repo.llamadas[1]
        assert len(listado) == 5

    def test_el_archivo_trae_EXACTAMENTE_las_filas_del_listado_filtrado(self) -> None:
        """🔴 El bug que esto cubre: filtrar por empresa, exportar, y que salgan las dos.
        Se compara el CONTENIDO, y por ids —no por nombre, que se repite."""
        svc, _ = _svc()

        listado = svc.get_areas(EMPRESA_B)
        filas = construir_filas_export(listado)

        assert len(filas) == 2
        assert {f["Área"] for f in filas} == {"Sistemas", "Legales"}
        assert "GESTION DE DEUDA" not in {f["Área"] for f in filas}

    def test_dos_areas_con_el_MISMO_nombre_salen_como_DOS_filas(self) -> None:
        """Colapsarlas escondería un área entera y su dotación. El export no deduplica."""
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_areas(None))

        sistemas = [f for f in filas if f["Área"] == "Sistemas"]
        assert len(sistemas) == 2
        assert {f["Empleados"] for f in sistemas} == {5, 2}


# ── 3. El router pasa lo que recibe ───────────────────────────────────────────

class TestElRouter:

    async def test_el_query_llega_al_service(self) -> None:
        """El router recibiendo un parámetro no prueba nada: hay que seguirlo hasta abajo."""
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="areas.csv"))

        # `search=None` explícito por el mismo motivo que `empresa_id` abajo: llamando a la
        # función directo, FastAPI no resuelve los defaults y llegaría el objeto `Query(None)`.
        await router_mod.exportar_areas(request=_request(), formato="csv",
                                        empresa_id=EMPRESA_B, search=None, service=svc)

        # El 3er argumento es el `search`, que el router pasa siempre (None si no vino).
        assert recibido["args"] == (EMPRESA_B, "csv", None)

    async def test_sin_query_NO_cae_al_header_de_empresa(self) -> None:
        """🔴 La empresa del export sale del QUERY, no del header — igual que el listado, que
        tampoco lee `request.state` (`list_areas` solo recibe el Query). Si alguien "arreglara"
        el export con un `empresa_id or _empresa_str(request)`, las dos puntas dejarían de
        coincidir: el listado mostraría todas y el archivo saldría acotado a la empresa activa.

        ⚠️ El `request` de este test lleva `EMPRESA_A` en el header a propósito: es el valor que
        NO tiene que aparecer. Se pasa `empresa_id=None` explícito porque llamando a la función
        directo FastAPI no resuelve los defaults y el parámetro llegaría como el objeto
        `Query(None)` — artefacto del arnés, no del código.
        """
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="areas.csv"))

        await router_mod.exportar_areas(request=_request(), formato="csv",
                                        empresa_id=None, search=None, service=svc)

        assert recibido["args"] == (None, "csv", None)
        assert EMPRESA_A not in recibido["args"], "cayó al header X-Empresa-Id"

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="areas.csv"))

        out = await router_mod.exportar_areas(request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="areas.csv"' in out.headers["Content-Disposition"]


# ── 4. Límite y formatos ──────────────────────────────────────────────────────

def test_el_export_chequea_el_limite_de_filas() -> None:
    muchas = [_CATALOGO[0]] * (LIMITE_FILAS_EXPORT + 1)
    # Devuelve (pagina, total): el corte lo dispara el TOTAL, no el largo de lo que llegó.
    svc = AreaService(repo=SimpleNamespace(
        find_all=lambda *a, **k: muchas,
        find_pagina=lambda *a, **k: (muchas, len(muchas)),
    ))

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA_A, "excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_un_export_normal_NO_corta() -> None:
    """Contrapeso: sin esto, un `verificar_limite_export` que rechazara siempre pasaría arriba."""
    svc, _ = _svc()

    d = svc.exportar(EMPRESA_A, "csv")

    assert d.content and d.filename.endswith(".csv")


def test_el_formato_llega_al_motor() -> None:
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(EMPRESA_A, formato).filename.endswith(ext)


def test_un_formato_inventado_se_rechaza() -> None:
    svc, _ = _svc()

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA_A, "xml")

    assert exc.value.code == "EXPORT_FORMATO_INVALIDO"
