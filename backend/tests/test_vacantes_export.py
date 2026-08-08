"""
Export de vacantes: que el filtro de estado llegue del router al repo y que el archivo traiga
lo mismo que la pantalla.

A diferencia de /equipo, de las plantillas de onboarding y de los días pendientes, este módulo
NO acota su universo por token: `Seccion.VACANTES` no está en `MANDOS_MEDIOS_SECCIONES`, así
que solo llegan admin_rrhh y gerencia_lectura, para quienes el ownership no restringe. El único
eje es la empresa, y va en el WHERE del repo. Por eso acá no hay tests de ownership: agregarlos
sería código que aparenta seguridad sin verificar nada.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL REPO FAKE FILTRA DE VERDAD POR ESTADO. Un repo que aceptara `estado` y devolviera
     siempre las cuatro vacantes se lee igual que uno correcto, y "el filtro llegó" y "el filtro
     se perdió" darían el mismo resultado.
  2. 🔴 LAS CUATRO SE REPARTEN EN TRES ESTADOS Y NINGÚN FILTRO DEVUELVE EL TOTAL. Si un filtro
     se cayera, el conteo salta a 4 y el test rojea. Con una sola vacante, "filtró" y "no
     filtró" serían indistinguibles.
  3. Cada vacante tiene título, área, modalidad y fechas DISTINTAS: una proyección que emitiera
     constantes, o siempre la primera fila, rojea.
  4. Una vacante tiene TODOS los opcionales en None (modalidad, jornada, ubicación, contrato,
     email, fecha de apertura): sin ella, un `.upper()` o un `.strftime()` agregado sobre esos
     campos reventaría recién en producción.
  5. Una trae los bloques de texto largo cargados (`descripcion`, `requisitos`, `funciones`,
     `copy_publicacion`, `hashtags`, `linkedin_post_id`): si la proyección empezara a volcarlos,
     hay contra qué comprobarlo. Sin esos campos poblados, "no vuelca los textos largos" pasaría
     con la proyección borrada.
  6. Se afirma sobre el CONTENIDO del CSV generado, no solo sobre lo que devolvió el fake.
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
from starlette.requests import Request  # noqa: E402

import routers.vacantes as router_mod  # noqa: E402
from schemas.vacante import VacanteResponse  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services._vacantes_export import construir_filas_export  # noqa: E402
from services.vacante_service import VacanteService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()

_TEXTO_LARGO = "Se busca perfil con experiencia. " * 12


def _vac(titulo: str, estado: str, area: str, **kw) -> VacanteResponse:
    base = dict(
        id=str(uuid4()), empresa_id=str(EMPRESA), empresa_nombre="Karstec", titulo=titulo,
        area_id=str(uuid4()), area_nombre=area, estado=estado,
        tipo_contrato="Tiempo indeterminado", modalidad="Híbrido", jornada="Full time",
        ubicacion="CABA", email_contacto="rrhh@karstec.com",
        fecha_apertura=date(2026, 3, 1), created_at=datetime(2026, 2, 20, 9, 0, 0),
    )
    return VacanteResponse(**{**base, **kw})


# Ver los puntos 2-5 del encabezado.
_CATALOGO = [
    # Con los textos largos cargados: es contra esto que se comprueba que NO se vuelquen.
    _vac("Dev Backend", "nueva", "Sistemas", descripcion=_TEXTO_LARGO, requisitos=_TEXTO_LARGO,
         funciones=_TEXTO_LARGO, copy_publicacion=_TEXTO_LARGO, hashtags="#dev #python",
         linkedin_post_id="urn:li:share:7100000000"),
    _vac("Analista de Cobranzas", "en_proceso", "Gestión de Deuda", modalidad="Presencial",
         ubicacion="Rosario", fecha_apertura=date(2026, 1, 15)),
    _vac("Contador Senior", "cerrada", "Administración", jornada="Part time",
         fecha_apertura=date(2025, 11, 5)),
    # Todos los opcionales en None (punto 4).
    _vac("Pasantía IT", "nueva", "Sistemas", tipo_contrato=None, modalidad=None, jornada=None,
         ubicacion=None, email_contacto=None, fecha_apertura=None),
]


class _Repo:
    """🔴 FILTRA DE VERDAD por estado (punto 1) y registra qué recibió."""

    def __init__(self, filas=None) -> None:
        self.llamadas: list[dict] = []
        self._filas = _CATALOGO if filas is None else filas

    def find_all(self, estado=None, empresa_id=None):
        self.llamadas.append({"estado": estado, "empresa_id": empresa_id})
        return [v for v in self._filas if estado is None or v.estado == estado]


def _svc(filas=None):
    repo = _Repo(filas)
    return VacanteService(repo=repo, audit=SimpleNamespace(registrar=lambda **k: None)), repo


def _csv(descarga) -> str:
    """El CSV generado, como texto: sirve para afirmar QUÉ filas y QUÉ columnas terminaron en
    el archivo, no qué devolvió el fake."""
    return descarga.content.decode("utf-8-sig")


def _request() -> Request:
    """Request real: `exportar_vacantes` está decorado con el rate limiter, que necesita leer
    la IP de un Request de starlette. Molde: test_proyectos_export.py."""
    req = Request({"type": "http", "path": "/api/vacantes/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    req.state.empresa_id = str(EMPRESA)
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_reparte_las_vacantes_en_tres_estados() -> None:
    """Sin reparto, todo filtro devolvería el total y "filtró" sería indistinguible de "no
    filtró". Y sin la vacante de textos largos, no habría contra qué comprobar que no salen."""
    repo = _Repo()
    assert len(repo.find_all()) == 4
    assert len(repo.find_all(estado="nueva")) == 2
    assert len(repo.find_all(estado="cerrada")) == 1
    assert _CATALOGO[0].descripcion and _CATALOGO[0].linkedin_post_id
    assert _CATALOGO[3].modalidad is None and _CATALOGO[3].fecha_apertura is None


