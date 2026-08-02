"""
Tipos de ausencia editables desde /configuracion (migración 085).

🔴 LA REGLA QUE ESTOS TESTS PROTEGEN: NO HAY BAJA FÍSICA. `solicitudes_ausencia.tipo_id` es
una FK sin ON DELETE; borrar un tipo en uso falla, y si no fallara se llevaría el historial.
La baja es `activo=False`: saca el tipo de los selects y deja las ausencias viejas intactas,
mostrando todavía su nombre.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El fake guarda tipos de TRES alcances —global, empresa A y empresa B— y `find_by_id` devuelve
la fila con su `empresa_id` real, que es lo que el service necesita para decidir el 404. Un
fake que devolviera siempre un tipo sin dueño dejaría pasar el test de la barrera sin barrera.
`update` MUTA el dict guardado y devuelve el resultado de esa mutación: no un objeto
prefabricado, así que si el service mandara los cambios equivocados el test lo ve.
"""
import os

# Patch env antes de importar el proyecto (config.settings lee os.environ al instanciar).
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

import inspect
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest

from schemas.ausencias import TipoAusenciaCreate, TipoAusenciaResponse
from schemas.configuracion import TipoAusenciaUpdate
from services.tipos_ausencia_service import TiposAusenciaService
from utils.errors import AppError

EMPRESA_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EMPRESA_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

GLOBAL_BASE = "11111111-1111-1111-1111-111111111111"   # es_base, sin empresa
PROPIO_A = "22222222-2222-2222-2222-222222222222"      # de la empresa A
PROPIO_B = "33333333-3333-3333-3333-333333333333"      # de la empresa B


def _tipo(id_: str, nombre: str, empresa_id: Optional[str], es_base: bool = False,
          activo: bool = True, cuenta: bool = True) -> Dict[str, Any]:
    return {"id": id_, "nombre": nombre, "es_base": es_base, "activo": activo,
            "empresa_id": empresa_id, "cuenta_ausentismo": cuenta}


class _FakeRepo:
    def __init__(self) -> None:
        self.filas: Dict[str, Dict[str, Any]] = {
            GLOBAL_BASE: _tipo(GLOBAL_BASE, "Enfermedad", None, es_base=True),
            PROPIO_A: _tipo(PROPIO_A, "Franco especial", str(EMPRESA_A)),
            PROPIO_B: _tipo(PROPIO_B, "Solo de B", str(EMPRESA_B)),
        }

    def find_all(self, empresa_id=None, incluir_inactivos=False) -> List[TipoAusenciaResponse]:
        # Reproduce el WHERE real: globales + los de esta empresa, y los inactivos solo si se piden.
        vis = [f for f in self.filas.values()
               if f["empresa_id"] is None or f["empresa_id"] == empresa_id]
        if not incluir_inactivos:
            vis = [f for f in vis if f["activo"]]
        return [TipoAusenciaResponse.model_validate(f) for f in sorted(vis, key=lambda f: f["nombre"])]

    def find_by_id(self, tipo_id):
        return self.filas.get(tipo_id)

    def create(self, nombre, empresa_id=None):
        nuevo = _tipo(f"nuevo-{nombre}", nombre, empresa_id)
        self.filas[nuevo["id"]] = nuevo
        return TipoAusenciaResponse.model_validate(nuevo)

    def update(self, tipo_id, cambios):
        self.filas[tipo_id].update(cambios)
        return TipoAusenciaResponse.model_validate(self.filas[tipo_id])


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.fixture
def svc(repo: _FakeRepo) -> TiposAusenciaService:
    return TiposAusenciaService(repo)


