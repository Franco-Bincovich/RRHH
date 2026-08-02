"""
Permisos de plantillas de mail: quién puede leer y quién editar.

El criterio es el MISMO que las reglas de negocio (`Seccion.CONFIGURACION`), y por el mismo
motivo: una plantilla de mail es una regla de cómo opera la empresa, no un dato operativo. Se
verifica contra la matriz REAL de `utils.permisos.puede`, no contra una copia.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · Se llama a `puede()` con la sección REAL que usa el router (`routers/plantillas.SECCION`),
    no con el string "configuracion" escrito a mano. Si alguien cambiara el gate del router a
    otra sección, estos tests lo verían; con el literal, no.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

import pytest

from routers.plantillas import SECCION
from utils.permisos import Seccion, puede


def test_la_seccion_del_router_es_configuracion() -> None:
    """No se creó una Seccion nueva: sumarla obligaría a tocar el espejo del front y el sidebar
    para algo que se toca dos veces al año."""
    assert SECCION is Seccion.CONFIGURACION


class TestQuienPuedeQue:
    def test_admin_rrhh_lee_y_edita(self) -> None:
        assert puede("admin_rrhh", SECCION, "read") and puede("admin_rrhh", SECCION, "write")

    def test_gerencia_lectura_LEE_pero_no_edita(self) -> None:
        """🔴 Leer sí, y es deliberado: quien puede ver todos los reportes debería poder ver con
        qué texto se comunica la empresa. Escribir no."""
        assert puede("gerencia_lectura", SECCION, "read") is True
        assert puede("gerencia_lectura", SECCION, "write") is False

    def test_mandos_medios_no_accede_ni_para_leer(self) -> None:
        """Solo llega a VACACIONES y AUSENCIAS. Las plantillas son de la empresa, no de su equipo."""
        assert puede("mandos_medios", SECCION, "read") is False
        assert puede("mandos_medios", SECCION, "write") is False

    @pytest.mark.parametrize("rol", ["rol_inventado", None, "", "ADMIN_RRHH"])
    def test_un_rol_desconocido_es_fail_closed(self, rol) -> None:
        assert puede(rol, SECCION, "read") is False and puede(rol, SECCION, "write") is False


def test_el_preview_exige_ademas_leer_empleados() -> None:
    """El preview con datos reales LEE un empleado: quien puede editar plantillas pero no ver
    empleados no debe sacar datos por esa puerta. mandos_medios no tiene ninguna de las dos."""
    import inspect

    import routers.plantillas as mod
    fuente = inspect.getsource(mod)
    assert "_VER_EMPLEADOS" in fuente
    assert "dependencies=[_READ, _VER_EMPLEADOS]" in fuente


def test_el_envio_exige_escritura() -> None:
    """Mandar mail a nombre de la empresa es una escritura, aunque no cambie una fila propia."""
    import inspect

    import routers.plantillas as mod
    envio = inspect.getsource(mod).split('@router.post("/enviar"')[1]
    assert "_WRITE" in envio.split("async def")[0]
