"""
Export de empresas: que salga del MISMO listado que la pantalla y con columnas que sirvan.

🔴 ES EL ÚNICO EXPORT DEL REPO QUE HOY SE PUEDE VERIFICAR A OJO: producción tiene 2 empresas.
Eso lo vuelve el más fácil de arreglar si sale mal, y también el más caro si sale mal y nadie
mira — porque es el que alguien va a usar para un trámite.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 SON TRES EMPRESAS CON VALORES DISTINTOS EN CADA COLUMNA. Con una sola, una proyección
     que emitiera constantes ("Empresa": "Karstec") pasaría todos los asserts de contenido; y
     una que devolviera siempre la primera fila, también.
  2. 🔴 UNA ESTÁ INACTIVA. Si las tres estuvieran activas, `"Activa" if e.activa else "Inactiva"`
     se podría reemplazar por el literal `"Activa"` y nada rojearía — que es justo la columna
     por la que alguien abre este archivo (quién sigue operando y quién no).
  3. 🔴 UNA TIENE cuit, razón social, email, teléfono y dirección en None. Son opcionales en el
     schema y están vacíos en producción: sin una fila así, un `.strftime()` o un `.upper()`
     agregado sobre esos campos reventaría recién en producción.
  4. Las fechas de alta son DISTINTAS entre sí, así que un formateo que devolviera una fecha
     fija no podría esconderse.
  5. El fake REGISTRA sus llamadas: se puede afirmar que listado y export van al MISMO método
     del repo, no solo que los dos devuelven algo.
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

import routers.empresa as router_mod  # noqa: E402
from schemas.empresa import EmpresaResponse  # noqa: E402
from services._empresas_export import construir_filas_export  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services.empresa_service import EmpresaService  # noqa: E402
from utils.errors import AppError  # noqa: E402


def _empresa(**kw) -> EmpresaResponse:
    base = dict(
        id=str(uuid4()), nombre="Karstec SA", razon_social="Karstec Sociedad Anónima",
        cuit="30-71234567-9", direccion="Av. Siempreviva 742", telefono="1144556677",
        email="admin@karstec.com", logo_url="https://cdn/avatars/logos/karstec.png",
        activa=True, created_at=datetime(2026, 1, 15, 8, 45, 0), updated_at=None,
    )
    return EmpresaResponse(**{**base, **kw})


# Ver los puntos 1-4 del encabezado: tres empresas distintas, una INACTIVA y una con TODOS los
# opcionales en None.
_CATALOGO = [
    _empresa(),
    _empresa(nombre="DOSUBA", razon_social="Dosuba SRL", cuit="30-70987654-3",
             email="contacto@dosuba.com", activa=False,
             created_at=datetime(2026, 3, 2, 10, 0, 0)),
    _empresa(nombre="Sin Datos SA", razon_social=None, cuit=None, direccion=None,
             telefono=None, email=None, logo_url=None,
             created_at=datetime(2026, 5, 20, 16, 30, 0)),
]


class _Repo:
    """Registra las llamadas: así se puede afirmar que listado y export van al MISMO método."""

    def __init__(self, filas=None) -> None:
        self.llamadas: list[str] = []
        self._filas = _CATALOGO if filas is None else filas

    def find_all(self):
        self.llamadas.append("find_all")
        return self._filas


def _svc(filas=None):
    repo = _Repo(filas)
    return EmpresaService(repo=repo, audit=SimpleNamespace(registrar=lambda **k: None)), repo


def _request() -> Request:
    """Request real: `exportar_empresas` está decorado con el rate limiter, que necesita leer
    la IP de un Request de starlette. Molde: test_proyectos_export.py."""
    req = Request({"type": "http", "path": "/api/empresas/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_tiene_una_inactiva_y_una_sin_datos_opcionales() -> None:
    """Sin la inactiva, la columna Estado se podría reemplazar por la constante "Activa" y
    nada rojearía. Sin la vacía, ningún test tocaría el camino de los opcionales en None."""
    assert len(_CATALOGO) == 3
    assert [e.activa for e in _CATALOGO] == [True, False, True]
    assert _CATALOGO[2].cuit is None and _CATALOGO[2].razon_social is None
    assert len({e.created_at for e in _CATALOGO}) == 3


# ── 1. Las columnas ───────────────────────────────────────────────────────────

class TestColumnas:

    def test_son_la_ficha_completa_y_en_orden(self) -> None:
        assert list(construir_filas_export(_CATALOGO)[0]) == [
            "Empresa", "Razón social", "CUIT", "Dirección", "Teléfono", "Email",
            "Estado", "Alta",
        ]

    def test_no_hay_uuid_ni_url_de_logo(self) -> None:
        """El id no sirve en una planilla y la URL del logo tapa lo que sí importa."""
        for original, fila in zip(_CATALOGO, construir_filas_export(_CATALOGO)):
            assert "id" not in fila and "logo_url" not in fila
            assert original.id not in str(fila)
            if original.logo_url:
                assert original.logo_url not in str(fila)

    def test_cada_empresa_conserva_SUS_valores(self) -> None:
        """Contrapeso del punto 1 del encabezado: con constantes, esto rojea."""
        filas = construir_filas_export(_CATALOGO)
        assert [f["Empresa"] for f in filas] == ["Karstec SA", "DOSUBA", "Sin Datos SA"]
        assert [f["CUIT"] for f in filas] == ["30-71234567-9", "30-70987654-3", None]

    def test_el_estado_distingue_activa_de_inactiva(self) -> None:
        """🔴 La columna por la que alguien abre este archivo."""
        assert [f["Estado"] for f in construir_filas_export(_CATALOGO)] == [
            "Activa", "Inactiva", "Activa"]

    def test_el_estado_no_sale_como_booleano(self) -> None:
        """True/False en Excel se lee VERDADERO/FALSO según el idioma de quien lo abre."""
        texto = str(construir_filas_export(_CATALOGO))
        assert "True" not in texto and "False" not in texto

    def test_la_fecha_de_alta_va_sin_hora_y_es_la_de_cada_una(self) -> None:
        assert [f["Alta"] for f in construir_filas_export(_CATALOGO)] == [
            "15/01/2026", "02/03/2026", "20/05/2026"]

    def test_una_empresa_sin_datos_opcionales_no_rompe(self) -> None:
        """Producción tiene empresas con razón social y teléfono vacíos."""
        fila = construir_filas_export([_CATALOGO[2]])[0]
        assert fila["Empresa"] == "Sin Datos SA"
        assert fila["Razón social"] is None and fila["Teléfono"] is None
        assert fila["Alta"] == "20/05/2026"


# ── 2. 🔴 Listado y export salen del MISMO lugar ──────────────────────────────

class TestListadoYExportCoinciden:

    def test_los_dos_van_al_mismo_metodo_del_repo(self) -> None:
        svc, repo = _svc()

        svc.list_empresas()
        svc.exportar("excel")

        assert repo.llamadas == ["find_all", "find_all"]

    def test_el_archivo_trae_EXACTAMENTE_las_empresas_del_listado(self) -> None:
        """Incluidas las INACTIVAS: el listado no filtra por estado, así que el archivo
        tampoco. Si un día la pantalla las escondiera, el export tendría que hacer lo mismo."""
        svc, _ = _svc()

        listado = svc.list_empresas()

        assert listado.total == 3
        nombres = {f["Empresa"] for f in construir_filas_export(listado.items)}
        assert nombres == {"Karstec SA", "DOSUBA", "Sin Datos SA"}


# ── 3. El límite de export, de los dos lados ──────────────────────────────────

def test_el_export_chequea_el_limite_de_filas() -> None:
    svc, _ = _svc([_CATALOGO[0]] * (LIMITE_FILAS_EXPORT + 1))

    with pytest.raises(AppError) as exc:
        svc.exportar("excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_un_export_normal_NO_corta() -> None:
    """Contrapeso: sin esto, un chequeo que rechazara siempre pasaría el test de arriba."""
    svc, _ = _svc()

    d = svc.exportar("csv")

    assert d.content and d.filename.endswith(".csv")


def test_el_formato_llega_al_motor() -> None:
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(formato).filename.endswith(ext)


def test_un_formato_inventado_se_rechaza() -> None:
    svc, _ = _svc()

    with pytest.raises(AppError) as exc:
        svc.exportar("xml")

    assert exc.value.code == "EXPORT_FORMATO_INVALIDO"


# ── 4. El router ──────────────────────────────────────────────────────────────

class TestElRouter:

    async def test_el_formato_llega_al_service(self) -> None:
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="empresas.csv"))

        await router_mod.exportar_empresas(request=_request(), formato="pdf", service=svc)

        assert recibido["args"] == ("pdf",)

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="empresas.csv"))

        out = await router_mod.exportar_empresas(request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="empresas.csv"' in out.headers["Content-Disposition"]

    def test_exportar_esta_declarada_ANTES_de_get_por_id(self) -> None:
        """🔴 Si /{id} se registrara primero, FastAPI matchearía "exportar" como un UUID y el
        endpoint devolvería 422 en vez de un archivo. Acá /{id} SÍ existe, así que el orden es
        load-bearing y no una precaución teórica."""
        paths = [r.path for r in router_mod.router.routes]
        assert paths.index("/exportar") < paths.index("/{id}")