# ── 1. El filtro de estado llega del service al repo ──────────────────────────

class TestElFiltro:

    def test_el_estado_llega_al_repo(self) -> None:
        svc, repo = _svc()

        svc.exportar(EMPRESA, "csv", "en_proceso")

        assert repo.llamadas[0] == {"estado": "en_proceso", "empresa_id": EMPRESA}

    def test_sin_filtro_el_repo_lo_recibe_en_None(self) -> None:
        """Contrapeso: con un valor hardcodeado, el test de arriba pasaría igual."""
        svc, repo = _svc()

        svc.exportar(EMPRESA, "csv")

        assert repo.llamadas[0]["estado"] is None

    def test_el_filtro_recorta_el_ARCHIVO(self) -> None:
        svc, _ = _svc()

        texto = _csv(svc.exportar(EMPRESA, "csv", "cerrada"))

        assert "Contador Senior" in texto
        assert "Dev Backend" not in texto and "Pasantía IT" not in texto

    def test_listado_y_export_le_piden_al_repo_LO_MISMO(self) -> None:
        svc, repo = _svc()

        svc.get_vacantes("nueva", EMPRESA)
        svc.exportar(EMPRESA, "csv", "nueva")

        assert repo.llamadas[0] == repo.llamadas[1]

    def test_en_consolidado_la_empresa_viaja_como_None(self) -> None:
        svc, repo = _svc()

        svc.exportar(None, "csv")

        assert repo.llamadas[0]["empresa_id"] is None


# ── 2. Las columnas ───────────────────────────────────────────────────────────

