"""
Tests de instrumentación de audit (T18.4c): empleados · costos · empresa · candidatos.

Repos fake + AuditService fake inyectados por constructor (sin DB). Foco: tras la
mutación exitosa el service llama a audit.registrar una vez con el evento/accion/entidad
correctos; empleado.update/deactivate LEEN el estado anterior (read-before); empresa
audita solo el toggle dedicado.

🔴 EJE TRANSVERSAL — DE DÓNDE SALE `empresa_id` DEL EVENTO. Auditar es una ACCIÓN, así que la
empresa sale de la ENTIDAD afectada, nunca del header `X-Empresa-Id` (que es VISTA: el selector
del sidebar). `TestCostoAudit` y `TestCandidatoAudit` lo fijan para las tres escrituras que
tenían el patrón. La condición para que esos tests puedan fallar es siempre la misma y está
escrita en cada docstring: la entidad tiene que traer una empresa DISTINTA de la del header —
con las dos en None, leer una u otra da el mismo resultado y el test no prueba nada.
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

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from schemas.costo import NominaResponse, PresupuestoResponse
from schemas.empleado import EmpleadoResponse, EmpleadoUpdate
from schemas.empresa import EmpresaResponse
from schemas.candidato import CandidatoResponse
from services.candidato_service import CandidatoService
from services.costo_service import CostoService
from services.empleado_service import EmpleadoService
from services.empresa_service import EmpresaService


# Empresas de las ENTIDADES, distintas de lo que se pasa como header en cada llamada. Que sean
# distintas es lo que hace que los tests de "empresa del registro" puedan fallar: con las dos
# iguales (o las dos None) el test pasaría leyendo cualquiera de los dos orígenes.
_EMPRESA_DEL_AREA = "e-area-7"
_EMPRESA_DEL_CANDIDATO = "e-cand-9"


class _FakeAudit:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def registrar(self, **kwargs) -> None:
        self.calls.append(kwargs)


def _empleado(**over) -> EmpleadoResponse:
    base = dict(
        id="emp1", nombre="Ana", apellido="Lopez", email_corporativo="a@x.com",
        empresa_id="e1", area_id="ar1", roles=["Dev"], cargo="Dev", modalidad_trabajo="remoto",
        tipo_contrato="indefinido", fecha_ingreso=date(2025, 1, 1), estado="activo",
        created_at=datetime(2026, 1, 1, 9, 0),
    )
    base.update(over)
    return EmpleadoResponse(**base)


class _FakeEmpRepo:
    def __init__(self) -> None:
        self.prior = _empleado(cargo="Dev")
        self.updated = _empleado(cargo="Lead")
        self.find_by_id_calls = 0

    def find_by_legajo(self, *a, **k):
        return None

    def find_by_id(self, _id, _empresa=None):
        self.find_by_id_calls += 1
        return self.prior

    def save(self, _data, _empresa):
        return self.prior

    def update(self, _id, _data, _empresa=None):
        return self.updated

    def soft_delete(self, _id, _empresa=None):
        return True


class _AreaRepoPermisivo:
    """area_repo fake permisivo: este test es de AUDITORÍA, no del gate de área (ese vive en
    test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


class TestEmpleadoAudit:
    def test_create_registra_alta(self) -> None:
        audit = _FakeAudit()
        svc = EmpleadoService(repo=_FakeEmpRepo(), audit=audit, area_repo=_AreaRepoPermisivo())
        from schemas.empleado import EmpleadoCreate
        svc.create_empleado(
            EmpleadoCreate(nombre="Ana", apellido="Lopez", email_corporativo="a@x.com",
                           area_id=uuid4(), roles=["Dev"], modalidad_trabajo="remoto",
                           tipo_contrato="indefinido", fecha_ingreso=date(2025, 1, 1),
                           empresa_id=uuid4()),
            created_by="u1", empresa_id=uuid4(),
        )
        assert len(audit.calls) == 1
        c = audit.calls[0]
        assert (c["evento"], c["accion"], c["entidad"]) == ("alta_empleado", "INSERT", "empleado")
        assert c["usuario_id"] == "u1"

    def test_update_lee_prior_y_diff(self) -> None:
        audit = _FakeAudit()
        repo = _FakeEmpRepo()
        svc = EmpleadoService(repo=repo, audit=audit)
        svc.update_empleado(uuid4(), EmpleadoUpdate(cargo="Lead"), empresa_id=None, usuario_id="u1")
        assert repo.find_by_id_calls == 1  # read-before ejecutado
        c = audit.calls[0]
        assert c["evento"] == "update_empleado" and c["accion"] == "UPDATE"
        # diff: cargo Dev→Lead capturado
        assert c["datos_anteriores"]["cargo"] == "Dev"
        assert c["datos_nuevos"]["cargo"] == "Lead"

    # `test_deactivate_lee_prior_y_registra_baja` se BORRÓ el 17/8/2026 junto con
    # `deactivate_empleado` y el evento `baja_empleado` que afirmaba. La baja de un empleado ya no
    # pasa por `EmpleadoService`: la escribe `_offboarding_efectivizar`, con el evento
    # `efectivizacion_baja` y siempre con `fecha_egreso`. Su auditoría se prueba en
    # `tests/test_offboarding_baja_efectiva.py`.


class TestCostoAudit:
    def test_cargar_nomina_usa_empresa_del_registro(self) -> None:
        audit = _FakeAudit()
        nomina = NominaResponse(id="n1", empleado_id="emp1", empresa_id="e9",
                                empleado_nombre="Ana", area_nombre="Dev", mes=6, anio=2026,
                                monto_bruto=100.0, monto_neto=80.0, total=100.0)

        class _Repo:
            def save_nomina(self, _d):
                return nomina

        from schemas.costo import NominaCreate
        svc = CostoService(nomina_repo=_Repo(), audit=audit)
        # `empleado_id` va con un UUID real: el schema lo tipa `UUID` desde la sesión 0.6 y un
        # "emp1" ni siquiera construye el modelo. La `NominaResponse` de arriba sigue con ids
        # cortos a propósito — ahí el campo es `str` y este test mira `empresa_id`, no el formato.
        svc.cargar_nomina(NominaCreate(empleado_id=str(uuid4()), mes=6, anio=2026,
                                       monto_bruto=100.0, monto_neto=80.0),
                          empresa_id=None, usuario_id="u1")
        c = audit.calls[0]
        assert c["evento"] == "carga_nomina" and c["entidad"] == "nomina"
        assert c["empresa_id"] == "e9"  # del registro, no del header (None)

    def test_set_presupuesto_usa_empresa_del_registro(self) -> None:
        """El evento se etiqueta con la empresa DEL PRESUPUESTO (heredada del área), no con la
        del header. Reemplaza a `test_set_presupuesto_usa_empresa_del_header`, que afirmaba lo
        contrario: ese test existía para garantizar el comportamiento incorrecto (Vista vs
        Acción — el selector del sidebar no gobierna una escritura).

        ¿Qué tendría que ser distinto en el fake para que este test falle? Que
        `save_presupuesto` devolviera un response SIN `empresa_id` (como antes, cuando el schema
        no declaraba el campo): ahí "usar el registro" y "usar el header" darían los DOS None y
        la aserción no podría distinguirlos. Por eso el fake devuelve `_EMPRESA_DEL_AREA` y la
        llamada pasa `empresa_id=None`: los dos orígenes dan resultados distintos, así que el
        test falla si el código vuelve a leer el header."""
        audit = _FakeAudit()

        class _Repo:
            """Construye la respuesta A PARTIR de lo que recibe (no un objeto prefabricado), salvo
            `empresa_id`, que el repo real resuelve del ÁREA y no del input — igual que en prod."""

            def save_presupuesto(self, d):
                return PresupuestoResponse(id="p1", area_id=d.area_id, area_nombre="Dev",
                                           empresa_id=_EMPRESA_DEL_AREA, mes=d.mes, anio=d.anio,
                                           presupuesto=d.presupuesto)

        from schemas.costo import PresupuestoCreate
        svc = CostoService(presupuesto_repo=_Repo(), audit=audit)
        svc.set_presupuesto_area(PresupuestoCreate(area_id="ar1", mes=6, anio=2026, presupuesto=500.0),
                                 empresa_id=None, usuario_id="u1")
        c = audit.calls[0]
        assert c["evento"] == "set_presupuesto"
        assert c["empresa_id"] == _EMPRESA_DEL_AREA  # del registro, no del header (None)

    def test_set_presupuesto_ignora_un_header_que_contradice_al_registro(self) -> None:
        """La contracara: con un header REAL y distinto del de la entidad, gana la entidad.

        Sin este test, "usa el registro" podría implementarse como "usa el header cuando no es
        None", que pasaría el test de arriba (header None) y seguiría mal etiquetando en el modo
        que de verdad importa: el de empresa seleccionada."""
        audit = _FakeAudit()

        class _Repo:
            def save_presupuesto(self, d):
                return PresupuestoResponse(id="p1", area_id=d.area_id, area_nombre="Dev",
                                           empresa_id=_EMPRESA_DEL_AREA, mes=d.mes, anio=d.anio,
                                           presupuesto=d.presupuesto)

        from schemas.costo import PresupuestoCreate
        svc = CostoService(presupuesto_repo=_Repo(), audit=audit)
        svc.set_presupuesto_area(PresupuestoCreate(area_id="ar1", mes=6, anio=2026, presupuesto=500.0),
                                 empresa_id="empresa-del-header", usuario_id="u1")
        assert audit.calls[0]["empresa_id"] == _EMPRESA_DEL_AREA


class TestEmpresaAudit:
    def _empresa(self, activa: bool) -> EmpresaResponse:
        return EmpresaResponse(id="e1", nombre="Karstec", activa=activa,
                               created_at=datetime(2026, 1, 1, 9, 0))

    def test_toggle_registra_evento(self) -> None:
        audit = _FakeAudit()
        emp = self._empresa(activa=False)

        class _Repo:
            def update(self, _id, _data):
                return emp

        svc = EmpresaService(repo=_Repo(), audit=audit)
        svc.toggle_activa("e1", False, usuario_id="u1")
        c = audit.calls[0]
        assert c["evento"] == "toggle_empresa_activa" and c["accion"] == "UPDATE"
        assert c["registro_id"] == "e1" and c["empresa_id"] == "e1"
        assert c["datos_nuevos"] == {"activa": False}

    def test_update_generico_no_audita(self) -> None:
        # El PUT genérico (update_empresa) NO debe auditar — solo el toggle.
        audit = _FakeAudit()
        emp = self._empresa(activa=True)

        class _Repo:
            def update(self, _id, _data):
                return emp

        from schemas.empresa import EmpresaUpdate
        svc = EmpresaService(repo=_Repo(), audit=audit)
        svc.update_empresa("e1", EmpresaUpdate(nombre="Nuevo"))
        assert audit.calls == []  # ningún evento de audit


class TestCandidatoAudit:
    """`baja_candidato` etiquetado con la empresa del CANDIDATO, no con la del header.

    Es la instancia hermana de `set_presupuesto` (misma clase de bug, otro módulo), y la única
    de las dos que YA produjo un evento mal etiquetado en producción: hay un `baja_candidato`
    con `empresa_id NULL` sobre un candidato que sí tenía empresa.
    """

    @staticmethod
    def _candidato() -> CandidatoResponse:
        return CandidatoResponse(
            id="c1", vacante_id=None, empresa_id=_EMPRESA_DEL_CANDIDATO,
            nombre="Ana", apellido="Lopez", email="a@x.com", etapa_pipeline="postulado",
            created_at=datetime(2026, 1, 1, 9, 0),
        )

    class _Repo:
        """HONRA empresa_id: devuelve None si el header no coincide con la empresa del candidato.

        Un fake que aceptara el parámetro y lo ignorara dejaría sin probar la barrera de empresa
        —caso #1 de "un test solo prueba lo que el fake puede desmentir"—, que es justo lo que
        este service tiene que seguir respetando después del cambio.
        """

        def __init__(self, cand: CandidatoResponse) -> None:
            self._cand = cand
            self.borrados: list[str] = []

        def find_by_id(self, candidato_id, empresa_id=None):
            if empresa_id and str(empresa_id) != self._cand.empresa_id:
                return None
            return self._cand if candidato_id == self._cand.id else None

        def delete(self, candidato_id, empresa_id=None) -> None:
            self.borrados.append(candidato_id)

    def test_baja_usa_empresa_del_candidato_no_del_header(self) -> None:
        """Header consolidado (None) + candidato con empresa → el evento lleva la del candidato.

        ¿Qué tendría que ser distinto en el fake para que falle? Que `find_by_id` devolviera un
        candidato SIN `empresa_id` (como antes del cambio, cuando el schema no declaraba el
        campo): ahí las dos fuentes darían None y la aserción no distinguiría nada. Con el
        candidato en `_EMPRESA_DEL_CANDIDATO` y el header en None, leer el header da None y leer
        la entidad da la empresa: solo una de las dos implementaciones pasa.
        """
        audit = _FakeAudit()
        repo = self._Repo(self._candidato())
        svc = CandidatoService(candidato_repo=repo, audit=audit)

        svc.delete_candidato("c1", empresa_id=None, usuario_id="u1")

        assert repo.borrados == ["c1"]          # el borrado ocurrió (el evento no es un no-op)
        c = audit.calls[0]
        assert (c["evento"], c["accion"], c["entidad"]) == ("baja_candidato", "DELETE", "candidato")
        assert c["empresa_id"] == _EMPRESA_DEL_CANDIDATO   # de la entidad, no del header (None)
        assert c["datos_anteriores"]["nombre"] == "Ana Lopez"

    def test_baja_ignora_un_header_que_contradice_al_candidato(self) -> None:
        """Con un header REAL e igual al del candidato, el evento sigue saliendo de la entidad.

        No se puede pasar un header DISTINTO como en presupuesto: la barrera de empresa haría
        que `find_by_id` devuelva None y el service corte con 404 antes de auditar. Ese es el
        comportamiento correcto, así que lo que se fija acá es que con el header presente el
        valor tampoco se toma de él —da igual porque coinciden—, y que la barrera sigue viva.
        """
        audit = _FakeAudit()
        repo = self._Repo(self._candidato())
        svc = CandidatoService(candidato_repo=repo, audit=audit)

        svc.delete_candidato("c1", empresa_id=_EMPRESA_DEL_CANDIDATO, usuario_id="u1")
        assert audit.calls[0]["empresa_id"] == _EMPRESA_DEL_CANDIDATO

    def test_la_barrera_de_empresa_sigue_viva_y_no_audita(self) -> None:
        """Un candidato de otra empresa da 404 y NO genera evento: el fix no aflojó la barrera."""
        import pytest

        from utils.errors import AppError

        audit = _FakeAudit()
        svc = CandidatoService(candidato_repo=self._Repo(self._candidato()), audit=audit)

        with pytest.raises(AppError) as exc:
            svc.delete_candidato("c1", empresa_id="otra-empresa", usuario_id="u1")
        assert exc.value.code == "CANDIDATO_NOT_FOUND"
        assert audit.calls == []


class TestElMapperNoPierdeLaEmpresa:
    """🔴 EL ESLABÓN QUE LOS TESTS DE SERVICE NO PUEDEN VER.

    Los tests de arriba inyectan repos FALSOS, así que prueban que el service usa
    `entidad.empresa_id` — pero no que el repo REAL lo ponga ahí. Ese era exactamente el bug:
    en los dos casos la columna ya viajaba en el SELECT (`_PRE_SEL` la nombra; `_crow` hace
    `select("*")`) y el MAPPER la descartaba al construir el response. Sin estos tests, borrar
    la línea del mapper deja los tests de service en verde y el evento vuelve a grabarse con
    `empresa_id` NULL en producción, en silencio.

    ¿Qué tendría que ser distinto en el fake para que fallen? Nada: no hay fake. Se invocan las
    funciones de mapeo REALES con un row como el que devuelve PostgREST. Lo único que podría
    volverlos vacuos es que el row de entrada no trajera `empresa_id` — por eso lo trae, y con
    un valor distinguible.
    """

    def test_to_presupuesto_mapea_empresa_id(self) -> None:
        from repositories.presupuesto_repo import _to_presupuesto

        row = {"id": "p1", "area_id": "ar1", "empresa_id": "e-77", "mes": 6, "anio": 2026,
               "monto_presupuestado": "500.0", "areas": {"nombre": "Sistemas"}}
        assert _to_presupuesto(row).empresa_id == "e-77"

    def test_crow_mapea_empresa_id(self) -> None:
        from repositories.candidato_repo import _crow

        row = {"id": "c1", "vacante_id": None, "empresa_id": "e-88", "nombre": "Ana",
               "apellido": "Lopez", "email": "a@x.com", "etapa": "postulado",
               "created_at": "2026-01-01T09:00:00Z"}
        assert _crow(row).empresa_id == "e-88"

    def test_ninguno_inventa_una_empresa_si_el_row_no_la_trae(self) -> None:
        """Un row sin la columna da None, no un string 'None' ni un KeyError: los dos mappers
        corren sobre filas legacy y sobre SELECTs que podrían no pedirla."""
        from repositories.candidato_repo import _crow
        from repositories.presupuesto_repo import _to_presupuesto

        pres = _to_presupuesto({"id": "p1", "area_id": "ar1", "mes": 6, "anio": 2026,
                                "monto_presupuestado": "500.0", "areas": {"nombre": "S"}})
        cand = _crow({"id": "c1", "vacante_id": None, "nombre": "Ana", "apellido": "Lopez",
                      "email": "a@x.com", "etapa": "postulado",
                      "created_at": "2026-01-01T09:00:00Z"})
        assert pres.empresa_id is None and cand.empresa_id is None
