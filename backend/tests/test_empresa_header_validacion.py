"""
Validación de existencia del header X-Empresa-Id + el caché por proceso que la sostiene.

El bug que se cierra: el middleware validaba solo el FORMATO del header, así que un UUID
sintácticamente correcto de una empresa inexistente entraba y quedaba en
`request.state.empresa_id`. Aguas abajo eso no daba acceso de más —apunta a menos que None,
que es la vista consolidada— pero sí llegaba a columnas con FK a `empresas`. La peor:
`auditoria.empresa_id`, donde el INSERT del evento fallaba, `AuditService` se tragaba la
excepción por diseño, y la operación de negocio se completaba **perdiendo el registro de
auditoría en silencio**. Eso es lo que cubre TestAuditoriaConHeaderFalso, y es el daño real
que cierra esta sesión — no las listas vacías.

El caché se prueba con un repo fake que CUENTA sus llamadas: el requisito no es solo "anda",
es "no dispara una query por request". Un caché que funcione pero consulte siempre pasaría
cualquier test de comportamiento y no serviría para nada.
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

from uuid import uuid4

import pytest

import utils.empresas_cache as cache_mod
from middleware._empresa_header import resolver_empresa_id as _resolver_empresa_id
from schemas.costo import PresupuestoCreate, PresupuestoResponse
from services.costo_service import CostoService
from utils.empresas_cache import _EmpresasCache

EXISTE = str(uuid4())
NO_EXISTE = str(uuid4())


class _RepoContador:
    """Repo fake que cuenta las queries. El punto del caché es que este contador NO suba."""

    def __init__(self, ids: list[str] | None = None) -> None:
        self.ids = ids if ids is not None else [EXISTE]
        self.llamadas = 0

    def find_all_ids(self) -> list[str]:
        self.llamadas += 1
        return list(self.ids)


class _RepoQueFalla:
    def __init__(self) -> None:
        self.llamadas = 0

    def find_all_ids(self) -> list[str]:
        self.llamadas += 1
        raise RuntimeError("base no disponible")


# ─── El caché ─────────────────────────────────────────────────────────────────


class TestCache:
    def test_construir_no_toca_la_base(self) -> None:
        """Carga perezosa, como el PyJWKClient: el cold start no paga la query."""
        repo = _RepoContador()
        _EmpresasCache(repo=repo)
        assert repo.llamadas == 0

    def test_primera_consulta_carga(self) -> None:
        repo = _RepoContador()
        assert _EmpresasCache(repo=repo).existe(EXISTE) is True
        assert repo.llamadas == 1

    def test_no_dispara_una_query_por_request(self) -> None:
        """El requisito central: 50 hits consecutivos = 1 sola query."""
        repo = _RepoContador()
        c = _EmpresasCache(repo=repo)
        for _ in range(50):
            assert c.existe(EXISTE) is True
        assert repo.llamadas == 1

    def test_id_inexistente_da_false(self) -> None:
        c = _EmpresasCache(repo=_RepoContador())
        assert c.existe(NO_EXISTE) is False

    def test_ttl_vencido_refresca(self) -> None:
        repo = _RepoContador()
        c = _EmpresasCache(repo=repo)
        c.existe(EXISTE)
        c._cargado_en -= cache_mod._TTL_SEGUNDOS + 1
        c._ultimo_intento = c._cargado_en
        c.existe(EXISTE)
        assert repo.llamadas == 2


class TestMissRefresh:
    def test_empresa_nueva_se_acepta_en_el_siguiente_request(self) -> None:
        """Sin esto quedaría invisible hasta 300s, con el usuario viendo el consolidado."""
        repo = _RepoContador()
        c = _EmpresasCache(repo=repo)
        assert c.existe(EXISTE) is True

        nueva = str(uuid4())
        repo.ids.append(nueva)                              # alguien la creó recién
        c._cargado_en -= cache_mod._GRACIA_MISS_SEGUNDOS + 1  # y pasó la gracia
        assert c.existe(nueva) is True
        assert repo.llamadas == 2

    def test_la_gracia_acota_los_refrescos(self) -> None:
        """N misses seguidos dentro de la gracia = 1 sola query. Acota el martilleo."""
        repo = _RepoContador()
        c = _EmpresasCache(repo=repo)
        c.existe(EXISTE)
        for _ in range(30):
            assert c.existe(NO_EXISTE) is False
        assert repo.llamadas == 1

    def test_miss_pasada_la_gracia_refresca_una_vez(self) -> None:
        repo = _RepoContador()
        c = _EmpresasCache(repo=repo)
        c.existe(EXISTE)
        c._cargado_en -= cache_mod._GRACIA_MISS_SEGUNDOS + 1
        assert c.existe(NO_EXISTE) is False   # refresca, sigue sin estar
        assert repo.llamadas == 2
        for _ in range(10):                   # y ya no vuelve a refrescar
            c.existe(NO_EXISTE)
        assert repo.llamadas == 2


class TestFailOpen:
    def test_si_no_carga_acepta_el_header(self) -> None:
        """Contraintuitivo pero correcto: descartar ENSANCHA (None = todas las empresas),
        así que ante un blip de base aceptar es la opción conservadora."""
        assert _EmpresasCache(repo=_RepoQueFalla()).existe(NO_EXISTE) is True

    def test_loguea_a_error(self, caplog) -> None:
        with caplog.at_level("ERROR"):
            _EmpresasCache(repo=_RepoQueFalla()).existe(NO_EXISTE)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_no_reintenta_por_request(self) -> None:
        """Con la base caída tampoco se dispara una query por request."""
        repo = _RepoQueFalla()
        c = _EmpresasCache(repo=repo)
        for _ in range(20):
            assert c.existe(NO_EXISTE) is True
        assert repo.llamadas == 1

    def test_set_viejo_sobrevive_a_un_fallo(self) -> None:
        """Si ya había datos y el refresco falla, se sigue usando lo último bueno."""
        repo = _RepoContador()
        c = _EmpresasCache(repo=repo)
        c.existe(EXISTE)
        c._repo = _RepoQueFalla()
        c._cargado_en -= cache_mod._TTL_SEGUNDOS + 1
        c._ultimo_intento = c._cargado_en
        assert c.existe(EXISTE) is True
        assert c.existe(NO_EXISTE) is False


# ─── El middleware ────────────────────────────────────────────────────────────


@pytest.fixture
def cache_sembrado(monkeypatch):
    """Reemplaza el singleton del proceso por uno con un set conocido."""
    c = _EmpresasCache(repo=_RepoContador([EXISTE]))
    monkeypatch.setattr(cache_mod, "_cache", c)
    return c


class TestResolverEmpresaId:
    def test_empresa_existente_pasa(self, cache_sembrado) -> None:
        assert _resolver_empresa_id(EXISTE, "/api/empleados") == EXISTE

    def test_empresa_inexistente_se_descarta(self, cache_sembrado) -> None:
        assert _resolver_empresa_id(NO_EXISTE, "/api/empleados") is None

    def test_inexistente_es_identico_a_no_mandar_header(self, cache_sembrado) -> None:
        """El requisito: mismo resultado que un request sin header. Sin status propio, sin
        oráculo de enumeración de empresas."""
        assert _resolver_empresa_id(NO_EXISTE, "/x") == _resolver_empresa_id("", "/x")

    def test_inexistente_loguea_warning(self, cache_sembrado, caplog) -> None:
        """Señal de manipulación: un UUID bien formado que no existe no sale del uso normal."""
        with caplog.at_level("WARNING"):
            _resolver_empresa_id(NO_EXISTE, "/api/empleados")
        assert any("X-Empresa-Id" in r.getMessage() for r in caplog.records)

    def test_existente_no_loguea_warning(self, cache_sembrado, caplog) -> None:
        with caplog.at_level("WARNING"):
            _resolver_empresa_id(EXISTE, "/api/empleados")
        assert not [r for r in caplog.records if "X-Empresa-Id" in r.getMessage()]

    @pytest.mark.parametrize("header", ["", "todas", "no-es-un-uuid", "12345", "  "])
    def test_casos_sin_cambio_de_comportamiento(self, cache_sembrado, header: str) -> None:
        """Malformado y "todas" siguen dando None, igual que antes."""
        assert _resolver_empresa_id(header.strip(), "/x") is None

    def test_malformado_no_consulta_el_cache(self, cache_sembrado) -> None:
        """Se descarta por formato antes de mirar el set: no cuesta una query."""
        _resolver_empresa_id("no-es-un-uuid", "/x")
        assert cache_sembrado._repo.llamadas == 0


# ─── El daño real: auditoría perdida ──────────────────────────────────────────


class TestAuditoriaConHeaderFalso:
    """Cierra el círculo: con un header falso el evento se registraba con un empresa_id que
    viola la FK de `auditoria.empresa_id`, el INSERT fallaba, AuditService se tragaba la
    excepción y el evento desaparecía.

    🔴 AHORA HAY DOS DEFENSAS, y esta clase pasó a cubrir la SEGUNDA. La primera es el middleware
    (un header inexistente se descarta → None), y la prueba `TestResolverEmpresaId`. La segunda,
    posterior: `set_presupuesto_area` ya NO etiqueta el evento con el header — usa la empresa del
    REGISTRO persistido, heredada del área (Vista vs Acción). O sea que el header **ya no llega**
    a `auditoria.empresa_id` por este camino, ni siquiera si esquivara al middleware.

    Por eso los tests de acá cambiaron de forma: antes afirmaban "el header falso llega como None
    y por eso no rompe la FK", que hoy pasaría **por el motivo equivocado** —el evento no lleva el
    header en absoluto—, o sea una aserción vacua. Ahora afirman la propiedad más fuerte que
    reemplazó a aquella: el evento lleva la empresa de la entidad, sea cual sea el header.
    """

    class _PresupuestoRepo:
        """El repo real hereda `empresa_id` del ÁREA (ver PresupuestoRepo.save_presupuesto), así
        que el response persistido SIEMPRE trae una empresa válida. Modelarlo es lo que permite
        distinguir "empresa del registro" de "empresa del header": con el response sin empresa,
        los dos orígenes darían None y ningún test de acá podría fallar."""

        def save_presupuesto(self, data) -> PresupuestoResponse:
            return PresupuestoResponse(id=str(uuid4()), area_id=data.area_id,
                                       area_nombre="Sistemas", empresa_id=EXISTE,
                                       mes=data.mes, anio=data.anio,
                                       presupuesto=data.presupuesto)

    class _AuditFK:
        """Modela la FK real: un empresa_id que no existe hace fallar el INSERT, y
        AuditService se traga el error → el evento se pierde."""

        def __init__(self, ids_validos: set[str]) -> None:
            self._validos = ids_validos
            self.guardados: list = []

        def registrar(self, **kw) -> None:
            eid = kw.get("empresa_id")
            if eid is not None and eid not in self._validos:
                return  # violación de FK, tragada por diseño
            self.guardados.append(kw)

    def _cargar(self, empresa_id):
        audit = self._AuditFK({EXISTE})
        svc = CostoService(presupuesto_repo=self._PresupuestoRepo(), audit=audit)
        svc.set_presupuesto_area(
            PresupuestoCreate(area_id=str(uuid4()), mes=6, anio=2026, presupuesto=1000.0),
            empresa_id, "u1",
        )
        return audit

    def test_el_evento_lleva_la_empresa_del_registro(self, cache_sembrado) -> None:
        """Con un header real y válido, el evento se guarda con la empresa de la entidad."""
        resuelto = _resolver_empresa_id(EXISTE, "/api/costos/presupuesto")
        guardados = self._cargar(resuelto).guardados
        assert len(guardados) == 1 and guardados[0]["empresa_id"] == EXISTE

    def test_un_header_inexistente_ya_no_puede_matar_el_evento(self) -> None:
        """🔴 Contrario de `test_sin_el_fix_el_evento_se_perdia`, que afirmaba que con el header
        crudo (sin pasar por el middleware) el evento se perdía por violar la FK.

        Ese test no se borró: se movió acá, invertido. Su premisa —que el header viaja hasta
        `auditoria.empresa_id`— dejó de ser cierta al pasar el etiquetado a la entidad. Se le pasa
        el UUID inexistente CRUDO, salteando el middleware a propósito: aun así el evento se
        guarda, y con la empresa del registro. Es la defensa en profundidad: aunque el primer
        anillo fallara, el header ya no llega a la columna con FK."""
        guardados = self._cargar(NO_EXISTE).guardados
        assert len(guardados) == 1, "el evento de auditoría se perdió"
        assert guardados[0]["empresa_id"] == EXISTE, "se coló el header en el evento"

    def test_el_fake_de_FK_sigue_siendo_letal(self) -> None:
        """Guarda contra el verde vacuo: si `_AuditFK` aceptara cualquier cosa, los dos tests de
        arriba pasarían con el bug puesto. Se lo invoca directo con un id inexistente —que es lo
        que el service ya no puede producir— para demostrar que el fake todavía descarta."""
        audit = self._AuditFK({EXISTE})
        audit.registrar(usuario_id="u1", entidad="presupuesto", registro_id=str(uuid4()),
                        accion="UPDATE", evento="set_presupuesto", empresa_id=NO_EXISTE)
        assert audit.guardados == []