class TestColumnas:

    def test_son_las_esperadas_y_en_orden(self) -> None:
        assert list(construir_filas_export(_CATALOGO)[0]) == [
            "Empresa", "Título", "Área", "Estado", "Tipo de contrato", "Modalidad",
            "Jornada", "Ubicación", "Email de contacto", "Fecha de apertura", "Creada",
        ]

    def test_sin_uuids_crudos(self) -> None:
        for original, fila in zip(_CATALOGO, construir_filas_export(_CATALOGO)):
            assert {"id", "empresa_id", "area_id"}.isdisjoint(fila.keys())
            assert original.id not in str(fila) and original.area_id not in str(fila)

    def test_NO_vuelca_los_bloques_de_texto_largo(self) -> None:
        """🔴 Son párrafos enteros: en una celda empujan el ancho de la fila hasta volver
        ilegible todo lo demás. El punto 5 del encabezado es lo que hace que esto pueda fallar:
        la primera vacante los trae cargados."""
        texto = str(construir_filas_export(_CATALOGO))
        assert _TEXTO_LARGO not in texto
        assert "#dev" not in texto and "urn:li:share" not in texto

    def test_cada_vacante_conserva_SUS_valores(self) -> None:
        filas = construir_filas_export(_CATALOGO)
        assert [f["Título"] for f in filas] == [
            "Dev Backend", "Analista de Cobranzas", "Contador Senior", "Pasantía IT"]
        assert [f["Modalidad"] for f in filas] == ["Híbrido", "Presencial", "Híbrido", None]
        assert [f["Ubicación"] for f in filas] == ["CABA", "Rosario", "CABA", None]

    def test_el_estado_sale_con_el_texto_de_la_pantalla(self) -> None:
        """`con_candidatos` es un valor de base, no algo que se le muestre a nadie. Son los
        mismos labels que ESTADO_LABELS de VacantesTable.tsx."""
        filas = construir_filas_export(_CATALOGO)
        assert [f["Estado"] for f in filas] == ["Nueva", "En proceso", "Cerrada", "Nueva"]
        assert "en_proceso" not in str(filas) and "con_candidatos" not in str(filas)

    def test_un_estado_desconocido_sale_crudo_y_no_vacio(self) -> None:
        """Un estado nuevo sin label es un dato raro, pero borrarlo escondería que existe."""
        rara = _CATALOGO[0].model_copy(update={"estado": "estado_futuro"})
        assert construir_filas_export([rara])[0]["Estado"] == "estado_futuro"

    def test_las_fechas_van_sin_hora_y_son_las_de_cada_una(self) -> None:
        filas = construir_filas_export(_CATALOGO)
        assert [f["Fecha de apertura"] for f in filas] == [
            "01/03/2026", "15/01/2026", "05/11/2025", ""]
        assert filas[0]["Creada"] == "20/02/2026"

    def test_una_vacante_con_todos_los_opcionales_vacios_no_rompe(self) -> None:
        """Punto 4: `fecha_apertura` en None tiene que dar '' y nunca la cadena "None"."""
        fila = construir_filas_export([_CATALOGO[3]])[0]
        assert fila["Título"] == "Pasantía IT"
        assert fila["Fecha de apertura"] == "" and "None" not in str(fila["Fecha de apertura"])
        assert fila["Tipo de contrato"] is None and fila["Email de contacto"] is None


# ── 3. El límite de export, de los dos lados ──────────────────────────────────

def test_el_export_chequea_el_limite_de_filas() -> None:
    svc, _ = _svc([_CATALOGO[0]] * (LIMITE_FILAS_EXPORT + 1))

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA, "excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_el_total_del_limite_respeta_el_filtro() -> None:
    """El mensaje dice "usá los filtros para acotar": si el conteo ignorara el filtro, ese
    consejo sería imposible de seguir. Las 5.001 son 'nueva'; filtrando por 'cerrada' salen 0."""
    svc, _ = _svc([_CATALOGO[0]] * (LIMITE_FILAS_EXPORT + 1))

    d = svc.exportar(EMPRESA, "csv", "cerrada")

    assert d.content is not None


def test_un_export_normal_NO_corta() -> None:
    svc, _ = _svc()

    d = svc.exportar(EMPRESA, "csv")

    assert d.content and d.filename.endswith(".csv")


def test_el_formato_llega_al_motor() -> None:
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(EMPRESA, formato).filename.endswith(ext)


def test_un_formato_inventado_se_rechaza() -> None:
    svc, _ = _svc()

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA, "xml")

    assert exc.value.code == "EXPORT_FORMATO_INVALIDO"


# ── 4. El router ──────────────────────────────────────────────────────────────

class TestElRouter:

    async def test_pasa_empresa_formato_y_estado(self) -> None:
        """El router recibiendo un parámetro no prueba nada: hay que seguirlo hasta abajo."""
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="vacantes.csv"))

        await router_mod.exportar_vacantes(
            request=_request(), formato="word", estado="cerrada", service=svc)

        assert recibido["args"] == (EMPRESA, "word", "cerrada")

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="vacantes.csv"))

        out = await router_mod.exportar_vacantes(request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="vacantes.csv"' in out.headers["Content-Disposition"]

    def test_exportar_esta_declarada_ANTES_de_get_por_id(self) -> None:
        """🔴 Acá /{id} SÍ existe, así que el orden es load-bearing y no una precaución
        teórica: al revés, "exportar" matchearía como un UUID y daría 422."""
        paths = [r.path for r in router_mod.router.routes]
        assert paths.index("/exportar") < paths.index("/{id}")
