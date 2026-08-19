"""
La guarda de A3.3 en el import de nómina: Fecha Baja sobre un preingreso SALTEA la fila y la
REPORTA — no la da de baja, no la actualiza. Contraste: un activo con Fecha Baja sí pasa a baja.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El arnés SE IMPORTA de `test_liderazgo_es_lider` (el molde de este service: `__new__` +
colaboradores falsos, con `EmpleadoService` REAL en el medio) en vez de reescribirse. Lo único
propio es `_RepoConBajas`, y su diferencia con el `_RepoCaptura` heredado es exactamente lo que
estos tests necesitan poder desmentir: **registra las llamadas a `dar_de_baja`** (el heredado
devolvía True sin dejar rastro, así que "no se dio de baja" y "se dio de baja" eran
indistinguibles) y **`update` conserva el estado del existente** (el heredado fabricaba siempre
un activo, con lo cual el preingreso desaparecía del fake antes de llegar a la guarda).

Verificado por reversión el 19/8/2026: con la llamada a `rechazar_baja_de_preingreso` comentada
en `_procesar_fila`, rojean los tres tests del preingreso y quedan verdes los dos del activo.
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

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.empleado import EmpleadoResponse  # noqa: E402
from services._nomina_empleados_baja import rechazar_baja_de_preingreso  # noqa: E402
from tests.test_liderazgo_es_lider import (  # noqa: E402
    _COLUMNAS, _RepoCaptura, _servicio, EMPRESA_A, AREA_A,
)

_DNI = "30111222"


def _empleado_estado(estado: str) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": str(uuid4()), "nombre": "N", "apellido": "A", "email_corporativo": "a@k.com",
        "empresa_id": EMPRESA_A, "area_id": AREA_A, "roles": ["Analista"], "dni": _DNI,
        "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo", "es_lider": False,
        "fecha_ingreso": "2026-09-01", "estado": estado, "created_at": "2026-01-01T00:00:00Z",
    })


def _csv_con_baja() -> str:
    fila = {c: "" for c in _COLUMNAS}
    fila.update({
        "Apellido": "Perez", "Nombre": "Ana", "DNI": _DNI, "Organismo": "ACME",
        "Sector": "SISTEMAS", "Rol": "Analista", "Fecha Ingreso": "1/3/2024",
        "Email": "ana@k.com", "Modalidad Contratacion": "RELACION DE DEPENDENCIA",
        "Fecha Baja": "1/7/2026", "Motivo Baja": "RENUNCIA",
    })
    return ";".join(_COLUMNAS) + "\r\n" + ";".join(fila[c] for c in _COLUMNAS) + "\r\n"


class _RepoConBajas(_RepoCaptura):
    """Ver el encabezado: registra las bajas y no le cambia el estado al existente."""

    def __init__(self, existentes=None) -> None:
        super().__init__(existentes)
        self.bajas: list = []

    def dar_de_baja(self, empleado_id, fecha, empresa_id=None):
        self.bajas.append((str(empleado_id), str(fecha)))
        return True

    def update(self, id, data, empresa_id=None):
        self.updates.append(data.model_dump(exclude_none=True))
        return next((e for e in self._por_dni.values() if e.id == str(id)), None)


def _importar(estado: str):
    svc, _ = _servicio()
    repo = _RepoConBajas({_DNI: _empleado_estado(estado)})
    svc._emp_repo = repo
    svc._empleados._repo = repo  # el EmpleadoService real del arnés también escribe por acá
    return svc.importar(_csv_con_baja(), "nomina.csv"), repo


class TestPreingresoConFechaBaja:
    def test_la_fila_se_saltea_y_se_reporta_con_motivo(self) -> None:
        r, _ = _importar("preingreso")
        assert r.creados == 0 and r.actualizados == 0
        assert len(r.no_cargados) == 1
        assert "preingreso" in r.no_cargados[0].motivo
        assert "nunca ingresó" in r.no_cargados[0].motivo

    def test_no_se_da_de_baja_ni_se_actualiza(self) -> None:
        """La guarda corre ANTES de escribir: ni `dar_de_baja` ni `update` llegan a llamarse —
        sin esto, la fila quedaría "editada pero no dada de baja", el estado a medias que el
        reporte no sabe contar."""
        _, repo = _importar("preingreso")
        assert repo.bajas == []
        assert repo.updates == []

    def test_el_empleado_sigue_en_preingreso(self) -> None:
        _, repo = _importar("preingreso")
        assert repo.find_by_dni(_DNI).estado == "preingreso"


class TestActivoConFechaBaja:
    def test_el_contraste_un_activo_si_pasa_a_baja(self) -> None:
        """Sin este contraste, una guarda que rechazara TODA Fecha Baja pasaría los de arriba
        en verde — y el import histórico de bajas, que es el uso real, quedaría roto."""
        r, repo = _importar("activo")
        assert r.actualizados == 1 and r.no_cargados == []
        assert len(repo.bajas) == 1
        assert repo.bajas[0][1] == "2026-07-01"


class TestLaGuardaSola:
    def test_sin_fecha_baja_no_rechaza_ni_a_un_preingreso(self) -> None:
        """El otro contraste: la guarda mira el PAR (estado, fecha), no el estado solo. Un CSV
        mensual normal trae a los preingresos sin Fecha Baja y tiene que poder actualizarlos."""
        rechazar_baja_de_preingreso(_empleado_estado("preingreso"), None)

    def test_un_empleado_nuevo_tampoco(self) -> None:
        """`existente=None` (alta + baja en el acto = import histórico) no pasa por la guarda."""
        rechazar_baja_de_preingreso(None, "2026-07-01")

    def test_preingreso_mas_fecha_lanza_con_motivo_legible(self) -> None:
        with pytest.raises(ValueError, match="preingreso"):
            rechazar_baja_de_preingreso(_empleado_estado("preingreso"), "2026-07-01")
