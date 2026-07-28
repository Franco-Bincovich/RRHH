"""
Autor de un template de onboarding (`created_by`), de punta a punta.

POR QUÉ EXISTE. La columna `created_by` está en la tabla desde la migración 007 con FK a
`users`, pero NINGÚN camino de escritura la escribía: el repo insertaba
`{nombre, descripcion, activo, empresa_id}` y el router ni siquiera recibía `request`, así que
no tenía de dónde sacar el usuario. Toda plantilla creada por la app nacía con
`created_by = NULL`. Es un bug propio, anterior a la visibilidad pública/privada, y el
prerrequisito de esa feature: sin autor, "privada" no puede tener dueño.

🚨 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR.
La pregunta no es retórica: el modo de falla obvio acá es un `_FakeRepo.create_template()` que
devuelve un `TemplateResponse` PREFABRICADO ignorando los argumentos. Con ese fake, "el alta
registra el autor" da verde **aunque el repo nunca ponga created_by en el INSERT** — el test
estaría afirmando algo sobre su propia constante.

Por eso hay dos niveles, y el que importa es el segundo:
  · `_RepoQueEcha` CONSTRUYE la respuesta a partir de lo que recibe. Cubre router → service.
  · `TestElInsertLlevaElAutor` faltea un escalón más abajo —el cliente de Supabase— y mira el
    PAYLOAD REAL del insert. Es el único que puede detectar que el repo se olvide de la
    columna, que es exactamente el bug que esta tanda vino a cerrar.

El fake de empresa HONRA `empresa_id` (dos empresas, devuelve None si no coincide): un fake
que lo acepta y lo ignora daría verde sin validar nada.
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

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from starlette.requests import Request

from repositories import onboarding_templates_repo as repo_mod
from repositories._onboarding_templates_row import SELECT_DETALLE, SELECT_LISTA, template
from routers.onboarding_templates import create_template as router_create
from schemas.onboarding import TemplateCreate, TemplateResponse
from services.onboarding_templates_service import OnboardingTemplatesService
from tests._postgrest_schema import SelectInvalidoError, cargar_schema
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
USUARIO = "d911f67d-aa41-4559-a20c-731c837844a3"
PROPIO = UUID("11111111-1111-1111-1111-111111111111")
AJENO = UUID("22222222-2222-2222-2222-222222222222")


# ─── router → service: el usuario del request llega al service ────────────────


class _RepoQueEcha:
    """Construye la respuesta A PARTIR de lo que recibe. No devuelve nada prefabricado."""

    def __init__(self) -> None:
        self.recibido: dict = {}

    def create_template(self, nombre, descripcion, empresa_id, created_by=None):
        self.recibido = {"nombre": nombre, "descripcion": descripcion,
                         "empresa_id": empresa_id, "created_by": created_by}
        return TemplateResponse(id=uuid4(), nombre=nombre, descripcion=descripcion,
                                empresa_id=empresa_id, created_by=created_by)


def _request(user: dict) -> Request:
    req = Request({"type": "http", "path": "/api/onboarding/templates", "headers": [],
                   "client": ("9.0.0.1", 1)})
    req.state.user = user
    return req


def _body() -> TemplateCreate:
    return TemplateCreate(nombre="Onboarding Técnico", empresa_id=EMPRESA_A)


class TestElRouterPasaElUsuario:
    async def test_el_autor_llega_al_service(self) -> None:
        repo = _RepoQueEcha()
        await router_create(_body(), _request({"id": USUARIO, "rol": "admin_rrhh"}),
                            OnboardingTemplatesService(repo))
        assert repo.recibido["created_by"] == USUARIO

    async def test_sin_id_de_usuario_va_none_y_no_un_placeholder(self) -> None:
        """`created_by` tiene FK a users: un literal como "system" —el fallback que usan
        empleados/areas/empresa— reventaría el INSERT. None es lo que la columna significa."""
        repo = _RepoQueEcha()
        await router_create(_body(), _request({"rol": "admin_rrhh"}),
                            OnboardingTemplatesService(repo))
        assert repo.recibido["created_by"] is None

    async def test_la_empresa_sigue_saliendo_del_body(self) -> None:
        """Crear es una ACCIÓN: la empresa es un dato explícito del form, no del header."""
        repo = _RepoQueEcha()
        req = _request({"id": USUARIO, "rol": "admin_rrhh"})
        req.state.empresa_id = str(EMPRESA_B)          # el sidebar dice otra cosa
        await router_create(_body(), req, OnboardingTemplatesService(repo))
        assert repo.recibido["empresa_id"] == EMPRESA_A


# ─── repo → base: el INSERT real lleva la columna ─────────────────────────────


class _TablaFake:
    """Captura el payload del insert. Devuelve la fila cruda, SIN los embeds — que es lo que
    PostgREST devuelve en un insert (los joins solo aparecen en un select)."""

    def __init__(self, capturado: dict) -> None:
        self._cap = capturado

    def insert(self, payload):
        self._cap.update(payload)
        return self

    def execute(self):
        return SimpleNamespace(data=[{**self._cap, "id": str(uuid4())}], count=1)


class TestElInsertLlevaElAutor:
    """🔴 El test que puede fallar de verdad: mira el payload que sale hacia la base."""

    def _crear(self, monkeypatch, created_by):
        capturado: dict = {}
        monkeypatch.setattr(
            repo_mod, "supabase_admin",
            SimpleNamespace(table=lambda _t: _TablaFake(capturado)),
        )
        tmpl = repo_mod.OnboardingTemplatesRepo().create_template(
            "T", None, EMPRESA_A, created_by,
        )
        return capturado, tmpl

    def test_created_by_viaja_en_el_payload(self, monkeypatch) -> None:
        capturado, _ = self._crear(monkeypatch, USUARIO)
        assert capturado["created_by"] == USUARIO

    def test_none_se_persiste_como_none(self, monkeypatch) -> None:
        """La clave va igual, con None: omitirla dejaría el default de la columna, que es lo
        mismo hoy, pero hace al repo dependiente de un default que nadie declaró acá."""
        capturado, _ = self._crear(monkeypatch, None)
        assert "created_by" in capturado and capturado["created_by"] is None

    def test_la_empresa_sigue_en_el_payload(self, monkeypatch) -> None:
        capturado, _ = self._crear(monkeypatch, USUARIO)
        assert capturado["empresa_id"] == str(EMPRESA_A)

    def test_la_respuesta_del_alta_expone_el_autor(self, monkeypatch) -> None:
        _, tmpl = self._crear(monkeypatch, USUARIO)
        assert str(tmpl.created_by) == USUARIO
        # Sin nombre: el insert no trae el join. El front navega al detalle enseguida, así que
        # esa fila no se muestra; el listado sí lo resuelve (ver TestElListadoResuelveElNombre).
        assert tmpl.created_by_nombre is None


# ─── el mapper resuelve el nombre del autor ───────────────────────────────────


class TestElListadoResuelveElNombre:
    def test_resuelve_el_embed_a_nombre(self) -> None:
        t = template({"id": str(PROPIO), "nombre": "T", "empresa_id": str(EMPRESA_A),
                      "created_by": USUARIO, "creador": {"nombre": "Alejandra"},
                      "empresas": {"nombre": "DOSUBA"}})
        assert t.created_by_nombre == "Alejandra" and str(t.created_by) == USUARIO

    def test_sin_autor_el_nombre_es_none_y_no_rompe(self) -> None:
        """Template viejo o usuario borrado (FK ON DELETE SET NULL). No es un error."""
        t = template({"id": str(PROPIO), "nombre": "T", "empresa_id": str(EMPRESA_A),
                      "created_by": None, "creador": None, "empresas": {"nombre": "DOSUBA"}})
        assert t.created_by is None and t.created_by_nombre is None

    @pytest.mark.parametrize("select", [SELECT_LISTA, SELECT_DETALLE])
    def test_los_dos_select_piden_el_autor(self, select: str) -> None:
        """Si un select se olvida de la columna, el mapper devuelve None en silencio."""
        assert "created_by" in select and "creador:created_by(nombre)" in select


class TestLosSelectSobrevivenAPostgrest:
    """🔴 Los embeds son el punto ciego del fake de Supabase: `select()` acepta cualquier cosa.

    Estos dos selects se validan contra db/schema.sql como lo haría PostgREST. Al escribirlos
    apareció un bug PREVIO: el embed de tareas era ambiguo —hay DOS FKs entre onboarding_tareas
    y onboarding_templates, la simple y la compuesta con empresa_id del retrofit— así que los
    dos endpoints de lectura respondían 300 PGRST201 en vez de datos. Se nombró la FK.

    Es el mismo molde que test_reportes_columnas.py, que cubre los generadores de reportes y
    no llega hasta acá.
    """

    @pytest.mark.parametrize("select", [SELECT_LISTA, SELECT_DETALLE], ids=["lista", "detalle"])
    def test_el_select_es_resoluble(self, select: str) -> None:
        cargar_schema().validar_select("onboarding_templates", select)

    def test_sin_nombrar_la_fk_el_embed_de_tareas_es_ambiguo(self) -> None:
        """Guarda contra el falso verde: si algún día la ambigüedad desapareciera (p. ej. se
        dropea la FK compuesta), este test avisa de que el hint dejó de ser necesario — y que
        el de arriba pasó a probar menos de lo que parece."""
        with pytest.raises(SelectInvalidoError, match="AMBIGUO"):
            cargar_schema().validar_select("onboarding_templates", "id,onboarding_tareas(id)")


# ─── la barrera de empresa sigue cerrada ──────────────────────────────────────


class _RepoDosEmpresas:
    """HONRA empresa_id: dos empresas, None cuando no coincide."""

    def __init__(self) -> None:
        self._t = {
            str(PROPIO): TemplateResponse(id=PROPIO, nombre="T", empresa_id=EMPRESA_A, created_by=USUARIO),
            str(AJENO): TemplateResponse(id=AJENO, nombre="T", empresa_id=EMPRESA_B, created_by=USUARIO),
        }

    def get_template(self, template_id, empresa_id=None):
        t = self._t.get(str(template_id))
        if not t or (empresa_id and str(t.empresa_id) != str(empresa_id)):
            return None
        return t


class TestLaBarreraDeEmpresaSigueCerrada:
    """El autor es un eje NUEVO: se compone con la empresa, no la reemplaza."""

    def setup_method(self) -> None:
        self.svc = OnboardingTemplatesService(_RepoDosEmpresas())

    def test_el_propio_se_lee(self) -> None:
        assert self.svc.get_template(PROPIO, EMPRESA_A).created_by == UUID(USUARIO)

    def test_el_ajeno_da_404_aunque_yo_sea_el_autor(self) -> None:
        """Ser el autor NO abre la puerta de otra empresa. Mismo 404 que 'no existe'."""
        with pytest.raises(AppError) as exc:
            self.svc.get_template(AJENO, EMPRESA_A)
        assert exc.value.code == "TEMPLATE_NOT_FOUND" and exc.value.status_code == 404

    def test_el_consolidado_no_restringe(self) -> None:
        """empresa_id=None = 'todas las empresas'. No es un fallo de validación."""
        assert self.svc.get_template(AJENO, None).id == AJENO