class TestBajaLogica:
    def test_desactivar_lo_saca_de_los_selects(self, svc: TiposAusenciaService) -> None:
        svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(activo=False), EMPRESA_A)
        nombres = [t.nombre for t in svc.get_tipos(EMPRESA_A).items]
        assert "Franco especial" not in nombres

    def test_pero_sigue_visible_en_configuracion_para_poder_reactivarlo(
        self, svc: TiposAusenciaService,
    ) -> None:
        svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(activo=False), EMPRESA_A)
        tipos = svc.get_tipos(EMPRESA_A, incluir_inactivos=True).items
        inactivo = next(t for t in tipos if t.nombre == "Franco especial")
        assert inactivo.activo is False

    def test_se_puede_reactivar(self, svc: TiposAusenciaService) -> None:
        svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(activo=False), EMPRESA_A)
        svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(activo=True), EMPRESA_A)
        assert "Franco especial" in [t.nombre for t in svc.get_tipos(EMPRESA_A).items]

    def test_desactivar_NO_borra_la_fila(self, svc: TiposAusenciaService, repo: _FakeRepo) -> None:
        # Es lo que mantiene viva la FK de las ausencias históricas.
        svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(activo=False), EMPRESA_A)
        assert PROPIO_A in repo.filas

    def test_el_repo_no_expone_ninguna_baja_fisica(self) -> None:
        # Guarda estructural: el día que alguien agregue un delete "por completitud", rojea.
        from repositories.tipos_ausencia_repo import TiposAusenciaRepo
        metodos = [m for m, _ in inspect.getmembers(TiposAusenciaRepo, inspect.isfunction)]
        assert not [m for m in metodos if "delete" in m or "remove" in m or "borrar" in m]

    def test_el_router_no_expone_DELETE(self) -> None:
        from fastapi.routing import APIRoute

        from main import app
        rutas = [r for r in app.routes
                 if isinstance(r, APIRoute) and r.path.endswith("/ausencias/tipos/{tipo_id}")]
        assert rutas, "guarda de mínimo: la ruta de edición tiene que existir"
        assert not [r for r in rutas if "DELETE" in r.methods]

    def test_las_ausencias_historicas_resuelven_el_nombre_sin_mirar_activo(self) -> None:
        """El listado de ausencias arma el tipo_map por id, NO filtrando por activo.

        Si filtrara, dar de baja un tipo dejaría en blanco la columna "Tipo" de todas las
        ausencias viejas que lo usan — que es justo el daño que la baja lógica evita.
        """
        import repositories.ausencias_repo as mod
        fuente = inspect.getsource(mod._build)
        assert 'tipo_map' in fuente
        assert '.eq("activo"' not in fuente and "'activo'" not in fuente


class TestTiposBase:
    def test_un_tipo_base_no_se_puede_desactivar(self, svc: TiposAusenciaService) -> None:
        with pytest.raises(AppError) as e:
            svc.update_tipo(UUID(GLOBAL_BASE), TipoAusenciaUpdate(activo=False), EMPRESA_A)
        assert e.value.code == "TIPO_BASE_NO_DESACTIVABLE" and e.value.status_code == 422

    def test_pero_si_se_le_puede_cambiar_si_cuenta_como_ausentismo(
        self, svc: TiposAusenciaService,
    ) -> None:
        # El bloqueo es solo sobre la BAJA: la política de ausentismo sigue siendo editable.
        r = svc.update_tipo(UUID(GLOBAL_BASE), TipoAusenciaUpdate(cuenta_ausentismo=False), EMPRESA_A)
        assert r.cuenta_ausentismo is False and r.activo is True

    def test_y_renombrarlo(self, svc: TiposAusenciaService) -> None:
        r = svc.update_tipo(UUID(GLOBAL_BASE), TipoAusenciaUpdate(nombre="Enfermedad común"), EMPRESA_A)
        assert r.nombre == "Enfermedad común"


class TestBarreraDeEmpresa:
    def test_un_tipo_de_otra_empresa_da_404(self, svc: TiposAusenciaService) -> None:
        with pytest.raises(AppError) as e:
            svc.update_tipo(UUID(PROPIO_B), TipoAusenciaUpdate(nombre="mío ahora"), EMPRESA_A)
        assert e.value.status_code == 404 and e.value.code == "TIPO_NOT_FOUND"

    def test_un_tipo_inexistente_da_EXACTAMENTE_el_mismo_error(
        self, svc: TiposAusenciaService,
    ) -> None:
        # Mismo status, mismo code y mismo mensaje: un 403 o un texto distinto confirmaría
        # que el tipo existe y es de otro, que es el oráculo de enumeración que la Fase 2 cerró.
        with pytest.raises(AppError) as ajeno:
            svc.update_tipo(UUID(PROPIO_B), TipoAusenciaUpdate(nombre="x"), EMPRESA_A)
        with pytest.raises(AppError) as inexistente:
            svc.update_tipo(UUID("99999999-9999-9999-9999-999999999999"),
                            TipoAusenciaUpdate(nombre="x"), EMPRESA_A)
        assert (ajeno.value.status_code, ajeno.value.code, ajeno.value.message) == \
               (inexistente.value.status_code, inexistente.value.code, inexistente.value.message)

    def test_el_tipo_de_B_no_se_le_lista_a_A(self, svc: TiposAusenciaService) -> None:
        assert "Solo de B" not in [t.nombre for t in svc.get_tipos(EMPRESA_A).items]

    def test_los_globales_se_le_listan_a_las_dos(self, svc: TiposAusenciaService) -> None:
        for empresa in (EMPRESA_A, EMPRESA_B):
            assert "Enfermedad" in [t.nombre for t in svc.get_tipos(empresa).items]

    def test_un_tipo_global_si_se_puede_editar_desde_cualquier_empresa(
        self, svc: TiposAusenciaService,
    ) -> None:
        # Decisión: los globales son de todas. Hoy hay un solo equipo de RRHH operándolas.
        r = svc.update_tipo(UUID(GLOBAL_BASE), TipoAusenciaUpdate(cuenta_ausentismo=False), EMPRESA_B)
        assert r.cuenta_ausentismo is False


