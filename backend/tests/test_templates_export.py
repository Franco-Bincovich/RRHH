"""
Export de plantillas de onboarding: que traiga EXACTAMENTE lo que este usuario ve.

🔴 ESTE EXPORT PUEDE FILTRAR DATOS, no solo filas de más. En los módulos con filtros por Query
el peor caso es un archivo más largo de la cuenta; acá el universo lo acota la VISIBILIDAD
(públicas de mi empresa + privadas mías), que el backend resuelve desde el token. Un export que
no le pase `user_id`/`rol` al repo devuelve las plantillas PRIVADAS de otros usuarios en un
archivo descargable — sin error, sin 403 y sin nada en pantalla que lo delate. Es el mismo
riesgo que el export de /equipo.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL REPO FAKE APLICA LA VISIBILIDAD DE VERDAD. Un fake que aceptara `user_id`/`rol` y
     devolviera siempre las cuatro plantillas haría que "el export respeta la visibilidad" pase
     CON LOS PARÁMETROS BORRADOS — que es exactamente el bug a cubrir. Acá filtra: públicas de
     la empresa pedida, más las privadas cuyo autor sea `user_id`.
  2. 🔴 HAY UNA PRIVADA DE OTRO USUARIO. Sin ella no habría nada que el filtro pudiera dejar
     afuera y cualquier implementación pasaría.
  3. Hay plantillas de DOS empresas, así que perder el `empresa_id` también se nota.
  4. Las cuatro tienen nombres, autores y conteos de tareas DISTINTOS: una proyección que
     emitiera constantes o siempre la primera fila rojea.
  5. El fake REGISTRA con qué argumentos lo llamaron: se puede afirmar que el export mandó los
     tres, no solo que devolvió algo.
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
from starlette.requests import Request  # noqa: E402

import routers.onboarding_templates as router_mod  # noqa: E402
from schemas.onboarding import TemplateResponse  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services._onboarding_templates_export import construir_filas_export  # noqa: E402
from services.onboarding_templates_service import OnboardingTemplatesService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A = uuid4()
EMPRESA_B = uuid4()
YO = str(uuid4())
OTRO = str(uuid4())


def _tmpl(nombre: str, empresa, autor, autor_nombre: str, publica: bool, tareas: int) -> TemplateResponse:
    return TemplateResponse(
        id=uuid4(), nombre=nombre, empresa_id=empresa,
        empresa_nombre="Karstec" if empresa == EMPRESA_A else "DOSUBA",
        descripcion=f"Plantilla {nombre}", created_by=autor, created_by_nombre=autor_nombre,
        es_publica=publica, tareas=[], tareas_total=tareas,
    )


# Ver los puntos 1-4 del encabezado. La tercera es LA que no puede salir en el archivo de YO.
_CATALOGO = [
    _tmpl("Ingreso general", EMPRESA_A, YO, "Sofía RRHH", True, 8),
    _tmpl("Ingreso IT", EMPRESA_A, OTRO, "Juan Pérez", True, 12),
    _tmpl("Borrador de Juan", EMPRESA_A, OTRO, "Juan Pérez", False, 3),
    _tmpl("Ingreso DOSUBA", EMPRESA_B, YO, "Sofía RRHH", True, 5),
]


class _Repo:
    """🔴 APLICA LA VISIBILIDAD DE VERDAD. Sin esto, el archivo entero no puede desmentir nada."""

    def __init__(self, filas=None) -> None:
        self.llamadas: list[dict] = []
        self._filas = _CATALOGO if filas is None else filas

    def get_templates(self, empresa_id=None, user_id=None, rol=None):
        self.llamadas.append({"empresa_id": empresa_id, "user_id": user_id, "rol": rol})
        return [
            t for t in self._filas
            if (empresa_id is None or t.empresa_id == empresa_id)
            # gerencia_lectura ve todo; el resto, públicas + las propias.
            and (rol == "gerencia_lectura" or t.es_publica or str(t.created_by) == str(user_id))
        ]


def _svc(filas=None):
    repo = _Repo(filas)
    return OnboardingTemplatesService(repo=repo), repo


def _csv(descarga) -> str:
    """El CSV generado, como texto. Es el único formato del motor que se puede leer sin
    parsear nada, así que es el que sirve para afirmar QUÉ filas terminaron en el archivo —
    no qué devolvió el repo."""
    return descarga.content.decode("utf-8-sig")


def _request() -> Request:
    req = Request({"type": "http", "path": "/api/onboarding/templates/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": YO, "rol": "admin_rrhh"}
    req.state.empresa_id = str(EMPRESA_A)
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_esconde_la_privada_ajena_y_reparte_en_dos_empresas() -> None:
    """Si el fake no filtrara, "el export respeta la visibilidad" pasaría con los parámetros
    borrados — el bug exacto que este archivo viene a cubrir."""
    repo = _Repo()
    assert len(repo.get_templates()) == 3                      # la privada de OTRO ya no está
    assert len(repo.get_templates(user_id=OTRO)) == 4          # para su autor, sí
    assert len(repo.get_templates(empresa_id=EMPRESA_A, user_id=YO)) == 2
    assert len(repo.get_templates(rol="gerencia_lectura")) == 4


# ── 1. 🔴 El export no puede ver más que el listado ───────────────────────────

class TestVisibilidad:

    def test_los_tres_parametros_llegan_al_repo(self) -> None:
        svc, repo = _svc()

        svc.exportar(EMPRESA_A, YO, "admin_rrhh", "excel")

        assert repo.llamadas[0] == {"empresa_id": EMPRESA_A, "user_id": YO, "rol": "admin_rrhh"}

    def test_la_privada_de_otro_usuario_NO_entra_en_el_archivo(self) -> None:
        """🔴 El test central del módulo.

        ⚠️ Se afirma sobre EL CONTENIDO DEL ARCHIVO, no sobre lo que devuelve el fake. La
        primera versión de este test comparaba contra `repo.get_templates(...)` llamado a mano,
        y eso afirma que el FAKE filtra —cosa que ya se sabe— en vez de que lo haga el export:
        borrarle `user_id`/`rol` al service lo dejaba en verde. Verificado por mutación."""
        svc, _ = _svc()

        texto = _csv(svc.exportar(EMPRESA_A, YO, "admin_rrhh", "csv"))

        assert "Borrador de Juan" not in texto
        assert "Ingreso general" in texto and "Ingreso IT" in texto

    def test_para_su_autor_la_privada_SI_entra(self) -> None:
        """Contrapeso: sin esto, un export que devolviera siempre vacío pasaría el de arriba."""
        svc, _ = _svc()

        texto = _csv(svc.exportar(EMPRESA_A, OTRO, "admin_rrhh", "csv"))

        assert "Borrador de Juan" in texto

    def test_la_de_la_otra_empresa_tampoco_entra(self) -> None:
        """Mismo criterio con el otro eje: perder el `empresa_id` también se ve en el archivo."""
        svc, _ = _svc()

        texto = _csv(svc.exportar(EMPRESA_A, YO, "admin_rrhh", "csv"))

        assert "Ingreso DOSUBA" not in texto

    def test_listado_y_export_devuelven_el_MISMO_conjunto(self) -> None:
        svc, repo = _svc()

        svc.get_templates(EMPRESA_A, YO, "admin_rrhh")
        svc.exportar(EMPRESA_A, YO, "admin_rrhh", "excel")

        assert repo.llamadas[0] == repo.llamadas[1]

    def test_en_consolidado_la_empresa_viaja_como_None(self) -> None:
        svc, repo = _svc()

        svc.exportar(None, YO, "admin_rrhh", "excel")

        assert repo.llamadas[0]["empresa_id"] is None


# ── 2. Las columnas ───────────────────────────────────────────────────────────

class TestColumnas:

    def test_son_las_esperadas_y_en_orden(self) -> None:
        assert list(construir_filas_export(_CATALOGO)[0]) == [
            "Empresa", "Plantilla", "Descripción", "Autor", "Visibilidad", "Tareas",
        ]

    def test_sin_uuids_crudos(self) -> None:
        for original, fila in zip(_CATALOGO, construir_filas_export(_CATALOGO)):
            assert {"id", "empresa_id", "created_by"}.isdisjoint(fila.keys())
            assert str(original.id) not in str(fila)
            assert str(original.created_by) not in str(fila)

    def test_cada_plantilla_conserva_SUS_valores(self) -> None:
        filas = construir_filas_export(_CATALOGO)
        assert [f["Plantilla"] for f in filas] == [
            "Ingreso general", "Ingreso IT", "Borrador de Juan", "Ingreso DOSUBA"]
        assert [f["Tareas"] for f in filas] == [8, 12, 3, 5]

    def test_la_visibilidad_distingue_publica_de_privada(self) -> None:
        assert [f["Visibilidad"] for f in construir_filas_export(_CATALOGO)] == [
            "Pública", "Pública", "Privada", "Pública"]

    def test_la_visibilidad_no_sale_como_booleano(self) -> None:
        texto = str(construir_filas_export(_CATALOGO))
        assert "True" not in texto and "False" not in texto

    def test_las_tareas_van_CONTADAS_y_no_volcadas(self) -> None:
        """🔴 `tareas` es una lista de objetos anidados: el motor renderiza escalares, así que
        volcarla dejaría el `repr` de Python en la celda."""
        con_tareas = _CATALOGO[0].model_copy(update={"tareas_total": 2})
        fila = construir_filas_export([con_tareas])[0]
        assert fila["Tareas"] == 2
        assert "tareas" not in fila and "TareaResponse" not in str(fila)

    def test_una_plantilla_sin_autor_no_rompe(self) -> None:
        """`created_by` es NULL en las anteriores al cableado del autor y en las huérfanas."""
        huerfana = _CATALOGO[0].model_copy(update={"created_by": None, "created_by_nombre": None})
        assert construir_filas_export([huerfana])[0]["Autor"] is None


# ── 3. El límite de export, de los dos lados ──────────────────────────────────

def test_el_export_chequea_el_limite_de_filas() -> None:
    svc, _ = _svc([_CATALOGO[0]] * (LIMITE_FILAS_EXPORT + 1))

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA_A, YO, "admin_rrhh", "excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_un_export_normal_NO_corta() -> None:
    svc, _ = _svc()

    d = svc.exportar(EMPRESA_A, YO, "admin_rrhh", "csv")

    assert d.content and d.filename.endswith(".csv")


def test_el_formato_llega_al_motor() -> None:
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(EMPRESA_A, YO, "admin_rrhh", formato).filename.endswith(ext)


def test_un_formato_inventado_se_rechaza() -> None:
    svc, _ = _svc()

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA_A, YO, "admin_rrhh", "xml")

    assert exc.value.code == "EXPORT_FORMATO_INVALIDO"


# ── 4. El router ──────────────────────────────────────────────────────────────

class TestElRouter:

    async def test_pasa_empresa_usuario_rol_y_formato(self) -> None:
        """🔴 El router recibiendo el request no prueba nada: si `sujeto(request)` no viajara,
        el service recibiría None en user_id y el archivo saldría con las privadas ajenas."""
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="plantillas_onboarding.csv"))

        await router_mod.exportar_templates(request=_request(), formato="csv", svc=svc)

        assert recibido["args"] == (EMPRESA_A, YO, "admin_rrhh", "csv")

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="plantillas_onboarding.csv"))

        out = await router_mod.exportar_templates(request=_request(), formato="csv", svc=svc)

        assert out.body == b"contenido"
        assert 'filename="plantillas_onboarding.csv"' in out.headers["Content-Disposition"]

    def test_exportar_esta_declarada_ANTES_de_get_por_id(self) -> None:
        """Si /{template_id} se registrara primero, "exportar" matchearía como un UUID y el
        endpoint devolvería 422 en vez de un archivo."""
        paths = [r.path for r in router_mod.router.routes]
        assert paths.index("/exportar") < paths.index("/{template_id}")
