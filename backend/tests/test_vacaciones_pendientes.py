"""
Tests de los días de vacaciones PENDIENTES (tabla nueva, migración 083) — sin red.

Cubre lo que justifica el diseño de tablas separadas y las dos barreras:
  1. El alta ENRUTA según si se tomó o no: con fechas → solicitudes_vacaciones, sin fechas →
     vacaciones_pendientes. Son dos tablas distintas, no dos formas de la misma fila.
  2. Barrera de empresa: un empleado de otra empresa da el MISMO 404 (code y mensaje) que uno
     inexistente. Un 403, o un texto distinto, sería un oráculo de enumeración.
  3. Ownership: VACACIONES está en MANDOS_MEDIOS_SECCIONES, así que un mando entra a estos
     endpoints. Solo ve/gestiona a su gente, por INTERSECCIÓN con la empresa.
  4. dias_liquidados se edita después de creada (es el tilde "Liquidada" de la UI).
  5. Los reportes / el mapa / el saldo / el export NO ven esta tabla. Es lo que hace que
     permitir días sin fecha no rompa nada — el punto entero de la migración 083.

⚠️ TODOS LOS FAKES DE ESTE ARCHIVO HONRAN empresa_id: modelan DOS empresas y devuelven None
cuando no coincide. Un fake que acepta empresa_id y lo ignora da VERDE FALSO — es exactamente
el bug que estos tests vienen a cubrir. NO calcar los fakes permisivos de
test_escrituras_ownership.py:98 ni de test_audit_instrumentacion.py:71.

¿Qué tendría que ser distinto en cada fake para que el test pueda fallar? La respuesta está
en el docstring de cada test.
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

import inspect
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from schemas.empleado import EmpleadoResponse
from schemas.vacaciones_pendientes import (
    VacacionPendienteCreate, VacacionPendienteResponse, VacacionPendienteUpdate,
)
from services.vacaciones_pendientes_service import VacacionesPendientesService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROPIO = UUID("11111111-1111-1111-1111-111111111111")       # empresa A, ES el mando
AJENO = UUID("22222222-2222-2222-2222-222222222222")        # empresa B
INEXISTENTE = UUID("33333333-3333-3333-3333-333333333333")
SUBORDINADO = UUID("44444444-4444-4444-4444-444444444444")  # empresa A, a cargo del mando
# 🔴 Empresa A pero FUERA del alcance del mando. Existe para que el eje de OWNERSHIP se pueda
# probar solo: contra un empleado de otra empresa, la barrera de empresa ya lo frenaría y el
# test pasaría con el ownership borrado (verificado por mutación).
OTRO_DE_A = UUID("66666666-6666-6666-6666-666666666666")
MANDO_UID = "user-mando"
ADMIN_UID = "user-admin"


def _empleado(id_: UUID, empresa_id: UUID) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(id_), "nombre": "N", "apellido": "A", "email_corporativo": f"{id_}@k.com",
        "empresa_id": str(empresa_id), "area_id": "55555555-5555-5555-5555-555555555555",
        "roles": ["Analista"], "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


class _EmpleadoRepo:
    """HONRA empresa_id: devuelve None si el empleado es de otra empresa (como _with_empresa)."""

    def __init__(self) -> None:
        self._por_id = {
            PROPIO: _empleado(PROPIO, EMPRESA_A),
            SUBORDINADO: _empleado(SUBORDINADO, EMPRESA_A),
            OTRO_DE_A: _empleado(OTRO_DE_A, EMPRESA_A),
            AJENO: _empleado(AJENO, EMPRESA_B),
        }

    def find_by_id(self, id: str, empresa_id=None):
        emp = self._por_id.get(UUID(str(id)))
        if emp is None:
            return None
        if empresa_id and emp.empresa_id != str(empresa_id):
            return None   # ← sin esta línea el test de barrera de empresa NO puede fallar
        return emp


class _OwnershipRepo:
    """El mando es PROPIO y tiene un solo subordinado. admin/gerencia no pasan por acá."""

    def find_by_user_id(self, user_id: str):
        return {"id": str(PROPIO)} if user_id == MANDO_UID else None

    def ids_subordinados(self, emp_id: str):
        return [str(SUBORDINADO)] if emp_id == str(PROPIO) else []

    def ids_empleados_por_area(self, empresa_id, area_id):
        return [str(PROPIO), str(SUBORDINADO)]


class _PendientesRepo:
    """Fake del repo de pendientes.

    HONRA empresa_id en find_by_id / update / delete (Forma A: el filtro va en el WHERE), y
    CONSTRUYE la respuesta A PARTIR de lo que recibe — nunca devuelve un objeto prefabricado.
    Si devolviera una constante, un test de "se guardó lo que mandé" estaría afirmando algo
    sobre su propia constante y pasaría con el service roto.
    """

    def __init__(self) -> None:
        self.filas: dict[str, dict] = {}
        self.creados: list[dict] = []

    def _resp(self, fila: dict) -> VacacionPendienteResponse:
        return VacacionPendienteResponse.model_validate({
            **fila, "empresa_nombre": "Empresa", "empleado_nombre": "N A",
            "area_id": None, "area_nombre": None, "created_at": "2026-01-01T00:00:00Z",
        })

    def crear(self, datos: dict) -> VacacionPendienteResponse:
        fila = {"id": str(uuid4()), **datos}          # ← construida DESDE lo recibido
        self.filas[fila["id"]] = fila
        self.creados.append(datos)
        return self._resp(fila)

    def find_by_id(self, id: str, empresa_id=None):
        fila = self.filas.get(str(id))
        if fila is None:
            return None
        if empresa_id and fila["empresa_id"] != str(empresa_id):
            return None
        return self._resp(fila)

    def find_by_empleado(self, empleado_id: str, empresa_id=None):
        return [self._resp(f) for f in self.filas.values()
                if f["empleado_id"] == str(empleado_id)
                and (not empresa_id or f["empresa_id"] == str(empresa_id))]

    def find_all(self, empresa_id=None, empleado_ids=None, page=1, page_size=20):
        filas = [f for f in self.filas.values()
                 if (not empresa_id or f["empresa_id"] == str(empresa_id))
                 and (empleado_ids is None or f["empleado_id"] in empleado_ids)]
        return [self._resp(f) for f in filas], len(filas)

    def update(self, id: str, patch: dict, empresa_id=None):
        fila = self.filas.get(str(id))
        if fila is None or (empresa_id and fila["empresa_id"] != str(empresa_id)):
            return None
        fila.update(patch)
        return self._resp(fila)

    def delete(self, id: str, empresa_id=None) -> bool:
        fila = self.filas.get(str(id))
        if fila is None or (empresa_id and fila["empresa_id"] != str(empresa_id)):
            return False
        del self.filas[str(id)]
        return True


class _Audit:
    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _svc():
    repo, audit = _PendientesRepo(), _Audit()
    return VacacionesPendientesService(repo, audit, _OwnershipRepo(), _EmpleadoRepo()), repo, audit


def _crear(svc, empleado_id=PROPIO, periodo=2025, dias=10, liquidados=0,
           user=ADMIN_UID, rol="admin_rrhh", empresa=EMPRESA_A):
    return svc.crear(
        VacacionPendienteCreate(empleado_id=empleado_id, periodo=periodo, dias=dias,
                                dias_liquidados=liquidados),
        user, rol, empresa)


class TestAltaEnrutaSegunSiSeTomo:
    def test_dias_pendientes_van_a_vacaciones_pendientes(self):
        """El alta sin fechas persiste en vacaciones_pendientes, con período y días.

        Para que falle: que `crear` no llame al repo de pendientes, o que pierda `periodo`.
        El fake registra lo RECIBIDO (`creados`), así que la aserción mira el payload real y
        no una constante propia."""
        svc, repo, _ = _svc()
        row = _crear(svc, periodo=2025, dias=10)
        assert len(repo.creados) == 1
        guardado = repo.creados[0]
        assert guardado["periodo"] == 2025
        assert guardado["dias"] == 10
        assert guardado["empleado_id"] == str(PROPIO)
        assert row.periodo == 2025 and row.dias == 10
        # Sin fechas por construcción: el schema de pendientes no tiene esos campos.
        assert not hasattr(row, "fecha_desde")

    def test_la_empresa_sale_del_empleado_no_del_header(self):
        """Vista vs Acción: escribir es una ACCIÓN, la empresa la da la entidad.

        Para que falle: que el service use el `empresa_id` del header como empresa_id de la
        fila. El fake de empleados devuelve EMPRESA_A, así que pasar None (consolidado) tiene
        que seguir escribiendo en EMPRESA_A."""
        svc, repo, _ = _svc()
        _crear(svc, empresa=None)   # modo consolidado: el header no dice nada
        assert repo.creados[0]["empresa_id"] == str(EMPRESA_A)

    def test_vacacion_tomada_no_pasa_por_este_service(self):
        """La licencia CON fechas es otra tabla y otro service: este no la puede crear.

        Es la aserción estructural del diseño. Para que falle: que VacacionPendienteCreate
        aceptara fechas — o sea, que alguien fusionara los dos modelos."""
        campos = VacacionPendienteCreate.model_fields
        assert "fecha_desde" not in campos and "fecha_hasta" not in campos


class TestBarreraDeEmpresa:
    def test_empleado_de_otra_empresa_da_el_mismo_404_que_inexistente(self):
        """Ajeno e inexistente: MISMO status, MISMO code, MISMO mensaje. Nunca un 403.

        Para que falle: que _EmpleadoRepo.find_by_id ignore empresa_id (la línea marcada).
        Ahí el ajeno se crearía y no habría excepción que comparar."""
        svc, _, _ = _svc()
        with pytest.raises(AppError) as ajeno:
            _crear(svc, empleado_id=AJENO)
        with pytest.raises(AppError) as inexistente:
            _crear(svc, empleado_id=INEXISTENTE)
        assert ajeno.value.status_code == inexistente.value.status_code == 404
        assert ajeno.value.code == inexistente.value.code == "EMPLEADO_NOT_FOUND"
        assert str(ajeno.value) == str(inexistente.value)

    def test_registro_de_otra_empresa_no_se_puede_editar_ni_borrar(self):
        """El id existe pero es de otra empresa → 404, no 403 (y el mismo que inexistente).

        Para que falle: que TODOS los métodos de _PendientesRepo dejen de honrar empresa_id.
        Con uno solo no alcanza, y eso es la propiedad buscada, no una debilidad del test: en
        Forma A cada query lleva la empresa en su WHERE, así que find_by_id, update y delete
        la frenan de forma independiente. Verificado por mutación: neutralizar un guarda deja
        el test en verde (lo ataja el siguiente); neutralizar los cuatro lo hace fallar."""
        svc, _, _ = _svc()
        row = _crear(svc)   # queda en EMPRESA_A
        with pytest.raises(AppError) as editar:
            svc.actualizar(UUID(row.id), VacacionPendienteUpdate(dias_liquidados=1),
                           EMPRESA_B, ADMIN_UID, "admin_rrhh")
        with pytest.raises(AppError) as inexistente:
            svc.actualizar(UUID(str(uuid4())), VacacionPendienteUpdate(dias_liquidados=1),
                           EMPRESA_A, ADMIN_UID, "admin_rrhh")
        assert editar.value.status_code == inexistente.value.status_code == 404
        assert editar.value.code == inexistente.value.code == "VACACION_PENDIENTE_NOT_FOUND"
        assert str(editar.value) == str(inexistente.value)
        with pytest.raises(AppError):
            svc.eliminar(UUID(row.id), EMPRESA_B, ADMIN_UID, "admin_rrhh")


class TestOwnershipDelMandoMedio:
    def test_el_mando_solo_ve_los_pendientes_de_su_gente(self):
        """INTERSECCIÓN empresa ∩ ownership en el listado: ve los suyos, no los del resto.

        Para que falle: que get_all ignore `empleado_ids` del resolver. Hay un tercer empleado
        de la MISMA empresa (OTRO_DE_A) que el mando NO tiene a cargo — sin él, un filtro
        roto devolvería lo mismo que uno correcto y el test no probaría nada."""
        svc, repo, _ = _svc()
        _crear(svc, empleado_id=PROPIO)
        _crear(svc, empleado_id=SUBORDINADO)
        _crear(svc, empleado_id=OTRO_DE_A)   # misma empresa, FUERA del alcance del mando
        del_mando = svc.get_all(MANDO_UID, "mandos_medios", EMPRESA_A)
        assert del_mando.total == 2
        assert {i.empleado_id for i in del_mando.items} == {str(PROPIO), str(SUBORDINADO)}

        del_admin = svc.get_all(ADMIN_UID, "admin_rrhh", EMPRESA_A)
        assert del_admin.total == 3   # admin no tiene restricción de ownership

    def test_el_mando_no_puede_crear_a_nombre_de_alguien_que_no_gestiona(self):
        """Ownership sobre el empleado TARGET, no solo sobre el listado.

        🔴 El objetivo es OTRO_DE_A —MISMA empresa, fuera de su alcance—, no un empleado de
        otra empresa: contra ese, la barrera de empresa sola ya devolvería 404 y el test
        pasaría con el ownership borrado. Verificado por mutación: cambiar
        ensure_empleado_visible por ensure_empleado_de_empresa hace fallar este test.

        El 404 tiene que ser el MISMO que el de un empleado inexistente: un mando no debe
        poder distinguir 'no existe' de 'existe pero no es tuyo'."""
        svc, _, _ = _svc()
        _crear(svc, empleado_id=SUBORDINADO, user=MANDO_UID, rol="mandos_medios")  # su gente: OK
        with pytest.raises(AppError) as fuera_de_alcance:
            _crear(svc, empleado_id=OTRO_DE_A, user=MANDO_UID, rol="mandos_medios")
        with pytest.raises(AppError) as inexistente:
            _crear(svc, empleado_id=INEXISTENTE, user=MANDO_UID, rol="mandos_medios")
        assert fuera_de_alcance.value.status_code == inexistente.value.status_code == 404
        assert fuera_de_alcance.value.code == inexistente.value.code == "EMPLEADO_NOT_FOUND"
        assert str(fuera_de_alcance.value) == str(inexistente.value)

    def test_el_mando_no_puede_editar_ni_borrar_lo_de_otro(self):
        """Ownership también en la ESCRITURA sobre un registro existente, no solo en el alta.

        El registro es de OTRO_DE_A: MISMA empresa, fuera del alcance del mando. Así el eje de
        empresa no lo frena y solo puede frenarlo el ownership. Verificado por mutación: sacar
        el chequeo de `_gestionable` hace fallar este test y ningún otro — sin él, un mando
        podía editar y borrar los pendientes de cualquiera de su empresa."""
        svc, _, _ = _svc()
        ajeno = _crear(svc, empleado_id=OTRO_DE_A)   # lo carga un admin

        with pytest.raises(AppError) as editar:
            svc.actualizar(UUID(ajeno.id), VacacionPendienteUpdate(dias_liquidados=1),
                           EMPRESA_A, MANDO_UID, "mandos_medios")
        with pytest.raises(AppError) as borrar:
            svc.eliminar(UUID(ajeno.id), EMPRESA_A, MANDO_UID, "mandos_medios")
        assert editar.value.status_code == borrar.value.status_code == 404
        assert editar.value.code == borrar.value.code == "VACACION_PENDIENTE_NOT_FOUND"

        # Y sobre SU gente sí puede: si no, el test pasaría con el ownership devolviendo
        # siempre False, que no es lo que se quiere probar.
        propio = _crear(svc, empleado_id=SUBORDINADO)
        assert svc.actualizar(UUID(propio.id), VacacionPendienteUpdate(dias_liquidados=1),
                              EMPRESA_A, MANDO_UID, "mandos_medios").dias_liquidados == 1

    def test_rol_desconocido_no_ve_nada(self):
        """Fail-closed: `vacio` del contrato de la tupla → NO se consulta la tabla."""
        svc, _, _ = _svc()
        _crear(svc)
        assert svc.get_all("quien-sabe", "rol_inventado", EMPRESA_A).total == 0


class TestLiquidadaEditableDespues:
    def test_marcar_liquidada_despues_de_creada(self):
        """El tilde de la UI: dias_liquidados pasa de 0 a todos los días, y vuelve.

        Para que falle: que el repo fake devolviera una constante en vez de aplicar el patch.
        `update` muta la fila guardada, así que la aserción mira el efecto real."""
        svc, _, _ = _svc()
        row = _crear(svc, dias=10, liquidados=0)
        assert row.dias_liquidados == 0

        liquidada = svc.actualizar(UUID(row.id), VacacionPendienteUpdate(dias_liquidados=10),
                                   EMPRESA_A, ADMIN_UID, "admin_rrhh")
        assert liquidada.dias_liquidados == 10

        revertida = svc.actualizar(UUID(row.id), VacacionPendienteUpdate(dias_liquidados=0),
                                   EMPRESA_A, ADMIN_UID, "admin_rrhh")
        assert revertida.dias_liquidados == 0

    def test_liquidacion_parcial_entra_en_una_sola_fila(self):
        """La razón de que dias_liquidados sea INT y no bool: 5 de 10 en UNA fila.

        Con un bool haría falta una segunda fila del mismo (empleado, período), que es lo que
        la UNIQUE de la migración 083 prohíbe. Para que falle: volver el campo a booleano."""
        svc, _, _ = _svc()
        row = _crear(svc, dias=10, liquidados=0)
        parcial = svc.actualizar(UUID(row.id), VacacionPendienteUpdate(dias_liquidados=5),
                                 EMPRESA_A, ADMIN_UID, "admin_rrhh")
        assert parcial.dias_liquidados == 5 and parcial.dias == 10

    def test_no_se_pueden_liquidar_mas_dias_de_los_que_hay(self):
        """Espejo del CHECK vp_dias_liquidados_check: 422 de negocio, no un 500 de la DB."""
        svc, _, _ = _svc()
        with pytest.raises(AppError) as exc:
            _crear(svc, dias=10, liquidados=11)
        assert exc.value.status_code == 422
        assert exc.value.code == "DIAS_LIQUIDADOS_INVALIDOS"


class TestAuditoria:
    def test_alta_edicion_y_baja_registran_evento(self):
        """Un evento por operación, con la empresa de la ENTIDAD (no del header)."""
        svc, _, audit = _svc()
        row = _crear(svc, empresa=None)   # consolidado: el header no aporta empresa
        svc.actualizar(UUID(row.id), VacacionPendienteUpdate(dias_liquidados=10),
                       EMPRESA_A, ADMIN_UID, "admin_rrhh")
        svc.eliminar(UUID(row.id), EMPRESA_A, ADMIN_UID, "admin_rrhh")

        eventos = [e["evento"] for e in audit.eventos]
        assert eventos == ["alta_vacacion_pendiente", "update_vacacion_pendiente",
                           "baja_vacacion_pendiente"]
        assert all(e["entidad"] == "vacacion_pendiente" for e in audit.eventos)
        # La empresa sale de la entidad aunque el header fuera None (Vista vs Acción).
        assert audit.eventos[0]["empresa_id"] == str(EMPRESA_A)

    def test_la_baja_audita_el_snapshot_previo(self):
        """El DELETE guarda datos_anteriores: después de borrar la fila ya no existe."""
        svc, _, audit = _svc()
        row = _crear(svc, dias=7)
        svc.eliminar(UUID(row.id), EMPRESA_A, ADMIN_UID, "admin_rrhh")
        baja = audit.eventos[-1]
        assert baja["datos_nuevos"] is None
        assert baja["datos_anteriores"]["dias"] == 7

    def test_el_diff_excluye_derivados_en_vez_de_enumerar(self):
        """Los payloads usan sin_derivados, así que una columna NUEVA se audita sola.

        Para que falle: que alguien cambie a una lista curada de campos — ahí una columna
        nueva dejaría de registrarse EN SILENCIO, que en un log de auditoría es peor que un
        campo de más."""
        from services import _audit_payloads_vacaciones as pl
        fuente = inspect.getsource(pl)
        assert "sin_derivados" in fuente
        assert "_subset" not in fuente


class TestLaTablaNuevaNoTocaLoQueYaFuncionaba:
    """🔴 Es lo que justifica el diseño de tablas separadas: si algo de esto falla, la
    decisión de no permitir fechas NULL en solicitudes_vacaciones no compró nada."""

    def test_las_fechas_de_solicitudes_vacaciones_siguen_siendo_obligatorias(self):
        """El schema de la licencia tomada NO acepta fechas nulas.

        Es la aserción central. Para que falle: que alguien vuelva `fecha_desde` Optional —
        que es justo el cambio que dispara los 6 crashes y las 9 fallas silenciosas."""
        from schemas.vacaciones import SolicitudVacacionesCreate, SolicitudVacacionesResponse
        assert SolicitudVacacionesCreate.model_fields["fecha_desde"].is_required()
        assert SolicitudVacacionesCreate.model_fields["fecha_hasta"].is_required()
        assert SolicitudVacacionesResponse.model_fields["fecha_desde"].is_required()

    def test_derive_estado_sigue_derivando_de_las_fechas(self):
        """El estado de una licencia tomada no cambió: planificada/tomada/cancelada."""
        from datetime import date as _date

        from schemas.vacaciones import SolicitudVacacionesResponse
        from services._vacaciones_utils import derive_estado

        hoy = _date.today()
        base = {
            "id": str(uuid4()), "empleado_id": str(PROPIO), "empresa_id": str(EMPRESA_A),
            "dias": 5, "tipo": "vacaciones", "cancelada": False, "estado": "",
            "created_at": "2026-01-01T00:00:00Z",
        }
        futura = SolicitudVacacionesResponse.model_validate({
            **base, "fecha_desde": str(hoy + timedelta(days=5)),
            "fecha_hasta": str(hoy + timedelta(days=9))})
        pasada = SolicitudVacacionesResponse.model_validate({
            **base, "fecha_desde": str(hoy - timedelta(days=9)),
            "fecha_hasta": str(hoy - timedelta(days=5))})
        assert derive_estado(futura, hoy).estado == "planificada"
        assert derive_estado(pasada, hoy).estado == "tomada"

    def test_el_saldo_no_mira_la_tabla_de_pendientes(self):
        """El cálculo del saldo quedó EXPLÍCITAMENTE fuera de alcance hasta definirlo con RRHH.

        Para que falle: que alguien enganche los pendientes al saldo antes de esa definición.
        Se mira el código fuente porque el punto es que la dependencia no exista, no que
        devuelva cierto número."""
        from services import _vacaciones_saldo
        fuente = inspect.getsource(_vacaciones_saldo)
        assert "pendiente" not in fuente.lower()

    def test_los_reportes_y_el_export_no_miran_la_tabla_de_pendientes(self):
        """R9/R11 y el export de vacaciones siguen leyendo SOLO solicitudes_vacaciones.

        Guarda de mínimo incluida: si el barrido dejara de encontrar módulos, pasaría sin
        haber comparado nada."""
        from services import _vacaciones_export
        from services.reportes import _reporte_vacaciones

        modulos = [_reporte_vacaciones, _vacaciones_export]
        assert len(modulos) >= 2
        for mod in modulos:
            assert "vacaciones_pendientes" not in inspect.getsource(mod), mod.__name__

    def test_el_repo_de_pendientes_lleva_la_empresa_en_la_query(self):
        """Forma A: el filtro va en el WHERE, no comparado después en el service.

        Un service que compara la empresa DESPUÉS de traer la fila se lee igual de seguro y
        es más fácil de olvidar. Se verifica un escalón más abajo que el resto de los tests
        —sobre el código de la query— porque es ahí donde vive la garantía."""
        from repositories import vacaciones_pendientes_repo
        for metodo in ("find_by_id", "update", "delete", "find_all"):
            fuente = inspect.getsource(getattr(vacaciones_pendientes_repo.VacacionesPendientesRepo, metodo))
            assert 'eq("empresa_id"' in fuente, metodo
