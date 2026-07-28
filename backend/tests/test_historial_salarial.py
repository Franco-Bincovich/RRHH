"""
Historial salarial del legajo: la serie de costos_nomina de un empleado.

🔴 ESTOS TESTS SON LA ÚNICA RED. `costos_nomina` tiene **0 filas en producción**, así que no
hay forma de verificar esta feature contra datos reales: no se puede abrir un legajo y mirar
si la serie sale bien, porque no hay serie. Todo lo que se sabe del comportamiento se sabe
por acá. Escritos con eso en mente — cubren el orden, las dos barreras, el vacío y la
derivación del neto, que es lo que un dato real habría desmentido si estuviera mal.

🚨 EL FAKE HONRA `empresa_id`: `find_by_id` devuelve None cuando el empleado es de otra
empresa, igual que el WHERE real, y `find_by_empleado` filtra la serie. Un fake que aceptara
el parámetro y lo ignorara daría verde sobre exactamente el agujero que estos tests cubren.

POR QUÉ LA SERIE Y NO EL AUDIT LOG: `UNIQUE (empleado_id, anio, mes)` hace que la progresión
salarial ya esté en los datos. Con auditoría, el caso más común —sueldos importados por CSV y
nunca editados— daría historial vacío teniendo los sueldos cargados.
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
from uuid import uuid4

import pytest

from repositories._nomina_row import item
from services.costo_service import CostoService
from utils.errors import AppError
from utils.permisos import Accion, Seccion, puede

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
EMP_A, EMP_B = uuid4(), uuid4()


class _FakeEmpleadoRepo:
    """DOS empresas. `find_by_id` devuelve None si el empleado no es de `empresa_id`, que es
    lo que hace el WHERE real — sin esto la barrera de empresa no se estaría probando."""

    def find_by_id(self, id, empresa_id=None):
        de = {str(EMP_A): EMPRESA_A, str(EMP_B): EMPRESA_B}.get(str(id))
        if de is None:
            return None
        if empresa_id and de != empresa_id:
            return None
        return SimpleNamespace(id=str(id), empresa_id=str(de))


class _FakeNominaRepo:
    """Serie por empleado, ordenada del período más reciente al más viejo (como la query)."""

    def __init__(self, filas: dict) -> None:
        self.filas = filas
        self.recibido: dict = {}

    def find_by_empleado(self, empleado_id, empresa_id=None):
        self.recibido = {"empleado_id": empleado_id, "empresa_id": empresa_id}
        crudas = self.filas.get(str(empleado_id), [])
        ordenadas = sorted(crudas, key=lambda r: (r["anio"], r["mes"]), reverse=True)
        return [item(r) for r in ordenadas]


def _fila(anio: int, mes: int, bruto: float, cargas: float = 0.0) -> dict:
    return {"anio": anio, "mes": mes, "salario_bruto": bruto, "cargas_sociales": cargas}


SERIE = {
    str(EMP_A): [
        _fila(2026, 3, 1000.0, 200.0), _fila(2026, 1, 800.0, 160.0),
        _fila(2025, 12, 750.0, 150.0), _fila(2026, 2, 900.0, 180.0),
    ],
    str(EMP_B): [_fila(2026, 3, 5000.0, 1000.0)],
}


def _svc(filas=None):
    nomina = _FakeNominaRepo(SERIE if filas is None else filas)
    return CostoService(nomina_repo=nomina, empleado_repo=_FakeEmpleadoRepo()), nomina


# ─── La serie ─────────────────────────────────────────────────────────────────


class TestLaSerie:
    def test_sale_ordenada_del_periodo_mas_reciente_al_mas_viejo(self) -> None:
        """La serie ES el producto: un orden que dependa de cómo lleguen las filas se rompe
        en silencio y el legajo muestra la progresión salarial al revés."""
        svc, _ = _svc()
        periodos = [(h.anio, h.mes) for h in svc.get_historial_salarial(EMP_A, EMPRESA_A)]
        assert periodos == [(2026, 3), (2026, 2), (2026, 1), (2025, 12)]

    def test_cruza_el_cambio_de_anio(self) -> None:
        """Diciembre 2025 va DESPUÉS de enero 2026: ordenar por mes solo lo pondría primero."""
        svc, _ = _svc()
        assert [(h.anio, h.mes) for h in svc.get_historial_salarial(EMP_A, EMPRESA_A)][-1] == (2025, 12)

    def test_un_empleado_sin_nomina_devuelve_lista_vacia(self) -> None:
        """NO es un error: hoy es el caso de los 19 empleados de producción."""
        svc, _ = _svc({})
        assert svc.get_historial_salarial(EMP_A, EMPRESA_A) == []


class TestElNeto:
    def test_se_deriva_restando_las_cargas(self) -> None:
        """`monto_neto` no es una columna: la tabla guarda bruto y cargas."""
        h = _svc()[0].get_historial_salarial(EMP_A, EMPRESA_A)[0]
        assert (h.monto_bruto, h.monto_neto) == (1000.0, 800.0)

    def test_sin_cargas_el_neto_es_el_bruto(self) -> None:
        """cargas = 0 es el default de la columna: el import solo escribe bruto y cargas, y
        una fila cargada a mano sin cargas tiene que dar neto = bruto, no 0."""
        svc, _ = _svc({str(EMP_A): [_fila(2026, 3, 1000.0, 0.0)]})
        h = svc.get_historial_salarial(EMP_A, EMPRESA_A)[0]
        assert h.monto_neto == 1000.0

    def test_cargas_nulas_no_rompen(self) -> None:
        svc, _ = _svc({str(EMP_A): [{"anio": 2026, "mes": 3, "salario_bruto": 500.0,
                                     "cargas_sociales": None}]})
        assert svc.get_historial_salarial(EMP_A, EMPRESA_A)[0].monto_neto == 500.0

    def test_no_expone_el_total_generado(self) -> None:
        """`total` es bruto+cargas+bonos+otros: el COSTO para la empresa, no lo que cobra la
        persona. En un legajo se leería como sueldo."""
        h = _svc()[0].get_historial_salarial(EMP_A, EMPRESA_A)[0]
        assert not hasattr(h, "total")


class TestElOrdenLoPoneLaQuery:
    """🔴 EL FAKE DE REPO NO ALCANZA PARA EL ORDEN, y el mutation check lo mostró.

    El fake de arriba ordena en Python, así que fija el CONTRATO (la serie sale del período
    más reciente al más viejo) pero no toca el `.order()` real: sacarle el `desc=True` al año
    dejaba todo en verde. Acá se faltea un escalón más abajo —el cliente de Supabase— para
    verificar que el orden viaje EN LA QUERY, que es donde tiene que estar: ordenar en Python
    depende de haberse traído todas las filas, y la serie de un empleado con años de nómina no
    tiene por qué caber en una sola página.

    (Mismo molde que TestElWhereDelRepoLlevaLaEmpresa en test_offboarding_entrevista.py.)"""

    def _repo_con_espia(self, monkeypatch):
        import repositories.nomina_repo as mod

        ordenes: list = []

        class _Q:
            def select(self, *a, **k):
                return self

            def eq(self, *a, **k):
                return self

            def order(self, col, desc=False):
                ordenes.append((col, desc))
                return self

            def execute(self):
                return SimpleNamespace(data=[], count=0)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.NominaRepo(), ordenes

    def test_ordena_por_anio_descendente(self, monkeypatch) -> None:
        repo, ordenes = self._repo_con_espia(monkeypatch)
        repo.find_by_empleado(str(EMP_A), EMPRESA_A)
        assert ("anio", True) in ordenes

    def test_y_despues_por_mes_descendente(self, monkeypatch) -> None:
        repo, ordenes = self._repo_con_espia(monkeypatch)
        repo.find_by_empleado(str(EMP_A), EMPRESA_A)
        assert ordenes == [("anio", True), ("mes", True)], (
            "el año tiene que ordenar ANTES que el mes: al revés, diciembre de 2025 sale "
            "arriba de enero de 2026."
        )


# ─── Barrera de empresa ───────────────────────────────────────────────────────


class TestBarreraDeEmpresa:
    def test_empleado_de_otra_empresa_da_404(self) -> None:
        svc, _ = _svc()
        with pytest.raises(AppError) as exc:
            svc.get_historial_salarial(EMP_B, EMPRESA_A)
        assert exc.value.status_code == 404

    def test_el_404_es_IDENTICO_al_de_no_existe(self) -> None:
        """Un code o un mensaje distinto confirmaría que el empleado existe y es de otra
        empresa: un oráculo para enumerar la nómina ajena."""
        svc, _ = _svc()
        with pytest.raises(AppError) as ajeno:
            svc.get_historial_salarial(EMP_B, EMPRESA_A)
        with pytest.raises(AppError) as inexistente:
            svc.get_historial_salarial(uuid4(), EMPRESA_A)
        assert (ajeno.value.code, ajeno.value.status_code, ajeno.value.message) == \
               (inexistente.value.code, inexistente.value.status_code, inexistente.value.message)

    def test_nunca_es_403(self) -> None:
        svc, _ = _svc()
        with pytest.raises(AppError) as exc:
            svc.get_historial_salarial(EMP_B, EMPRESA_A)
        assert exc.value.status_code != 403

    def test_no_filtra_ni_un_monto_del_ajeno(self) -> None:
        """Que tire 404 no alcanza si igual consultó la serie: se verifica que NO llegó al repo."""
        svc, nomina = _svc()
        with pytest.raises(AppError):
            svc.get_historial_salarial(EMP_B, EMPRESA_A)
        assert nomina.recibido == {}

    def test_la_empresa_llega_al_repo(self) -> None:
        """La barrera valida el empleado; el filtro de la serie tiene que viajar igual."""
        svc, nomina = _svc()
        svc.get_historial_salarial(EMP_A, EMPRESA_A)
        assert nomina.recibido["empresa_id"] == EMPRESA_A

    def test_consolidado_alcanza_a_cualquiera(self) -> None:
        """empresa_id=None es la vista consolidada, no un fallo de validación."""
        svc, _ = _svc()
        assert len(svc.get_historial_salarial(EMP_B, None)) == 1


# ─── Gate de sección ──────────────────────────────────────────────────────────


class TestGateDeSeccion:
    """El endpoint vive bajo Seccion.COSTOS aunque se consuma desde la ficha, que está bajo
    EMPLEADOS. Hoy ningún rol tiene una y no la otra, pero el gate va igual: los roles
    cambian y este endpoint no se vuelve a mirar."""

    def test_el_endpoint_declara_el_gate_de_costos(self) -> None:
        import routers.costos as mod
        assert mod.SECCION is Seccion.COSTOS

    def test_la_ruta_esta_montada_con_su_dependency(self) -> None:
        from fastapi.routing import APIRoute

        from main import app
        ruta = next(r for r in app.routes
                    if isinstance(r, APIRoute) and r.path.endswith("/nomina/empleado/{empleado_id}"))
        assert ruta.dependencies, "el endpoint quedó sin gate de permisos"

    @pytest.mark.parametrize("rol", ["mandos_medios", None, "rol_inventado"])
    def test_un_rol_sin_costos_no_pasa(self, rol) -> None:
        assert not puede(rol, Seccion.COSTOS, Accion.READ)

    @pytest.mark.parametrize("rol", ["admin_rrhh", "gerencia_lectura"])
    def test_los_roles_con_costos_si(self, rol: str) -> None:
        assert puede(rol, Seccion.COSTOS, Accion.READ)

    def test_no_alcanza_con_tener_empleados(self) -> None:
        """Si algún día aparece un rol con EMPLEADOS y sin COSTOS, la ficha no puede
        convertirse en la puerta de atrás a los sueldos."""
        roles_con_fuga = [r for r in ("admin_rrhh", "gerencia_lectura", "mandos_medios")
                          if puede(r, Seccion.EMPLEADOS, Accion.READ)
                          and not puede(r, Seccion.COSTOS, Accion.READ)]
        assert roles_con_fuga == []
