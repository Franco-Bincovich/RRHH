"""
🔒 Export de "mi equipo": el ÚNICO export del repo donde el filtro puede filtrar DATOS.

En todos los demás módulos el universo lo acota un Query (`estado`, `area_id`, `empresa_id`), y
el peor caso de equivocarse es un archivo con más filas de las que se ven. Acá el universo lo
acota el OWNERSHIP —`ids_empleados_visibles(user_id, rol)`—, así que un export que armara su
propia consulta le entregaría a un `mandos_medios` la nómina de gente que no puede ver en ninguna
otra pantalla. Sin error, sin aviso, y con el archivo ya bajado.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 HAY **DOS** MANDOS CON SUBORDINADOS DISTINTOS Y DISJUNTOS. Es la condición del archivo:
     con un solo manager, "respetó el ownership" y "trajo todo" devuelven el mismo conjunto y el
     bug no se puede expresar. Cada test afirma las dos mitades — que estén los propios Y que NO
     esté la gente del otro.
  2. 🔴 EL REPO DE PROYECCIÓN FILTRA DE VERDAD por la lista de ids que recibe, y con `None`
     devuelve TODO el padrón. Un fake que devolviera siempre las mismas filas haría pasar el test
     del mando con el filtro borrado — es el caso #1 de la regla del repo.
  3. HAY CONTRAPESO DE ADMIN: sin él, un export que devolviera SIEMPRE vacío pasaría el test de
     "no ve a los del otro" y dejaría la feature muerta en vez de insegura.
  4. La equivalencia listado↔export se afirma POR COMPORTAMIENTO —mismo `user_id`+`rol` dan el
     mismo conjunto en los dos caminos— y no leyendo el código: el export podría llamar a
     `get_equipo` y aun así recortar después.
  5. El padrón tiene gente de DOS empresas y un mando tiene un subordinado de la otra: si alguien
     "arreglara" el export sumándole un filtro por empresa, ese subordinado desaparecería y el
     test rojea.
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

import routers.equipo as router_mod  # noqa: E402
from services._equipo_export import construir_filas_export  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services.equipo_service import EquipoService  # noqa: E402
from utils.errors import AppError  # noqa: E402

# ── El padrón: dos mandos, subordinados DISJUNTOS, y uno cruzado de empresa ───

USER_ANA, USER_BETO, USER_ADMIN = "u-ana", "u-beto", "u-admin"
EMP_ANA, EMP_BETO = "e-ana", "e-beto"

# id → (nombre, apellido, empresa)
_PADRON = {
    EMP_ANA:  ("Ana", "Gómez", "SERVICIOS Y CONSULTORIA"),
    "e-a1":   ("Carla", "Ruiz", "SERVICIOS Y CONSULTORIA"),
    # 🔴 Subordinado de Ana en OTRA empresa del grupo: el modelo lo permite y el export no
    # puede recortarlo (ver `_alcance_mandos.py`).
    "e-a2":   ("Diego", "Sosa", "KARSTEC - IT NET"),
    EMP_BETO: ("Beto", "Pérez", "KARSTEC - IT NET"),
    "e-b1":   ("Elena", "Vera", "KARSTEC - IT NET"),
    "e-b2":   ("Fabio", "Luna", "SERVICIOS Y CONSULTORIA"),
}

_SUBORDINADOS = {EMP_ANA: ["e-a1", "e-a2"], EMP_BETO: ["e-b1", "e-b2"]}
_USUARIOS = {USER_ANA: {"id": EMP_ANA}, USER_BETO: {"id": EMP_BETO}}


class _OwnershipRepo:
    """Doble de `EmpleadoOwnershipRepo`. Dos mandos con gente distinta — sin eso, el archivo no
    puede desmentir nada."""

    def find_by_user_id(self, user_id: str):
        return _USUARIOS.get(user_id)

    def ids_subordinados(self, empleado_id: str):
        return list(_SUBORDINADOS.get(empleado_id, []))


class _EquipoRepo:
    """🔴 FILTRA DE VERDAD por la lista de ids, y con `None` devuelve el padrón COMPLETO —
    el mismo contrato que `EquipoRepo.find_equipo`. Un fake que devolviera siempre lo mismo
    haría pasar el test del mando con el filtro borrado."""

    def __init__(self) -> None:
        self.llamadas: list = []

    def find_equipo(self, ids):
        self.llamadas.append(ids)
        elegidos = _PADRON.items() if ids is None else [(i, _PADRON[i]) for i in ids if i in _PADRON]
        return [{"id": _uuid(i), "nombre": n, "apellido": a, "empresa": e}
                for i, (n, a, e) in sorted(elegidos, key=lambda kv: (kv[1][1], kv[1][0]))]


# Los ids del padrón son legibles ("e-ana") pero el schema pide UUID: se mapean a UUIDs estables.
_UUIDS: dict = {}


def _uuid(clave: str):
    return _UUIDS.setdefault(clave, uuid4())


def _svc():
    equipo = _EquipoRepo()
    return EquipoService(ownership_repo=_OwnershipRepo(), equipo_repo=equipo), equipo


def _apellidos(filas) -> set:
    return {f["Apellido"] for f in filas}


def _request(user_id: str, rol: str) -> Request:
    """Request real: `exportar_equipo` está decorado con el rate limiter, que necesita leer la IP
    de un Request de starlette. Molde: test_reporte_area.py."""
    req = Request({"type": "http", "path": "/api/equipo/exportar", "headers": [],
                   "client": ("8.8.8.8", 1)})
    req.state.user = {"id": user_id, "rol": rol}
    return req


# ── 0. Los guardianes del fake ────────────────────────────────────────────────

def test_el_fake_tiene_DOS_mandos_con_gente_DISJUNTA() -> None:
    """Sin dos mandos, "respetó el ownership" y "trajo todo" son indistinguibles."""
    ana = {EMP_ANA, *_SUBORDINADOS[EMP_ANA]}
    beto = {EMP_BETO, *_SUBORDINADOS[EMP_BETO]}
    assert ana and beto and ana.isdisjoint(beto)
    assert len(_PADRON) == len(ana) + len(beto), "el padrón tiene que ser la unión de los dos"


def test_el_fake_tiene_un_subordinado_de_OTRA_empresa() -> None:
    """Si el padrón fuera de una sola empresa, un filtro por empresa de más pasaría inadvertido."""
    empresas_de_ana = {_PADRON[i][2] for i in _SUBORDINADOS[EMP_ANA]}
    assert len(empresas_de_ana) > 1


# ── 1. 🔴 El mando exporta SOLO a su gente ────────────────────────────────────

class TestElExportRespetaElOwnership:

    def test_un_mando_exporta_a_los_suyos(self) -> None:
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))

        assert _apellidos(filas) == {"Gómez", "Ruiz", "Sosa"}

    def test_y_NO_a_la_gente_del_OTRO_mando(self) -> None:
        """🔴 La mitad que importa. Sin el segundo mando en el fake, esto no se puede afirmar."""
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))

        assert _apellidos(filas).isdisjoint({"Pérez", "Vera", "Luna"})

    def test_el_otro_mando_ve_lo_suyo_y_no_lo_de_Ana(self) -> None:
        """Simétrico: descarta que el fake esté devolviendo un conjunto fijo que casualmente
        coincide con el de Ana."""
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_BETO, "mandos_medios"))

        assert _apellidos(filas) == {"Pérez", "Vera", "Luna"}
        assert _apellidos(filas).isdisjoint({"Gómez", "Ruiz", "Sosa"})

    def test_el_export_le_pasa_al_repo_la_lista_ACOTADA(self) -> None:
        """Un escalón más abajo: lo que llega al repo son los ids del mando, no `None`."""
        svc, repo = _svc()

        svc.exportar(USER_ANA, "mandos_medios", "csv")

        assert repo.llamadas == [[EMP_ANA, "e-a1", "e-a2"]]

    def test_un_mando_SIN_empleado_vinculado_exporta_vacio_sin_tocar_la_DB(self) -> None:
        """Fail-closed. `manager_id` está 0/19 en producción, así que este es el caso real hoy."""
        svc, repo = _svc()

        d = svc.exportar("u-fantasma", "mandos_medios", "csv")

        assert repo.llamadas == [], "no debió consultar el padrón"
        assert d.content and d.filename.endswith(".csv")

    def test_un_rol_desconocido_exporta_vacio(self) -> None:
        svc, repo = _svc()

        svc.exportar(USER_ANA, "rol_inventado", "csv")

        assert repo.llamadas == []


# ── 2. 🔴 El contrapeso: el admin trae todo ───────────────────────────────────

class TestElAdminTraeTodo:
    """Sin esto, un export que devolviera SIEMPRE vacío pasaría todos los tests de arriba."""

    def test_admin_exporta_el_padron_completo(self) -> None:
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_ADMIN, "admin_rrhh"))

        assert _apellidos(filas) == {"Gómez", "Ruiz", "Sosa", "Pérez", "Vera", "Luna"}

    def test_gerencia_lectura_tambien(self) -> None:
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_ADMIN, "gerencia_lectura"))

        assert len(filas) == len(_PADRON)

    def test_al_admin_el_repo_lo_recibe_como_None_no_como_una_lista(self) -> None:
        """`None` ES la señal de "sin restricción" (contrato de `ids_empleados_visibles`).
        Mandar la lista completa funcionaría hoy y se rompería con el padrón real."""
        svc, repo = _svc()

        svc.exportar(USER_ADMIN, "admin_rrhh", "csv")

        assert repo.llamadas == [None]


# ── 3. 🔴 Listado y export son EL MISMO camino (por comportamiento) ───────────

class TestListadoYExportCoinciden:
    """Se verifica por COMPORTAMIENTO, no leyendo el código: el export podría llamar a
    `get_equipo` y recortar después, y eso también tiene que rojear."""

    @pytest.mark.parametrize("user_id,rol", [
        (USER_ANA, "mandos_medios"),
        (USER_BETO, "mandos_medios"),
        (USER_ADMIN, "admin_rrhh"),
        (USER_ADMIN, "gerencia_lectura"),
        ("u-fantasma", "mandos_medios"),
        (USER_ANA, "rol_inventado"),
    ])
    def test_mismo_usuario_mismo_conjunto_en_los_dos_caminos(self, user_id, rol) -> None:
        svc_listado, repo_listado = _svc()
        svc_export, repo_export = _svc()

        svc_listado.get_equipo(user_id, rol)
        svc_export.exportar(user_id, rol, "csv")

        # Misma pregunta al repo de proyección: mismo universo, en los dos caminos.
        assert repo_listado.llamadas == repo_export.llamadas

    def test_el_archivo_trae_EXACTAMENTE_lo_que_muestra_la_pantalla(self) -> None:
        svc, _ = _svc()

        de_la_pantalla = {(m.apellido, m.nombre) for m in svc.get_equipo(USER_ANA, "mandos_medios")}
        del_archivo = {(f["Apellido"], f["Nombre"])
                       for f in construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))}

        assert de_la_pantalla == del_archivo and len(del_archivo) == 3


# ── 4. 🔴 El ownership CRUZA empresas y el export no lo recorta ───────────────

class TestElOwnershipCruzaEmpresas:
    """Decisión de producto: un mando puede tener subordinados de otra empresa del grupo, y para
    `mandos_medios` el `manager_id` REEMPLAZA al filtro de empresa (ver `_alcance_mandos.py`)."""

    def test_el_subordinado_de_otra_empresa_SIGUE_en_el_archivo(self) -> None:
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))

        sosa = [f for f in filas if f["Apellido"] == "Sosa"]
        assert sosa, "se recortó por empresa: el subordinado cruzado desapareció"
        assert sosa[0]["Empresa"] == "KARSTEC - IT NET"

    def test_el_archivo_de_un_mando_puede_tener_DOS_empresas(self) -> None:
        svc, _ = _svc()

        filas = construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))

        assert len({f["Empresa"] for f in filas}) == 2


# ── 5. La proyección ──────────────────────────────────────────────────────────

class TestLaProyeccion:

    def test_sin_UUIDs_crudos(self) -> None:
        svc, _ = _svc()

        fila = construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))[0]

        assert {"id", "empleado_id", "empresa_id"}.isdisjoint(fila.keys())
        assert str(_uuid(EMP_ANA)) not in str(fila)

    def test_las_tres_columnas_y_nada_mas(self) -> None:
        """El roster expone identidad mínima a propósito: un `mandos_medios` NO tiene permiso de
        EMPLEADOS, y sumar campos convertiría este export en la puerta de atrás a la ficha."""
        svc, _ = _svc()

        fila = construir_filas_export(svc.get_equipo(USER_ANA, "mandos_medios"))[0]

        assert list(fila.keys()) == ["Apellido", "Nombre", "Empresa"]

    def test_una_empresa_sin_cargar_no_rompe(self) -> None:
        from schemas.equipo import EquipoMiembroResponse

        fila = construir_filas_export([EquipoMiembroResponse(
            id=uuid4(), nombre="Sin", apellido="Empresa", empresa=None)])[0]

        assert fila["Empresa"] is None and fila["Apellido"] == "Empresa"


# ── 6. Límite, formatos y router ──────────────────────────────────────────────

def test_el_limite_muerde() -> None:
    muchos = [{"id": _uuid(EMP_ANA), "nombre": "A", "apellido": "B", "empresa": "K"}] * (
        LIMITE_FILAS_EXPORT + 1)
    svc = EquipoService(ownership_repo=_OwnershipRepo(),
                        equipo_repo=SimpleNamespace(find_equipo=lambda ids: muchos))

    with pytest.raises(AppError) as exc:
        svc.exportar(USER_ADMIN, "admin_rrhh", "csv")

    assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"


def test_un_export_normal_NO_corta() -> None:
    """Contrapeso: sin esto, un `verificar_limite_export` que rechazara siempre pasaría arriba."""
    svc, _ = _svc()

    assert svc.exportar(USER_ANA, "mandos_medios", "csv").filename.endswith(".csv")


def test_los_cuatro_formatos_llegan_al_motor() -> None:
    svc, _ = _svc()

    for formato, ext in (("csv", ".csv"), ("excel", ".xlsx"), ("word", ".docx"), ("pdf", ".pdf")):
        assert svc.exportar(USER_ANA, "mandos_medios", formato).filename.endswith(ext)


async def test_el_router_pasa_el_USUARIO_DEL_REQUEST_al_service() -> None:
    """🔴 Lo que define el universo sale del token, no de un Query. Si el router mandara otra
    cosa —o dejara que el cliente eligiera—, sería la vía para pedir gente ajena."""
    recibido: dict = {}
    svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
        content=b"x", media_type="text/csv", filename="equipo.csv"))

    await router_mod.exportar_equipo(request=_request(USER_BETO, "mandos_medios"),
                                     formato="csv", service=svc)

    assert recibido["args"] == (USER_BETO, "mandos_medios", "csv")


async def test_el_router_devuelve_el_archivo_con_su_nombre() -> None:
    svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
        content=b"contenido", media_type="text/csv", filename="equipo.csv"))

    out = await router_mod.exportar_equipo(request=_request(USER_ANA, "mandos_medios"),
                                           formato="csv", service=svc)

    assert out.body == b"contenido"
    assert 'filename="equipo.csv"' in out.headers["Content-Disposition"]
