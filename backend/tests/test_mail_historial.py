"""
Historial de mails: que el filtro llegue del ROUTER hasta la QUERY, y que el techo no se pueda
levantar desde afuera.

`mail_enviado` se escribía desde la migración 087 y no lo leía nadie: el repo tenía `ultimos()`
sin un solo caller y no había ni service ni router. Esta tanda le puso la punta.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL FAKE MÁS BAJO ES EL CLIENTE DE SUPABASE, NO EL REPO. Un fake de repo que ACEPTE
     `estado`/`desde`/`hasta` y los ignore se lee igual que uno correcto, y el test pasaría con
     el `.eq()` borrado — es el caso #1 de la regla del repo, y acá la pregunta ES si el filtro
     llega a la query. `_Tabla` registra cada `.eq/.gte/.lte/.order/.limit` y los tests afirman
     sobre eso. Molde: `TestElOrdenLoPoneLaQuery` de `test_historial_salarial.py`.
  2. El orden se afirma con su `desc=True`: sacárselo dejaría "lo último enviado" abajo de todo,
     que es justo lo que nadie busca, y sin esta aserción el test no lo vería.
  3. Cada filtro se prueba PUESTO y AUSENTE. Con solo el caso puesto, un repo que aplicara el
     `.eq("estado", ...)` SIEMPRE pasaría, y el historial no podría mostrar los dos estados.
  4. El techo se prueba pidiendo MÁS del máximo: si el `min(limite, 200)` desapareciera, el
     caso de 500 devolvería 500 y el test rojea. Sin ese caso, el cap no está verificado.
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

import repositories.mail_enviado_repo as repo_mod  # noqa: E402
import routers.mail_historial as router_mod  # noqa: E402
from services.mail_historial_service import MailHistorialService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()

_FILA = {"id": str(uuid4()), "empresa_id": str(EMPRESA), "plantilla_clave": "bienvenida",
         "destinatario": "ana@k.com", "asunto_render": "Hola", "estado": "enviado",
         "error": None, "created_at": "2026-08-07T13:00:00+00:00"}


class _Tabla:
    """Fake del cliente de Supabase que REGISTRA lo que se le pidió. Es el único nivel donde se
    puede ver si el filtro viajó EN LA QUERY.

    ⚠️ Los atributos de registro NO se llaman como los métodos (`eqs`, no `eq`): un atributo de
    instancia con el mismo nombre pisa al método y la segunda llamada encadenada revienta con
    `'list' object is not callable`. Pasó al escribir este archivo."""

    def __init__(self, filas) -> None:
        self.filas = filas
        self.eqs: dict = {}
        self.gtes: dict = {}
        self.ltes: dict = {}
        self.ordenes: list = []
        self.limite = None
        self.select_spec = None

    def select(self, spec):
        self.select_spec = spec
        return self

    def order(self, col, desc=False):
        self.ordenes.append((col, desc))
        return self

    def limit(self, n):
        self.limite = n
        return self

    def eq(self, col, val):
        self.eqs[col] = val
        return self

    def gte(self, col, val):
        self.gtes[col] = val
        return self

    def lte(self, col, val):
        self.ltes[col] = val
        return self

    def execute(self):
        return SimpleNamespace(data=self.filas)


def _repo(monkeypatch, filas=None):
    tabla = _Tabla(filas if filas is not None else [_FILA])
    monkeypatch.setattr(repo_mod, "supabase_admin", SimpleNamespace(table=lambda _n: tabla))
    return repo_mod.MailEnviadoRepo(), tabla


def _request(empresa_id) -> Request:
    req = Request({"type": "http", "path": "/api/mails", "headers": [], "client": ("7.7.7.7", 1)})
    req.state.user = {"id": "u1", "rol": "admin_rrhh"}
    req.state.empresa_id = empresa_id
    return req


# ── 1. El filtro llega a la QUERY ─────────────────────────────────────────────

class TestElFiltroLoAplicaLaQuery:

    def test_el_estado_viaja_como_eq(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ultimos(estado="fallido")

        assert tabla.eqs.get("estado") == "fallido"

    def test_sin_estado_NO_hay_eq(self, monkeypatch) -> None:
        """Contrapeso: con el `.eq` incondicional, el historial mostraría un solo estado."""
        repo, tabla = _repo(monkeypatch)

        repo.ultimos()

        assert "estado" not in tabla.eqs

    def test_el_rango_viaja_como_gte_y_lte_sobre_created_at(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ultimos(desde="2026-08-01T00:00:00+00:00", hasta="2026-08-07T23:59:59+00:00")

        assert tabla.gtes.get("created_at") == "2026-08-01T00:00:00+00:00"
        assert tabla.ltes.get("created_at") == "2026-08-07T23:59:59+00:00"

    def test_sin_rango_no_hay_gte_ni_lte(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ultimos()

        assert tabla.gtes == {} and tabla.ltes == {}

    def test_la_empresa_viaja_como_eq(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ultimos(empresa_id=EMPRESA)

        assert tabla.eqs.get("empresa_id") == str(EMPRESA)

    def test_en_consolidado_no_se_filtra_por_empresa(self, monkeypatch) -> None:
        """El historial es una VISTA: sin empresa activa muestra las de todas."""
        repo, tabla = _repo(monkeypatch)

        repo.ultimos(empresa_id=None)

        assert "empresa_id" not in tabla.eqs


class TestElOrdenYElTechoLosPoneLaQuery:

    def test_ordena_por_fecha_DESCENDENTE(self, monkeypatch) -> None:
        """Lo último enviado es lo que se busca. Sin el `desc=True` queda al final de todo."""
        repo, tabla = _repo(monkeypatch)

        repo.ultimos()

        assert tabla.ordenes == [("created_at", True)]

    def test_el_techo_de_200_no_se_puede_levantar_desde_afuera(self, monkeypatch) -> None:
        """`mail_enviado` tiene datos personales: el límite duro es lo que impide que esto se
        vuelva un volcado de la tabla. Sin el `min`, esto devolvería 500."""
        repo, tabla = _repo(monkeypatch)

        repo.ultimos(limite=500)

        assert tabla.limite == 200

    def test_un_limite_chico_se_respeta(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        repo.ultimos(limite=10)

        assert tabla.limite == 10

    def test_el_cuerpo_del_mail_NO_sale_en_el_select(self, monkeypatch) -> None:
        """🔴 `cuerpo_render` es el texto completo que recibió una persona. El select es una
        allowlist justamente para que no viaje a un listado; un `select("*")` lo largaría."""
        repo, tabla = _repo(monkeypatch)

        repo.ultimos()

        assert "cuerpo_render" not in tabla.select_spec
        assert "*" not in tabla.select_spec


# ── 2. El service compone los bordes del día ──────────────────────────────────

class TestLosBordesDelDia:

    def test_hasta_se_estira_al_FIN_del_dia(self, monkeypatch) -> None:
        """🔴 `created_at` es un timestamp: comparar contra la fecha pelada equivale a las 00:00,
        así que "hasta el 7/8" dejaría afuera todo lo enviado ESE día. El síntoma sería "el mail
        que mandé hoy no aparece", que se lee como que el envío falló."""
        repo, tabla = _repo(monkeypatch)

        MailHistorialService(repo).listar(hasta="2026-08-07")

        assert tabla.ltes["created_at"].startswith("2026-08-07T23:59")

    def test_desde_arranca_al_COMIENZO_del_dia(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        MailHistorialService(repo).listar(desde="2026-08-01")

        assert tabla.gtes["created_at"].startswith("2026-08-01T00:00")

    def test_una_fecha_ilegible_se_ignora_en_vez_de_romper_la_pantalla(self, monkeypatch) -> None:
        repo, tabla = _repo(monkeypatch)

        MailHistorialService(repo).listar(desde="no-es-una-fecha")

        assert tabla.gtes == {}

    def test_un_estado_inventado_se_rechaza(self, monkeypatch) -> None:
        """Fail-closed: un estado desconocido devolvería cero filas en silencio, y la pantalla
        diría "todavía no se envió ningún mail" con la tabla llena."""
        repo, _ = _repo(monkeypatch)

        with pytest.raises(AppError) as exc:
            MailHistorialService(repo).listar(estado="rebotado")

        assert exc.value.code == "ESTADO_INVALIDO" and exc.value.status_code == 422

    def test_los_dos_estados_reales_se_aceptan(self, monkeypatch) -> None:
        """Contrapeso: sin esto, un service que rechazara TODO pasaría el test de arriba."""
        for estado in ("enviado", "fallido"):
            repo, tabla = _repo(monkeypatch)
            MailHistorialService(repo).listar(estado=estado)
            assert tabla.eqs["estado"] == estado


# ── 3. Del ROUTER al repo, con los nombres del contrato ───────────────────────

class TestElRouterPasaLosFiltros:

    async def test_los_tres_query_params_llegan_al_service(self, monkeypatch) -> None:
        """El router recibiendo un parámetro no prueba nada: hay que seguirlo hasta abajo."""
        recibido: dict = {}
        monkeypatch.setattr(router_mod, "MailHistorialService", lambda: SimpleNamespace(
            listar=lambda **kw: recibido.update(kw) or SimpleNamespace(items=[], limite=0)))

        await router_mod.listar(request=_request(str(EMPRESA)), estado="fallido",
                                fecha_desde="2026-08-01", fecha_hasta="2026-08-07", limite=50)

        assert recibido == {"empresa_id": EMPRESA, "estado": "fallido",
                            "desde": "2026-08-01", "hasta": "2026-08-07", "limite": 50}

    async def test_en_consolidado_la_empresa_llega_como_None(self, monkeypatch) -> None:
        """Es una VISTA, no una acción: sin empresa activa devuelve las de todas, no un 400.
        Es el opuesto deliberado del ENVÍO, que exige empresa concreta."""
        recibido: dict = {}
        monkeypatch.setattr(router_mod, "MailHistorialService", lambda: SimpleNamespace(
            listar=lambda **kw: recibido.update(kw) or SimpleNamespace(items=[], limite=0)))

        await router_mod.listar(request=_request(None))

        assert recibido["empresa_id"] is None

    async def test_el_router_gatea_por_configuracion_igual_que_plantillas(self) -> None:
        """La sección NO cambió al mudar la pantalla a /comunicacion: crear una `Seccion` nueva
        habría tocado el espejo manual permisos.py ↔ permisos.ts para el mismo resultado."""
        import routers.plantillas as plantillas_mod

        assert router_mod.SECCION is plantillas_mod.SECCION


# ── 4. El contrato de salida ──────────────────────────────────────────────────

class TestLaRespuesta:

    def test_mapea_las_filas_y_devuelve_el_limite(self, monkeypatch) -> None:
        repo, _ = _repo(monkeypatch)

        out = MailHistorialService(repo).listar(limite=25)

        assert out.limite == 25 and len(out.items) == 1
        assert out.items[0].destinatario == "ana@k.com" and out.items[0].estado == "enviado"

    def test_un_fallido_conserva_el_motivo(self, monkeypatch) -> None:
        """Es el dato que alguien viene a buscar cuando pregunta "¿por qué no le llegó?"."""
        fallido = {**_FILA, "estado": "fallido", "error": "MAIL_ERROR_PROVEEDOR: rechazado"}
        repo, _ = _repo(monkeypatch, filas=[fallido])

        out = MailHistorialService(repo).listar()

        assert out.items[0].error == "MAIL_ERROR_PROVEEDOR: rechazado"

    def test_sin_filas_devuelve_lista_vacia_sin_romper(self, monkeypatch) -> None:
        repo, _ = _repo(monkeypatch, filas=[])

        assert MailHistorialService(repo).listar().items == []