class TestCreacion:
    def test_el_tipo_nuevo_nace_en_la_empresa_activa(self, svc: TiposAusenciaService) -> None:
        r = svc.create_tipo(TipoAusenciaCreate(nombre="Mudanza"), EMPRESA_A)
        assert r.empresa_id == str(EMPRESA_A)

    def test_y_nace_contando_como_ausentismo(self, svc: TiposAusenciaService) -> None:
        # DEFAULT TRUE = comportamiento idéntico al previo a 085.
        assert svc.create_tipo(TipoAusenciaCreate(nombre="Mudanza"), EMPRESA_A).cuenta_ausentismo

    def test_nombre_en_blanco_se_rechaza(self, svc: TiposAusenciaService) -> None:
        with pytest.raises(AppError) as e:
            svc.create_tipo(TipoAusenciaCreate(nombre="   "), EMPRESA_A)
        assert e.value.code == "TIPO_NOMBRE_VACIO"

    def test_renombrar_a_blanco_tambien(self, svc: TiposAusenciaService) -> None:
        with pytest.raises(AppError) as e:
            svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(nombre="  "), EMPRESA_A)
        assert e.value.code == "TIPO_NOMBRE_VACIO"

    def test_un_patch_vacio_no_rompe_ni_cambia_nada(self, svc: TiposAusenciaService) -> None:
        r = svc.update_tipo(UUID(PROPIO_A), TipoAusenciaUpdate(), EMPRESA_A)
        assert r.nombre == "Franco especial" and r.activo is True


class TestElWhereDelRepoLlevaLaEmpresa:
    """El fake fija el contrato pero no toca la query real: acá se faltea el cliente de
    Supabase para verificar que "globales + los míos" viaje EN LA QUERY.

    Traer todos los tipos de todas las empresas y descartar en Python expondría los ajenos a
    cualquiera que mire la respuesta cruda."""

    def _repo_con_espia(self, monkeypatch):
        import repositories.tipos_ausencia_repo as mod

        llamadas: list = []

        class _Q:
            def select(self, *a, **k): return self
            def order(self, *a, **k): return self
            def maybe_single(self): return self
            def eq(self, col, val):
                llamadas.append(("eq", col, val)); return self
            def is_(self, col, val):
                llamadas.append(("is", col, val)); return self
            def or_(self, expr):
                llamadas.append(("or", expr)); return self
            def execute(self): return SimpleNamespace(data=[])

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.TiposAusenciaRepo(), llamadas

    def test_pide_los_globales_mas_los_de_la_empresa(self, monkeypatch) -> None:
        repo, llamadas = self._repo_con_espia(monkeypatch)
        repo.find_all(str(EMPRESA_A))
        assert ("or", f"empresa_id.is.null,empresa_id.eq.{EMPRESA_A}") in llamadas

    def test_por_defecto_filtra_los_inactivos_en_la_query(self, monkeypatch) -> None:
        repo, llamadas = self._repo_con_espia(monkeypatch)
        repo.find_all(str(EMPRESA_A))
        assert ("eq", "activo", True) in llamadas

    def test_con_incluir_inactivos_no_filtra_por_activo(self, monkeypatch) -> None:
        repo, llamadas = self._repo_con_espia(monkeypatch)
        repo.find_all(str(EMPRESA_A), incluir_inactivos=True)
        assert not [c for c in llamadas if c[:2] == ("eq", "activo")]

    def test_sin_empresa_solo_trae_los_globales(self, monkeypatch) -> None:
        repo, llamadas = self._repo_con_espia(monkeypatch)
        repo.find_all(None)
        assert ("is", "empresa_id", "null") in llamadas
