"""
Export de offboardings activos: que salga del MISMO listado que la pantalla y que las listas
anidadas salgan CONTADAS, no volcadas.

Este módulo NO acota su universo por token: `Seccion.OFFBOARDING` no está en
`MANDOS_MEDIOS_SECCIONES`, así que solo llegan admin_rrhh y gerencia_lectura, para quienes el
ownership no restringe. El único eje es la empresa. Por eso acá no hay tests de ownership:
agregarlos sería código que aparenta seguridad sin verificar nada.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 LOS OFFBOARDINGS TIENEN LISTAS DE ACTIVOS Y ACCESOS DE VERDAD, con distinto grado de
     devolución (3 de 5, 0 de 2, 0 de 0). Si todos tuvieran las listas vacías, "los activos van
     contados" pasaría con `sum(...)` reemplazado por `0`, y "no se vuelcan" pasaría con la
     proyección borrada: no habría nada que volcar.
  2. 🔴 UNO NO TIENE NINGÚN ACTIVO. "0 de 0" y "0 de 5" dan los dos 0% de progreso y significan
     cosas distintas; sin ese caso, la columna de total se podría borrar sin que nada rojee.
  3. Los tres tienen empleado, motivo y fecha DISTINTOS: una proyección que emitiera constantes
     —o siempre la primera fila— rojea.
  4. Los tres motivos son distintos y uno NO está en el diccionario de labels: así se prueba la
     traducción y el fallback en el mismo catálogo.
  5. Uno tiene `notas_entrevista` cargadas: es contra eso que se comprueba que NO salgan. Sin
     notas en la entrada, esa aserción pasaría con la proyección borrada.
  6. `fecha_inicio` llega como STRING ISO (así lo devuelve el repo), no como date: un `_fecha`
     copiado de otro módulo —que llama a `.strftime()`— reventaría acá.
  7. El repo fake registra sus llamadas y se afirma sobre el CONTENIDO del CSV generado.
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

import routers.offboarding as router_mod  # noqa: E402
from schemas.offboarding import AccesoResponse, ActivoResponse, OffboardingResponse  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services._offboarding_export import construir_filas_export  # noqa: E402
from services.offboarding_service import OffboardingService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()

_NOTAS = "Dijo que se va por el clima del equipo y mencionó a su jefe directo."


def _activo(devuelto: bool) -> ActivoResponse:
    return ActivoResponse(id=uuid4(), tipo_activo="Notebook", descripcion=None,
                          estado="pendiente", devuelto=devuelto)


def _acceso(revocado: bool) -> AccesoResponse:
    return AccesoResponse(id=uuid4(), tipo="VPN", descripcion=None, revocado=revocado)


def _off(empleado: str, motivo: str, fecha: str, devueltos: int, total: int,
         accesos_rev: int, accesos_total: int, progreso: int, **kw) -> OffboardingResponse:
    base = dict(
        id=uuid4(), empleado_id=uuid4(), empresa_id=EMPRESA, empresa_nombre="Karstec",
        empleado_nombre=empleado, motivo=motivo, estado="en_curso", fecha_inicio=fecha,
        progreso=progreso, entrevista_salida=False, notas_entrevista=None,
        activos=[_activo(i < devueltos) for i in range(total)],
        accesos=[_acceso(i < accesos_rev) for i in range(accesos_total)],
    )
    return OffboardingResponse(**{**base, **kw})


# Ver los puntos 1-6 del encabezado.
_CATALOGO = [
    _off("Ana Gómez", "renuncia", "2026-03-01", 3, 5, 1, 2, 60,
         entrevista_salida=True, notas_entrevista=_NOTAS),
    _off("Beto Pérez", "despido", "2026-01-15", 0, 2, 0, 3, 0),
    # Sin activos ni accesos: "0 de 0" (punto 2). Y con un motivo sin label (punto 4).
    _off("Caro Díaz", "motivo_futuro", "2025-11-20", 0, 0, 0, 0, 0),
]


class _Repo:
    """Registra las llamadas: así se puede afirmar que listado y export van al MISMO método."""

    def __init__(self, filas=None) -> None:
        self.llamadas: list = []
        self._filas = _CATALOGO if filas is None else filas

    def find_activos(self, empresa_id=None):
        self.llamadas.append({"empresa_id": empresa_id})
        return self._filas


def _svc(filas=None):
    repo = _Repo(filas)
    return OffboardingService(repo=repo, empleado_repo=SimpleNamespace(),
                              audit=SimpleNamespace(registrar=lambda **k: None)), repo


def _csv(descarga) -> str:
    """El CSV generado, como texto: sirve para afirmar QUÉ terminó en el archivo."""
    return descarga.content.decode("utf-8-sig")


def _request() -> Request:
    """Request real: `exportar_offboardings` está decorado con el rate limiter, que necesita
    leer la IP de un Request de starlette. Molde: test_proyectos_export.py."""
    req = Request({"type": "http", "path": "/api/offboarding/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    req.state.empresa_id = str(EMPRESA)
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_tiene_listas_reales_y_un_proceso_sin_activos() -> None:
    """Con las listas vacías en todos, "van contados" y "no se vuelcan" pasarían con la
    proyección borrada. Y sin el de 0 activos, la columna de total sería inobservable."""
    assert [len(o.activos) for o in _CATALOGO] == [5, 2, 0]
    assert [sum(1 for a in o.activos if a.devuelto) for o in _CATALOGO] == [3, 0, 0]
    assert [len(o.accesos) for o in _CATALOGO] == [2, 3, 0]
    assert _CATALOGO[0].notas_entrevista == _NOTAS
    assert isinstance(_CATALOGO[0].fecha_inicio, str)   # punto 6: llega como string ISO


# ── 1. Las listas anidadas ────────────────────────────────────────────────────

class TestActivosYAccesos:

    def test_van_CONTADOS_y_no_volcados(self) -> None:
        """🔴 `activos` y `accesos` son listas de objetos: el motor renderiza escalares, así que
        volcarlas dejaría el `repr` de Python dentro de una celda."""
        filas = construir_filas_export(_CATALOGO)
        assert [f["Activos devueltos"] for f in filas] == [3, 0, 0]
        assert [f["Activos totales"] for f in filas] == [5, 2, 0]
        assert "activos" not in filas[0] and "ActivoResponse" not in str(filas)
        assert "accesos" not in filas[0] and "AccesoResponse" not in str(filas)

    def test_los_accesos_se_cuentan_aparte_de_los_activos(self) -> None:
        """Son dos cosas distintas: devolver una notebook no es revocar la VPN. El segundo
        offboarding tiene 0 de 2 activos y 0 de 3 accesos — si se contaran juntos, no se vería."""
        fila = construir_filas_export(_CATALOGO)[1]
        assert fila["Activos totales"] == 2 and fila["Accesos totales"] == 3

    def test_cero_de_cero_no_se_confunde_con_cero_de_cinco(self) -> None:
        """Los dos dan 0% de progreso y significan cosas distintas: uno es un proceso sin
        activos asignados, el otro es uno donde no se devolvió nada."""
        filas = construir_filas_export(_CATALOGO)
        sin_activos, sin_devolver = filas[2], filas[1]
        assert sin_activos["Activos totales"] == 0 and sin_devolver["Activos totales"] == 2
        assert sin_activos["Progreso"] == sin_devolver["Progreso"] == "0%"


# ── 2. Las demás columnas ─────────────────────────────────────────────────────

class TestColumnas:

    def test_son_las_esperadas_y_en_orden(self) -> None:
        assert list(construir_filas_export(_CATALOGO)[0]) == [
            "Empresa", "Colaborador", "Motivo", "Estado", "Inicio",
            "Activos devueltos", "Activos totales", "Progreso",
            "Accesos revocados", "Accesos totales", "Entrevista de salida",
        ]

    def test_sin_uuids_crudos(self) -> None:
        for original, fila in zip(_CATALOGO, construir_filas_export(_CATALOGO)):
            assert {"id", "empleado_id", "empresa_id"}.isdisjoint(fila.keys())
            assert str(original.id) not in str(fila)
            assert str(original.empleado_id) not in str(fila)

    def test_las_notas_de_la_entrevista_NO_salen(self) -> None:
        """🔴 Es texto libre sobre por qué se fue una persona — el campo que no se quiere en un
        archivo que se manda por mail. El flag de si se hizo sí sale: eso es seguimiento."""
        filas = construir_filas_export(_CATALOGO)
        assert _NOTAS not in str(filas)
        assert "notas_entrevista" not in filas[0]
        assert [f["Entrevista de salida"] for f in filas] == ["Sí", "No", "No"]

    def test_cada_proceso_conserva_SUS_valores(self) -> None:
        filas = construir_filas_export(_CATALOGO)
        assert [f["Colaborador"] for f in filas] == ["Ana Gómez", "Beto Pérez", "Caro Díaz"]
        assert [f["Progreso"] for f in filas] == ["60%", "0%", "0%"]

    def test_el_motivo_sale_con_el_texto_de_la_pantalla(self) -> None:
        """Mismos labels que MOTIVO_LABEL del front. `despido` se muestra como
        "Desvinculación": el enum crudo no es lo que se le pone delante a nadie."""
        filas = construir_filas_export(_CATALOGO)
        assert [f["Motivo"] for f in filas] == ["Renuncia", "Desvinculación", "motivo_futuro"]
        assert "despido" not in str(filas)

    def test_la_fecha_de_inicio_llega_como_STRING_y_se_formatea(self) -> None:
        """🔴 El repo la devuelve como str ISO, no como date: un `_fecha` copiado de otro
        módulo —que llama a `.strftime()`— reventaría con AttributeError."""
        assert [f["Inicio"] for f in construir_filas_export(_CATALOGO)] == [
            "01/03/2026", "15/01/2026", "20/11/2025"]

    def test_una_fecha_vacia_da_string_vacio_y_no_None(self) -> None:
        sin = _CATALOGO[0].model_copy(update={"fecha_inicio": ""})
        assert construir_filas_export([sin])[0]["Inicio"] == ""


# ── 3. Listado y export salen del MISMO lugar ─────────────────────────────────

class TestListadoYExportCoinciden:

    def test_los_dos_van_al_mismo_metodo_del_repo(self) -> None:
        svc, repo = _svc()

        svc.get_offboardings_activos(EMPRESA)
        svc.exportar(EMPRESA, "csv")

        assert repo.llamadas == [{"empresa_id": EMPRESA}, {"empresa_id": EMPRESA}]

    def test_el_archivo_trae_los_MISMOS_procesos_que_el_listado(self) -> None:
        svc, _ = _svc()

        texto = _csv(svc.exportar(EMPRESA, "csv"))

        assert "Ana Gómez" in texto and "Beto Pérez" in texto and "Caro Díaz" in texto

    def test_en_consolidado_la_empresa_viaja_como_None(self) -> None:
        svc, repo = _svc()

        svc.exportar(None, "csv")

        assert repo.llamadas[0]["empresa_id"] is None


# ── 4. El límite de export, de los dos lados ──────────────────────────────────

def test_el_export_chequea_el_limite_de_filas() -> None:
    svc, _ = _svc([_CATALOGO[0]] * (LIMITE_FILAS_EXPORT + 1))

    with pytest.raises(AppError) as exc:
        svc.exportar(EMPRESA, "excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_un_export_normal_NO_corta() -> None:
    """Contrapeso: sin esto, un chequeo que rechazara siempre pasaría el test de arriba."""
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


# ── 5. El router ──────────────────────────────────────────────────────────────

class TestElRouter:

    async def test_pasa_empresa_y_formato(self) -> None:
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="offboardings.csv"))

        await router_mod.exportar_offboardings(request=_request(), formato="pdf", service=svc)

        assert recibido["args"] == (EMPRESA, "pdf")

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="offboardings.csv"))

        out = await router_mod.exportar_offboardings(request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="offboardings.csv"' in out.headers["Content-Disposition"]
