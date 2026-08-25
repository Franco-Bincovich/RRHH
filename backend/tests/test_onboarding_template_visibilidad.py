"""
Visibilidad pública/privada de las plantillas de onboarding (migración 082).

LA REGLA:  es_publica = true  OR  created_by = yo  OR  created_by IS NULL
…compuesta POR INTERSECCIÓN con la empresa, que se aplica primero. `gerencia_lectura` no se
filtra: ve todas, incluidas las privadas ajenas.

🚨 QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE CADA TEST PUEDA FALLAR.
El modo de falla obvio de este archivo es un fake que ACEPTE `user_id` y lo IGNORE: con ese
fake, "la privada ajena no se ve" da verde aunque nadie filtre nada — que es exactamente el
bug que la feature vino a cerrar. Es la misma familia que los fakes que aceptaban `empresa_id`
y lo ignoraban en la Fase 2.

Por eso hay DOS niveles, y hacen falta los dos:

  · `_RepoQueFiltra` (nivel service) HONRA empresa, autor y rol. Lo que puede detectar es que
    el SERVICE se olvide de pasar `user_id`/`rol` hacia abajo: si no los pasa, el fake recibe
    None, no filtra, y la privada ajena aparece → rojo. NO puede detectar que la regla esté
    mal escrita en SQL, porque la reimplementa en Python.
  · `TestElWhereLlevaLaVisibilidad` (nivel cliente de Supabase) mira el `.or_()` REAL que sale
    hacia la base. Es el único que verifica la regla en sí. Sin él, los dos lados podrían
    divergir y todo seguiría en verde.

`TestMutacionPorEje` cierra la pinza: comprueba que los dos ejes filtran conjuntos DISJUNTOS,
o sea que ninguno está tapando al otro. Si alguien borrara el filtro de empresa y los tests
siguieran verdes porque el de visibilidad casualmente cubre las mismas filas, ese test falla.
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

from repositories import onboarding_repo as onb_repo_mod
from repositories._onboarding_templates_filtros import ROL_VE_TODO, with_visibilidad
from schemas.onboarding import TareaCreate, TareaResponse, TareaUpdate, TemplateResponse, TemplateUpdate
from services._onboarding_iniciar import iniciar
from services.onboarding_templates_service import OnboardingTemplatesService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
YO, OTRO = str(uuid4()), str(uuid4())
TAREA = UUID("44444444-4444-4444-4444-444444444444")
INEXISTENTE = UUID("99999999-9999-9999-9999-999999999999")

# Catálogo de prueba. El nombre dice empresa · autor · visibilidad.
PUB_A_OTRO = UUID("11111111-1111-1111-1111-111111111111")
PRIV_A_OTRO = UUID("22222222-2222-2222-2222-222222222222")
PRIV_A_YO = UUID("33333333-3333-3333-3333-333333333333")
HUERFANA_A = UUID("44444444-4444-4444-4444-444444444444")
PUB_B_OTRO = UUID("55555555-5555-5555-5555-555555555555")
PRIV_B_YO = UUID("66666666-6666-6666-6666-666666666666")

_CATALOGO = [
    (PUB_A_OTRO, EMPRESA_A, OTRO, True),
    (PRIV_A_OTRO, EMPRESA_A, OTRO, False),
    (PRIV_A_YO, EMPRESA_A, YO, False),
    (HUERFANA_A, EMPRESA_A, None, False),   # sin autor: la FK es ON DELETE SET NULL
    (PUB_B_OTRO, EMPRESA_B, OTRO, True),
    (PRIV_B_YO, EMPRESA_B, YO, False),
]


def _tmpl(id_, empresa_id, created_by, es_publica) -> TemplateResponse:
    return TemplateResponse(id=id_, nombre="T", empresa_id=empresa_id,
                            created_by=created_by, es_publica=es_publica)


class _RepoQueFiltra:
    """HONRA los tres ejes: empresa, autor y rol. NO acepta un parámetro para ignorarlo.

    Reimplementa la regla en Python a propósito, para poder detectar que el service deje de
    pasar `user_id`/`rol`. Que la regla esté bien escrita EN SQL lo verifica
    TestElWhereLlevaLaVisibilidad, un escalón más abajo.
    """

    def __init__(self) -> None:
        self._t = {str(i): _tmpl(i, e, c, p) for i, e, c, p in _CATALOGO}
        self.escrituras: list = []

    def _visible(self, t: TemplateResponse, user_id, rol) -> bool:
        if rol == ROL_VE_TODO:
            return True
        return t.es_publica or t.created_by is None or str(t.created_by) == str(user_id)

    def get_templates(self, empresa_id=None, user_id=None, rol=None):
        return [t for t in self._t.values()
                if (not empresa_id or str(t.empresa_id) == str(empresa_id))
                and self._visible(t, user_id, rol)]

    def get_template(self, template_id, empresa_id=None, user_id=None, rol=None):
        t = self._t.get(str(template_id))
        if not t or (empresa_id and str(t.empresa_id) != str(empresa_id)):
            return None
        return t if self._visible(t, user_id, rol) else None

    def update_template(self, template_id, data, user_id=None, rol=None):
        self.escrituras.append(("update_template", str(template_id)))
        return self._t[str(template_id)]

    def delete_template(self, template_id):
        self.escrituras.append(("delete_template", str(template_id)))
        return True

    def add_tarea(self, template_id, data, empresa_id) -> TareaResponse:
        self.escrituras.append(("add_tarea", str(template_id)))
        return TareaResponse(id=TAREA, template_id=UUID(str(template_id)), titulo="X", semana=1, orden=1)

    def update_tarea(self, tarea_id, data) -> TareaResponse:
        self.escrituras.append(("update_tarea", str(tarea_id)))
        return TareaResponse(id=UUID(str(tarea_id)), template_id=PRIV_A_YO, titulo="X", semana=1, orden=1)

    def delete_tarea(self, tarea_id):
        """Devuelve LA FILA BORRADA, como el repo real — ver el fake hermano de
        `test_onboarding_templates_scope.py`."""
        self.escrituras.append(("delete_tarea", str(tarea_id)))
        return {"id": str(tarea_id), "template_id": str(PRIV_A_YO), "titulo": "X",
                "semana": 1, "orden": 1}


def _svc(repo=None):
    return OnboardingTemplatesService(repo=repo or _RepoQueFiltra())


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ─── el listado ───────────────────────────────────────────────────────────────


class TestElListado:
    def _ids(self, empresa=EMPRESA_A, user=YO, rol="admin_rrhh"):
        return {t.id for t in _svc().get_templates(empresa, user, rol)}

    def test_la_publica_ajena_se_ve(self) -> None:
        assert PUB_A_OTRO in self._ids()

    def test_la_privada_ajena_NO_se_ve(self) -> None:
        assert PRIV_A_OTRO not in self._ids()

    def test_la_privada_propia_se_ve(self) -> None:
        assert PRIV_A_YO in self._ids()

    def test_la_huerfana_se_ve(self) -> None:
        """created_by NULL + es_publica false ⇒ pública. Si no, borrar al autor la volvería
        invisible para todos, para siempre (la FK es ON DELETE SET NULL)."""
        assert HUERFANA_A in self._ids()

    def test_gerencia_lectura_ve_las_privadas_de_todos(self) -> None:
        """Decisión de producto: "privada" es privacidad entre pares de RRHH, no
        confidencialidad frente a la dirección. Ocultárselas sería la primera excepción
        row-level al modelo de roles."""
        assert PRIV_A_OTRO in self._ids(rol=ROL_VE_TODO)

    def test_el_consolidado_no_afloja_la_visibilidad(self) -> None:
        """empresa_id=None no restringe por empresa — pero la visibilidad sigue filtrando. Es
        donde más fácil se colaría una plantilla ajena."""
        ids = self._ids(empresa=None)
        assert PUB_B_OTRO in ids            # otra empresa, pública: entra
        assert PRIV_A_OTRO not in ids       # privada ajena: NO entra ni en consolidado


# ─── el detalle por id ────────────────────────────────────────────────────────


class TestElDetalle:
    def test_la_privada_ajena_da_404(self) -> None:
        err = _error(lambda: _svc().get_template(PRIV_A_OTRO, EMPRESA_A, YO))
        assert err.code == "TEMPLATE_NOT_FOUND" and err.status_code == 404

    def test_indistinguible_de_una_inexistente(self) -> None:
        """Mismo code, mismo mensaje y mismo status: un texto propio para "es privada"
        confirmaría que existe y de quién es."""
        privada = _error(lambda: _svc().get_template(PRIV_A_OTRO, EMPRESA_A, YO))
        inexistente = _error(lambda: _svc().get_template(INEXISTENTE, EMPRESA_A, YO))
        assert (privada.code, privada.message, privada.status_code) == \
               (inexistente.code, inexistente.message, inexistente.status_code)

    def test_la_privada_propia_se_lee(self) -> None:
        assert _svc().get_template(PRIV_A_YO, EMPRESA_A, YO).id == PRIV_A_YO

    def test_ser_el_autor_no_abre_la_puerta_de_otra_empresa(self) -> None:
        """PRIV_B_YO es MÍA, pero de la empresa B. Con la empresa A activa: mismo 404.
        La visibilidad se compone con la empresa, no la reemplaza."""
        err = _error(lambda: _svc().get_template(PRIV_B_YO, EMPRESA_A, YO))
        inexistente = _error(lambda: _svc().get_template(INEXISTENTE, EMPRESA_A, YO))
        assert (err.code, err.message, err.status_code) == \
               (inexistente.code, inexistente.message, inexistente.status_code)


# ─── las CINCO escrituras ─────────────────────────────────────────────────────


def _upd_tmpl(svc, tid):
    return svc.update_template(tid, TemplateUpdate(nombre="N"), EMPRESA_A, YO)


def _del_tmpl(svc, tid):
    return svc.delete_template(tid, EMPRESA_A, YO)


def _add_tarea(svc, tid):
    return svc.add_tarea(tid, TareaCreate(titulo="Z", semana=1, orden=1), EMPRESA_A, YO)


def _upd_tarea(svc, tid):
    return svc.update_tarea(tid, TAREA, TareaUpdate(titulo="Y"), EMPRESA_A, YO)


def _del_tarea(svc, tid):
    return svc.delete_tarea(tid, TAREA, EMPRESA_A, YO)


_OPS = [_upd_tmpl, _del_tmpl, _add_tarea, _upd_tarea, _del_tarea]
_IDS = ["update_template", "delete_template", "add_tarea", "update_tarea", "delete_tarea"]


@pytest.mark.parametrize("llamar", _OPS, ids=_IDS)
class TestLasEscrituras:
    """add_tarea entra en el barrido: era el único que llamaba al repo directo."""

    def test_sobre_la_privada_ajena_da_404(self, llamar) -> None:
        err = _error(lambda: llamar(_svc(), PRIV_A_OTRO))
        assert err.code == "TEMPLATE_NOT_FOUND" and err.status_code == 404

    def test_no_toca_el_repo_con_la_privada_ajena(self, llamar) -> None:
        """El gate corta ANTES de escribir: no alcanza con que devuelva 404 después."""
        repo = _RepoQueFiltra()
        _error(lambda: llamar(_svc(repo), PRIV_A_OTRO))
        assert repo.escrituras == []

    def test_sobre_la_privada_propia_funciona(self, llamar) -> None:
        assert llamar(_svc(), PRIV_A_YO) is not None


# ─── cambiar la visibilidad: solo el autor ────────────────────────────────────


class TestSoloElAutorCambiaLaVisibilidad:
    """El gate de acceso NO alcanza para esto: una plantilla PÚBLICA de otro es alcanzable
    para todos, así que sin una guarda propia cualquiera podía volverla privada — y como
    `created_by` sigue siendo del autor, quien lo hacía perdía el acceso en el acto."""

    def _cambiar(self, tid, es_publica=False, user=YO):
        return _svc().update_template(tid, TemplateUpdate(es_publica=es_publica), EMPRESA_A, user)

    def test_no_puedo_volver_privada_la_publica_de_otro(self) -> None:
        err = _error(lambda: self._cambiar(PUB_A_OTRO))
        assert err.code == "TEMPLATE_NO_SOS_AUTOR" and err.status_code == 403

    def test_no_toca_el_repo(self) -> None:
        repo = _RepoQueFiltra()
        _error(lambda: _svc(repo).update_template(
            PUB_A_OTRO, TemplateUpdate(es_publica=False), EMPRESA_A, YO))
        assert repo.escrituras == []

    def test_es_403_y_no_404_porque_no_hay_nada_que_ocultar(self) -> None:
        """El 404 uniforme protege contra ENUMERACIÓN. Acá la plantilla ya te era visible: un
        código propio no confirma ninguna existencia que no supieras."""
        assert _error(lambda: self._cambiar(PUB_A_OTRO)).status_code == 403

    def test_sobre_la_propia_si_puedo(self) -> None:
        assert self._cambiar(PRIV_A_YO, es_publica=True) is not None

    def test_la_huerfana_la_puede_cambiar_cualquiera(self) -> None:
        """Contracara de la regla de huérfanas: se comporta como pública y no hay a quién
        preguntarle."""
        assert self._cambiar(HUERFANA_A, es_publica=True) is not None

    def test_editar_el_nombre_de_la_publica_ajena_sigue_permitido(self) -> None:
        """La guarda es SOLO para la visibilidad: el resto de la edición es colaborativa."""
        assert _svc().update_template(PUB_A_OTRO, TemplateUpdate(nombre="N"), EMPRESA_A, YO) is not None


# ─── el flujo de inicio de onboarding ─────────────────────────────────────────


class _EmpleadoRepo:
    def find_by_id(self, empleado_id, empresa_id=None):
        return SimpleNamespace(id=empleado_id, empresa_id=str(EMPRESA_A))


class _OnbRepo:
    """`get_default_template` HONRA la visibilidad, como el real."""

    def __init__(self, default=None) -> None:
        self._default = default
        self.creadas: list = []

    def find_instancia_by_empleado(self, empleado_id, empresa_id=None):
        return None

    def get_default_template(self, empresa_id=None, user_id=None, rol=None):
        t = self._default
        if t is None:
            return None
        if rol != ROL_VE_TODO and not (t.es_publica or t.created_by is None
                                       or str(t.created_by) == str(user_id)):
            return None
        return t

    def create_instancia(self, empleado_id, template_id, empresa_id):
        self.creadas.append(str(template_id))
        return SimpleNamespace(id=uuid4())


def _iniciar(template_id=None, default=None, user=YO, rol="admin_rrhh"):
    return iniciar(_OnbRepo(default), _RepoQueFiltra(), _EmpleadoRepo(),
                   uuid4(), template_id, EMPRESA_A, user, rol)


class TestIniciarOnboarding:
    def test_con_una_privada_ajena_da_404_y_NO_422(self) -> None:
        """🔴 Antes el lookup no acotaba por empresa y el desajuste salía por EMPRESA_MISMATCH
        (422): un status distinto al 404 del id inexistente confirmaba que la plantilla existe.
        Ese oráculo ya no existe."""
        err = _error(lambda: _iniciar(template_id=PRIV_A_OTRO))
        assert err.status_code == 404 and err.code == "TEMPLATE_NOT_FOUND"

    def test_una_de_otra_empresa_tambien_da_404(self) -> None:
        """La plantilla se resuelve contra la empresa del EMPLEADO."""
        assert _error(lambda: _iniciar(template_id=PUB_B_OTRO)).status_code == 404

    def test_con_la_propia_privada_arranca(self) -> None:
        assert _iniciar(template_id=PRIV_A_YO) is not None

    def test_el_default_no_puede_ser_una_privada_ajena(self) -> None:
        """🔴 El agujero semántico: sin este filtro, una plantilla marcada privada seguía
        siendo la que el sistema elige para onboardear a todo el equipo."""
        privada = _tmpl(PRIV_A_OTRO, EMPRESA_A, OTRO, False)
        assert _error(lambda: _iniciar(default=privada)).status_code == 404

    def test_el_default_publico_si_se_usa(self) -> None:
        publica = _tmpl(PUB_A_OTRO, EMPRESA_A, OTRO, True)
        assert _iniciar(default=publica) is not None


# ─── la regla, en el WHERE real ───────────────────────────────────────────────


class _QueryFake:
    def __init__(self, registro: dict) -> None:
        self._r = registro

    def or_(self, expr):
        self._r["or_"] = expr
        return self

    def eq(self, col, val):
        self._r.setdefault("eq", []).append((col, val))
        return self

    def select(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return SimpleNamespace(data=None, count=0)


class TestElWhereLlevaLaVisibilidad:
    """El único nivel que verifica la REGLA en sí: lo que sale hacia PostgREST."""

    def _expr(self, user_id, rol=None):
        reg: dict = {}
        with_visibilidad(_QueryFake(reg), user_id, rol)
        return reg.get("or_")

    def test_las_tres_ramas_estan(self) -> None:
        expr = self._expr(YO)
        assert "es_publica.eq.true" in expr
        assert "created_by.is.null" in expr
        assert f"created_by.eq.{YO}" in expr

    def test_gerencia_lectura_no_agrega_filtro(self) -> None:
        assert self._expr(YO, ROL_VE_TODO) is None

    def test_sin_user_id_no_filtra(self) -> None:
        """Es la relectura posterior a una escritura ya gateada, no un modo de acceso."""
        assert self._expr(None) is None

    def test_el_default_de_onboarding_usa_la_misma_regla(self, monkeypatch) -> None:
        """get_default_template no pasa por el repo de templates: si no reusara
        with_visibilidad, la regla tendría dos copias."""
        reg: dict = {}
        monkeypatch.setattr(onb_repo_mod, "supabase_admin",
                            SimpleNamespace(table=lambda _t: _QueryFake(reg)))
        onb_repo_mod.OnboardingRepo().get_default_template(EMPRESA_A, YO, "admin_rrhh")
        assert f"created_by.eq.{YO}" in reg["or_"]
        assert ("empresa_id", str(EMPRESA_A)) in reg["eq"]      # empresa TAMBIÉN, no en vez de


# ─── los dos ejes son independientes ──────────────────────────────────────────


class TestMutacionPorEje:
    """Cada eje filtra un conjunto DISTINTO. Si se solaparan, borrar uno pasaría inadvertido."""

    def _ids(self, empresa, user, rol="admin_rrhh"):
        return {t.id for t in _svc().get_templates(empresa, user, rol)}

    def test_los_conjuntos_que_caen_son_disjuntos(self) -> None:
        base = self._ids(EMPRESA_A, YO)
        sin_empresa = self._ids(None, YO)          # se afloja SOLO el eje de empresa
        sin_visibilidad = self._ids(EMPRESA_A, YO, ROL_VE_TODO)  # SOLO el de visibilidad

        gana_empresa = sin_empresa - base
        gana_visibilidad = sin_visibilidad - base

        assert gana_empresa and gana_visibilidad, "algún eje no está filtrando nada"
        assert not (gana_empresa & gana_visibilidad), (
            "los dos ejes tapan las mismas filas: borrar uno podría no romper ningún test"
        )

    def test_el_eje_de_empresa_deja_entrar_solo_otras_empresas(self) -> None:
        gana = self._ids(None, YO) - self._ids(EMPRESA_A, YO)
        assert gana == {PUB_B_OTRO, PRIV_B_YO}

    def test_el_eje_de_visibilidad_deja_entrar_solo_privadas_ajenas(self) -> None:
        gana = self._ids(EMPRESA_A, YO, ROL_VE_TODO) - self._ids(EMPRESA_A, YO)
        assert gana == {PRIV_A_OTRO}
