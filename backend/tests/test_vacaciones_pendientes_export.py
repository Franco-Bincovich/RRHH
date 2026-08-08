"""
Export de días de vacaciones PENDIENTES: que traiga exactamente lo que este usuario ve.

🔴 ESTE EXPORT PUEDE FILTRAR DATOS, no solo traer filas de más. VACACIONES está en
`MANDOS_MEDIOS_SECCIONES`, así que un `mandos_medios` llega a este módulo y su universo NO lo
acota la empresa: lo acota el OWNERSHIP (a qué empleados llego por su `manager_id`). Un export
que le pegara al repo por su cuenta —aunque le pasara el `empresa_id`— le entregaría los días
de gente que no puede ver en ninguna pantalla, en un archivo, sin error y sin 403. Es el tercer
caso del repo con esta forma, después de /equipo y de las plantillas de onboarding.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL OWNERSHIP DEL FAKE DEVUELVE UN SUBCONJUNTO ESTRICTO. Si `ids_subordinados` devolviera
     a todos, "el export respeta el ownership" pasaría con el filtro borrado — el bug exacto a
     cubrir. Acá el mando medio tiene 1 de los 3 empleados a cargo.
  2. 🔴 EL REPO FAKE APLICA `empleado_ids` DE VERDAD. Un repo que aceptara la lista y devolviera
     siempre las tres filas volvería vacuo todo el archivo.
  3. 🔴 SE AFIRMA SOBRE EL CONTENIDO DEL CSV GENERADO, no sobre lo que devolvió el fake.
     Comparar contra `repo.find_all(...)` llamado a mano afirma que el FAKE filtra —cosa que ya
     se sabe— y deja pasar la mutación de fuga. Pasó exactamente eso en el export de plantillas
     de onboarding, en la sesión anterior; acá se hace al revés desde el principio.
  4. Los tres registros tienen empleado, área, período y números DISTINTOS: una proyección que
     emitiera constantes, o siempre la primera fila, rojea.
  5. Los `dias`/`dias_liquidados` están elegidos para que "Sin liquidar" NO coincida con ninguna
     de las dos columnas de origen (10-4=6, 5-5=0, 8-0=8): si la resta se reemplazara por `dias`
     o por `dias_liquidados`, se nota.
  6. El repo fake REGISTRA sus llamadas, así que se puede afirmar qué recibió — no solo qué
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

from datetime import datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
from starlette.requests import Request  # noqa: E402

import routers.vacaciones_pendientes as router_mod  # noqa: E402
from schemas.vacaciones_pendientes import VacacionPendienteResponse  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services._vacaciones_pendientes_export import construir_filas_export  # noqa: E402
from services.vacaciones_pendientes_service import VacacionesPendientesService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()
MI_SUBORDINADO = str(uuid4())
AJENO_1 = str(uuid4())
AJENO_2 = str(uuid4())
MANDO = str(uuid4())        # el USUARIO logueado
MANDO_EMP = str(uuid4())    # su EMPLEADO (de él cuelgan los subordinados)


def _pend(empleado_id: str, empleado: str, area: str, periodo: int, dias: int,
          liquidados: int) -> VacacionPendienteResponse:
    return VacacionPendienteResponse(
        id=str(uuid4()), empresa_id=str(EMPRESA), empresa_nombre="Karstec",
        empleado_id=empleado_id, empleado_nombre=empleado, area_id=str(uuid4()),
        area_nombre=area, periodo=periodo, dias=dias, dias_liquidados=liquidados,
        comentario=f"Saldo {periodo}", created_at=datetime(2026, 2, 10, 9, 0, 0),
    )


# Ver los puntos 4 y 5 del encabezado. La primera es la del subordinado del mando.
_CATALOGO = [
    _pend(MI_SUBORDINADO, "Ana Gómez", "Sistemas", 2024, 10, 4),
    _pend(AJENO_1, "Beto Pérez", "Comercial", 2025, 5, 5),
    _pend(AJENO_2, "Caro Díaz", "Legales", 2023, 8, 0),
]


class _Repo:
    """🔴 APLICA `empleado_ids` DE VERDAD (punto 2). Y devuelve el total del FILTRO, no el de la
    tabla: el chequeo de límite se hace sobre ese número."""

    def __init__(self, filas=None) -> None:
        self.llamadas: list[dict] = []
        self._filas = _CATALOGO if filas is None else filas

    def find_all(self, empresa_id=None, empleado_ids=None, page=1, page_size=20):
        self.llamadas.append({"empresa_id": empresa_id, "empleado_ids": empleado_ids,
                              "page": page, "page_size": page_size})
        filas = [f for f in self._filas
                 if empleado_ids is None or f.empleado_id in empleado_ids]
        return filas[(page - 1) * page_size: page * page_size], len(filas)


class _Ownership:
    """🔴 DEVUELVE UN SUBCONJUNTO ESTRICTO (punto 1). Con "todos", el archivo entero no puede
    desmentir nada.

    Modela el contrato real de `EmpleadoOwnershipRepo`: `find_by_user_id` resuelve el EMPLEADO
    del usuario logueado y `ids_subordinados` cuelga de ese empleado, no del usuario. El
    conjunto visible que arma `ownership.ids_empleados_visibles` es
    [su propio empleado, *sus subordinados] — el mando se ve a sí mismo, y por eso el catálogo
    NO tiene un registro suyo: así "ve 1 de 3" no depende de esa inclusión.
    """

    def find_by_user_id(self, user_id: str):
        return {"id": MANDO_EMP} if user_id == MANDO else None

    def ids_subordinados(self, empleado_id: str) -> list[str]:
        return [MI_SUBORDINADO] if empleado_id == MANDO_EMP else []


def _svc(filas=None):
    repo = _Repo(filas)
    return VacacionesPendientesService(
        repo=repo, audit=SimpleNamespace(registrar=lambda **k: None),
        ownership_repo=_Ownership(), empleado_repo=SimpleNamespace()), repo


def _csv(descarga) -> str:
    """El CSV generado, como texto. Es el único formato del motor que se lee sin parsear, así
    que es el que sirve para afirmar QUÉ filas terminaron en el archivo (punto 3)."""
    return descarga.content.decode("utf-8-sig")


def _request(rol: str = "admin_rrhh") -> Request:
    """Request real: `exportar_pendientes` está decorado con el rate limiter, que necesita leer
    la IP de un Request de starlette. Molde: test_proyectos_export.py."""
    req = Request({"type": "http", "path": "/api/vacaciones-pendientes/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": MANDO, "rol": rol}
    req.state.empresa_id = str(EMPRESA)
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_da_al_mando_UNO_de_los_tres_empleados() -> None:
    """Si el ownership devolviera a los tres, "el export respeta el ownership" pasaría con el
    filtro borrado. Y si devolviera cero, pasaría cualquier cosa que no traiga nada."""
    from services.ownership import ids_empleados_visibles

    own = _Ownership()
    assert ids_empleados_visibles(MANDO, "mandos_medios", own) == [MANDO_EMP, MI_SUBORDINADO]
    assert ids_empleados_visibles(MANDO, "admin_rrhh", own) is None  # admin: sin restricción
    assert len(_CATALOGO) == 3
    repo = _Repo()
    assert repo.find_all()[1] == 3
    assert repo.find_all(empleado_ids=[MANDO_EMP, MI_SUBORDINADO])[1] == 1


# ── 1. 🔴 El export no ve más que el listado ──────────────────────────────────

class TestOwnership:

    def test_un_mando_medio_solo_recibe_a_SU_gente(self) -> None:
        """🔴 El test central del módulo, afirmado sobre el CONTENIDO del archivo."""
        svc, _ = _svc()

        texto = _csv(svc.exportar(MANDO, "mandos_medios", EMPRESA, "csv"))

        assert "Ana Gómez" in texto
        assert "Beto Pérez" not in texto and "Caro Díaz" not in texto

    def test_un_admin_recibe_a_todos(self) -> None:
        """Contrapeso: sin esto, un export que devolviera siempre una sola fila pasaría arriba."""
        svc, _ = _svc()

        texto = _csv(svc.exportar(MANDO, "admin_rrhh", EMPRESA, "csv"))

        assert "Ana Gómez" in texto and "Beto Pérez" in texto and "Caro Díaz" in texto

    def test_listado_y_export_le_piden_al_repo_LO_MISMO(self) -> None:
        """Salvo la paginación, que el export no usa por diseño."""
        svc, repo = _svc()

        svc.get_all(MANDO, "mandos_medios", EMPRESA)
        svc.exportar(MANDO, "mandos_medios", EMPRESA, "csv")

        listado, export = repo.llamadas[0], repo.llamadas[1]
        assert listado["empleado_ids"] == export["empleado_ids"] == [MANDO_EMP, MI_SUBORDINADO]
        assert listado["empresa_id"] == export["empresa_id"]

    def test_el_export_no_se_pagina(self) -> None:
        """Pide una sola página del tamaño del tope: un export paginado entrega un archivo
        incompleto sin decirlo."""
        svc, repo = _svc()

        svc.exportar(MANDO, "admin_rrhh", EMPRESA, "csv")

        assert repo.llamadas[0]["page"] == 1
        assert repo.llamadas[0]["page_size"] == LIMITE_FILAS_EXPORT


# ── 2. Los filtros del listado llegan al export ───────────────────────────────

class TestFiltros:

    def test_el_filtro_por_empleado_llega_al_repo(self) -> None:
        svc, repo = _svc()

        svc.exportar(MANDO, "admin_rrhh", EMPRESA, "csv", None, AJENO_1)

        assert repo.llamadas[0]["empleado_ids"] == [AJENO_1]

    def test_el_filtro_por_empleado_recorta_el_ARCHIVO(self) -> None:
        svc, _ = _svc()

        texto = _csv(svc.exportar(MANDO, "admin_rrhh", EMPRESA, "csv", None, AJENO_1))

        assert "Beto Pérez" in texto
        assert "Ana Gómez" not in texto and "Caro Díaz" not in texto

    def test_sin_filtros_no_se_inventa_ninguno(self) -> None:
        """Contrapeso: con un filtro hardcodeado, el test de arriba pasaría igual."""
        svc, repo = _svc()

        svc.exportar(MANDO, "admin_rrhh", EMPRESA, "csv")

        assert repo.llamadas[0]["empleado_ids"] is None

    def test_en_consolidado_la_empresa_viaja_como_None(self) -> None:
        svc, repo = _svc()

        svc.exportar(MANDO, "admin_rrhh", None, "csv")

        assert repo.llamadas[0]["empresa_id"] is None


# ── 3. Las columnas ───────────────────────────────────────────────────────────

class TestColumnas:

    def test_son_las_esperadas_y_en_orden(self) -> None:
        assert list(construir_filas_export(_CATALOGO)[0]) == [
            "Empresa", "Empleado", "Área", "Período", "Días", "Liquidados",
            "Sin liquidar", "Comentario", "Cargado",
        ]

    def test_sin_uuids_crudos(self) -> None:
        for original, fila in zip(_CATALOGO, construir_filas_export(_CATALOGO)):
            assert {"id", "empresa_id", "empleado_id", "area_id"}.isdisjoint(fila.keys())
            assert original.id not in str(fila) and original.empleado_id not in str(fila)

    def test_cada_registro_conserva_SUS_valores(self) -> None:
        filas = construir_filas_export(_CATALOGO)
        assert [f["Empleado"] for f in filas] == ["Ana Gómez", "Beto Pérez", "Caro Díaz"]
        assert [f["Período"] for f in filas] == [2024, 2025, 2023]
        assert [f["Área"] for f in filas] == ["Sistemas", "Comercial", "Legales"]

    def test_sin_liquidar_es_la_RESTA_y_no_una_de_las_dos_columnas(self) -> None:
        """🔴 La columna por la que se abre este archivo: lo que la empresa todavía debe.
        Los números están elegidos para que la resta no coincida con `dias` ni con
        `dias_liquidados` en ninguna fila (punto 5 del encabezado)."""
        filas = construir_filas_export(_CATALOGO)
        assert [f["Sin liquidar"] for f in filas] == [6, 0, 8]
        assert [f["Días"] for f in filas] == [10, 5, 8]
        assert [f["Liquidados"] for f in filas] == [4, 5, 0]

    def test_liquidado_del_todo_da_cero_y_no_se_esconde(self) -> None:
        """0 sin liquidar es un dato: dice que ese período ya se pagó entero."""
        fila = construir_filas_export([_CATALOGO[1]])[0]
        assert fila["Sin liquidar"] == 0 and fila["Días"] == 5

    def test_la_fecha_va_sin_hora(self) -> None:
        assert construir_filas_export(_CATALOGO)[0]["Cargado"] == "10/02/2026"

    def test_sin_comentario_ni_area_no_rompe(self) -> None:
        """`comentario` y `area_nombre` son opcionales en el schema."""
        sin = _CATALOGO[0].model_copy(update={"comentario": None, "area_nombre": None})
        fila = construir_filas_export([sin])[0]
        assert fila["Comentario"] is None and fila["Área"] is None
        assert fila["Empleado"] == "Ana Gómez"


# ── 4. El límite de export, de los dos lados ──────────────────────────────────

# La inundación es de filas de un empleado AJENO al mando: así el mismo repo desborda el tope
# para un admin y queda en cero para el mando, que es lo que separa "contar la tabla" de
# "contar lo que este usuario ve".
_INUNDACION = [_CATALOGO[1]] * (LIMITE_FILAS_EXPORT + 1)


def test_el_export_chequea_el_limite_de_filas() -> None:
    svc, _ = _svc(_INUNDACION)

    with pytest.raises(AppError) as exc:
        svc.exportar(MANDO, "admin_rrhh", EMPRESA, "excel")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_el_total_del_limite_es_EL_QUE_ESTE_USUARIO_VE_no_el_de_la_tabla() -> None:
    """🔴 El mismo repo, el mismo pedido, otro rol: para el mando esas 5.001 filas son de un
    empleado ajeno, así que su export son 0 filas y NO tiene por qué cortar. Si el conteo se
    tomara de la tabla en vez del resultado filtrado, un mando medio no podría exportar nunca
    —y el mensaje "usá los filtros para acotar" sería un consejo imposible de seguir."""
    svc, _ = _svc(_INUNDACION)

    d = svc.exportar(MANDO, "mandos_medios", EMPRESA, "csv")

    assert d.content is not None
    assert "Beto Pérez" not in _csv(d)


def test_un_export_normal_NO_corta() -> None:
    svc, _ = _svc()

    d = svc.exportar(MANDO, "admin_rrhh", EMPRESA, "csv")

    assert d.content and d.filename.endswith(".csv")


def test_el_formato_llega_al_motor() -> None:
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(MANDO, "admin_rrhh", EMPRESA, formato).filename.endswith(ext)


def test_un_formato_inventado_se_rechaza() -> None:
    svc, _ = _svc()

    with pytest.raises(AppError) as exc:
        svc.exportar(MANDO, "admin_rrhh", EMPRESA, "xml")

    assert exc.value.code == "EXPORT_FORMATO_INVALIDO"


# ── 5. El router ──────────────────────────────────────────────────────────────

class TestElRouter:

    async def test_pasa_usuario_rol_empresa_formato_y_los_tres_filtros(self) -> None:
        """🔴 Si `user_id`/`rol` no viajaran, el service no podría aplicar el ownership y el
        archivo saldría con empleados fuera del alcance del rol."""
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="vacaciones_pendientes.csv"))
        area, proy = uuid4(), uuid4()

        await router_mod.exportar_pendientes(
            request=_request("mandos_medios"), formato="csv", area_id=area,
            empleado_id=None, proyecto_id=proy, service=svc)

        assert recibido["args"] == (MANDO, "mandos_medios", EMPRESA, "csv", area, None, proy)

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="vacaciones_pendientes.csv"))

        out = await router_mod.exportar_pendientes(
            request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="vacaciones_pendientes.csv"' in out.headers["Content-Disposition"]
