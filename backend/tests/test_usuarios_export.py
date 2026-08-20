"""
Export de usuarios del sistema: que salga del MISMO listado que la pantalla y que NO filtre
nada que no deba salir de la base.

Este export es distinto de los otros del repo en una cosa: lista PERSONAS CON ACCESO. El modo
de falla que más caro sale acá no es traer filas de más, es traer COLUMNAS de más — un Excel
con el estado de la credencial de cada usuario se manda por mail sin pensarlo dos veces.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 LAS FILAS DEL FAKE TRAEN LOS CAMPOS SENSIBLES PUESTOS. `listar_activos` hoy proyecta
     seis columnas, así que un fake que devolviera solo esas seis haría que
     `test_no_filtra_*` pase CON LA PROYECCIÓN BORRADA: no habría nada sensible que filtrar.
     Acá las filas llegan con `password_hash`, `must_change_password`, `ultimo_acceso` y `id`,
     como si mañana alguien ensanchara el `select` del repo — que es exactamente el día en que
     este test tiene que gritar.
  2. 🔴 SON TRES USUARIOS CON VALORES DISTINTOS EN CADA COLUMNA. Con uno solo, una proyección
     que emitiera constantes ("Nombre": "Ana") pasaría todos los asserts de contenido. Y con
     tres iguales, una que devolviera siempre la primera fila también.
  3. Los tres tienen ROLES DISTINTOS, así que la traducción de rol se prueba de verdad: si
     `_rol` devolviera siempre el mismo label, el conjunto de roles del archivo colapsaría.
  4. El fake REGISTRA sus llamadas, así que se puede afirmar que el listado y el export pegan
     al MISMO método — no solo que los dos devuelven algo.
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

import routers.usuarios as router_mod  # noqa: E402
from services._limite_export import LIMITE_FILAS_EXPORT  # noqa: E402
from services._usuarios_export import construir_filas_export  # noqa: E402
from services.usuario_service import UsuarioService  # noqa: E402
from utils.errors import AppError  # noqa: E402

# 🔴 Las filas llevan MÁS campos de los que el repo proyecta hoy. Ver el punto 1 del encabezado:
# sin esto, "no filtra credenciales" no podría fallar ni con la proyección borrada.
_CATALOGO = [
    {
        "id": str(uuid4()), "nombre": "Ana", "apellido": "Gómez", "email": "ana@karstec.com",
        "username": "agomez", "rol": "admin_rrhh",
        "password_hash": "$2b$12$NOdebeSalirNuncaEnUnExcel", "must_change_password": True,
        "ultimo_acceso": "2026-08-01T10:00:00+00:00", "activo": True,
    },
    {
        "id": str(uuid4()), "nombre": "Beto", "apellido": "Pérez", "email": "beto@karstec.com",
        "username": "bperez", "rol": "gerencia_lectura",
        "password_hash": "$2b$12$TampocoEste", "must_change_password": False,
        "ultimo_acceso": "2026-07-15T08:30:00+00:00", "activo": True,
    },
    {
        "id": str(uuid4()), "nombre": "Caro", "apellido": "Díaz", "email": "caro@karstec.com",
        "username": "cdiaz", "rol": "mandos_medios",
        "password_hash": "$2b$12$NiEste", "must_change_password": False,
        "ultimo_acceso": None, "activo": True,
    },
]

# Todo lo que NO puede aparecer en el archivo, ni como key ni como valor.
_PROHIBIDO_COMO_KEY = {"id", "password_hash", "must_change_password", "ultimo_acceso", "username"}


class _Repo:
    """Registra las llamadas: así se puede afirmar que listado y export van al MISMO método."""

    def __init__(self, filas=None) -> None:
        self.llamadas: list[str] = []
        self._filas = _CATALOGO if filas is None else filas

    def listar_activos(self) -> list[dict]:
        self.llamadas.append("listar_activos")
        return self._filas


def _svc(filas=None):
    repo = _Repo(filas)
    return UsuarioService(repo=repo, audit=SimpleNamespace(registrar=lambda **k: None),
                          remitente_repo=SimpleNamespace()), repo


def _request() -> Request:
    """Request real: `exportar_usuarios` está decorado con el rate limiter, que necesita leer
    la IP de un Request de starlette. Molde: test_proyectos_export.py."""
    req = Request({"type": "http", "path": "/api/usuarios/exportar", "headers": [],
                   "client": ("5.5.5.5", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_trae_campos_sensibles_y_tres_usuarios_distintos() -> None:
    """Si esto falla, TODO lo de abajo pasa a ser decorativo: sin campos sensibles en la
    entrada no hay nada que la proyección pueda filtrar, y sin valores distintos no se
    distingue una proyección real de una que emite constantes."""
    assert len(_CATALOGO) == 3
    assert all("password_hash" in u and "ultimo_acceso" in u for u in _CATALOGO)
    assert len({u["nombre"] for u in _CATALOGO}) == 3
    assert len({u["rol"] for u in _CATALOGO}) == 3


# ── 1. 🔴 El archivo no puede decir más que la pantalla ───────────────────────

class TestLoQueNoSale:

    def test_no_hay_keys_de_credencial_ni_de_id(self) -> None:
        for fila in construir_filas_export(_CATALOGO):
            assert _PROHIBIDO_COMO_KEY.isdisjoint(fila.keys())

    @pytest.mark.parametrize("campo", ["password_hash", "ultimo_acceso", "id"])
    def test_ningun_VALOR_sensible_viaja_en_la_fila(self, campo: str) -> None:
        """No alcanza con que la KEY no esté: el valor podría salir bajo otro nombre."""
        filas = construir_filas_export(_CATALOGO)
        for original, fila in zip(_CATALOGO, filas):
            valor = original[campo]
            if valor:
                assert str(valor) not in str(fila), f"{campo} viajó en el export"

    def test_el_flag_de_cambio_de_password_no_sale_ni_como_booleano(self) -> None:
        """`must_change_password` dice a quién le vence la clave. No es asunto de un Excel."""
        texto = str(construir_filas_export(_CATALOGO))
        assert "must_change" not in texto and "True" not in texto


# ── 2. Las columnas que SÍ salen ──────────────────────────────────────────────

class TestLoQueSale:

    def test_las_columnas_son_las_de_la_tabla_de_la_pantalla(self) -> None:
        """UsuariosTable.tsx muestra Nombre · Apellido · Email · Usuario · Rol. El archivo
        agrega Activo (constante 'Sí' por construcción: el listado trae solo activos)."""
        assert list(construir_filas_export(_CATALOGO)[0]) == [
            "Nombre", "Apellido", "Email", "Usuario", "Rol", "Activo",
        ]

    def test_cada_usuario_conserva_SUS_valores(self) -> None:
        """Contrapeso del punto 2 del encabezado: con constantes, esto rojea."""
        filas = construir_filas_export(_CATALOGO)
        assert [f["Nombre"] for f in filas] == ["Ana", "Beto", "Caro"]
        assert [f["Email"] for f in filas] == [
            "ana@karstec.com", "beto@karstec.com", "caro@karstec.com"]

    def test_el_rol_sale_traducido_y_distinto_por_usuario(self) -> None:
        filas = construir_filas_export(_CATALOGO)
        assert [f["Rol"] for f in filas] == [
            "Administrador Capital Humano", "Gerencia (solo lectura)", "Mando medio"]

    def test_un_rol_desconocido_sale_crudo_y_no_vacio(self) -> None:
        """Un rol nuevo sin label es un dato raro, pero borrarlo escondería que existe."""
        fila = construir_filas_export([{**_CATALOGO[0], "rol": "rol_futuro"}])[0]
        assert fila["Rol"] == "rol_futuro"

    def test_un_usuario_dado_de_baja_saldria_marcado(self) -> None:
        """Hoy no puede pasar (el listado filtra activos), pero la columna no miente si el
        día de mañana el listado dejara de filtrar."""
        assert construir_filas_export([{**_CATALOGO[0], "activo": False}])[0]["Activo"] == "No"


# ── 3. 🔴 Listado y export salen del MISMO lugar ──────────────────────────────

class TestListadoYExportCoinciden:
    """La query vivía en el router. Al bajarla al repo, lo que hay que fijar es que las dos
    puntas sigan yendo al mismo método: dos consultas separadas divergen sin avisar."""

    def test_los_dos_van_al_mismo_metodo_del_repo(self) -> None:
        svc, repo = _svc()

        svc.listar()
        svc.exportar("excel")

        assert repo.llamadas == ["listar_activos", "listar_activos"]

    def test_el_archivo_trae_EXACTAMENTE_los_usuarios_del_listado(self) -> None:
        svc, _ = _svc()

        listado = svc.listar()

        assert listado["total"] == 3
        esperados = {f["Email"] for f in construir_filas_export(listado["items"])}
        assert esperados == {"ana@karstec.com", "beto@karstec.com", "caro@karstec.com"}


# ── 4. El límite de export, de los dos lados ──────────────────────────────────

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


# ── 5. El router pasa lo que recibe ───────────────────────────────────────────

class TestElRouter:

    async def test_el_formato_llega_al_service(self) -> None:
        """El router recibiendo un parámetro no prueba nada: hay que seguirlo hasta abajo."""
        recibido: dict = {}
        svc = SimpleNamespace(exportar=lambda *a: recibido.update(args=a) or SimpleNamespace(
            content=b"x", media_type="text/csv", filename="usuarios.csv"))

        await router_mod.exportar_usuarios(request=_request(), formato="word", service=svc)

        assert recibido["args"] == ("word",)

    async def test_devuelve_el_archivo_con_su_nombre(self) -> None:
        svc = SimpleNamespace(exportar=lambda *a: SimpleNamespace(
            content=b"contenido", media_type="text/csv", filename="usuarios.csv"))

        out = await router_mod.exportar_usuarios(request=_request(), formato="csv", service=svc)

        assert out.body == b"contenido"
        assert 'filename="usuarios.csv"' in out.headers["Content-Disposition"]

    async def test_el_listado_tambien_pasa_por_el_service(self) -> None:
        """Antes pegaba a supabase_admin desde el router. Si vuelve a hacerlo, el export deja
        de compartir origen con la pantalla."""
        svc = SimpleNamespace(listar=lambda: {"items": [], "total": 0})

        assert await router_mod.list_usuarios(request=_request(), service=svc) == {
            "items": [], "total": 0}
