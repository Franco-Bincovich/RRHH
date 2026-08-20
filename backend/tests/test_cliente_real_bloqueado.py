"""
El cliente REAL de Supabase no puede correr bajo tests: falla ruidoso y dice quién lo pidió.

## Por qué existe el guard que esto cubre

La suite falsea la base **módulo por módulo** (71 archivos de test, ~172 sitios de parcheo, 22 de
ellos con una LISTA A MANO de tres o más módulos). Esa lista no puede saber que apareció un módulo
nuevo: el 20/8/2026 se movió `dar_de_baja` a `_empleado_baja_repo.py`, su módulo quedó fuera del
fixture de `test_offboarding_baja_efectiva.py`, y el test **salió a la red con el cliente real**.
Murió en `getaddrinfo failed` por casualidad — en una máquina con red y el `.env` cargado habría
escrito `estado='baja'` sobre producción con la `service_key`.

## 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR

  1. **Se usa el `supabase_admin` REAL, sin falsear.** Es el único objeto que puede desmentir al
     guard: contra un fake no hay nada que bloquear. Es seguro justamente porque el guard existe
     — si algún día se lo borrara, estos tests dejarían de rojear y **saldrían a la red**, que es
     el modo de falla que cubren. Por eso el primero verifica el mensaje y no solo que levante.

  2. **Se prueban las DOS direcciones del interruptor**: con el escape puesto NO bloquea, sin él
     SÍ. Un guard que bloqueara siempre pasaría la mitad de los tests y rompería el E2E que la
     salida de emergencia existe para permitir.

  3. **Está la contracara del falso positivo que ya se pagó**: `monkeypatch.setattr` sobre un
     atributo del proxy hace un `getattr` para guardarse el original, y con el guard en
     `__getattr__` eso rojeaba a 21 tests que estaban falseando el cliente BIEN. Sin ese test,
     mover el guard de vuelta a `__getattr__` no rompería nada acá.
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

import pytest  # noqa: E402

import integrations._cliente_real_en_tests as guard  # noqa: E402
from integrations.supabase_client import supabase_admin  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_cache(monkeypatch):
    """La decisión se cachea por proceso; acá se limpia antes y después de cada caso.

    Sin esto, el test del escape dejaría `_decision=False` cacheado y los siguientes verían un
    guard apagado — pasarían por el motivo equivocado, que es peor que fallar.
    """
    monkeypatch.setattr(guard, "_decision", None)
    yield
    guard._decision = None


class TestBajoTestsElClienteRealNoCorre:

    def test_invocar_el_cliente_real_levanta(self) -> None:
        with pytest.raises(RuntimeError):
            supabase_admin.table("empleados").select("*").execute()

    def test_el_mensaje_dice_QUIEN_lo_pidio(self) -> None:
        """El punto entero del guard: que quien lo vea sepa qué sumarle al fixture. Un
        `RuntimeError` pelado no ahorraría ni un minuto de diagnóstico."""
        with pytest.raises(RuntimeError) as exc:
            supabase_admin.table("empleados").execute()
        mensaje = str(exc.value)
        assert "tests/test_cliente_real_bloqueado.py:" in mensaje, (
            f"el mensaje no nombra el archivo que lo pidió: {mensaje}"
        )
        assert "CLIENTE REAL DE SUPABASE USADO BAJO TESTS" in mensaje
        assert "monkeypatch.setattr" in mensaje, "tiene que decir cómo se arregla"

    def test_el_mensaje_dice_QUE_se_estaba_haciendo(self) -> None:
        """La cadena de atributos distingue de un vistazo una consulta de una subida a Storage."""
        with pytest.raises(RuntimeError) as exc:
            supabase_admin.table("empleados").execute()
        assert "table" in str(exc.value)

    def test_corta_ANTES_de_tocar_la_red(self) -> None:
        """🔴 La diferencia con el estado anterior. Antes esto moría en `getaddrinfo failed`
        —o peor, escribía— y el rojo no decía nada útil. El guard tiene que cortar antes de que
        httpx intente resolver el host."""
        with pytest.raises(RuntimeError) as exc:
            supabase_admin.table("empleados").insert({"nombre": "X"}).execute()
        assert "getaddrinfo" not in str(exc.value)


class TestElInterruptorFuncionaEnLasDosDirecciones:

    def test_con_el_escape_puesto_NO_bloquea(self, monkeypatch) -> None:
        """`SUPABASE_REAL_EN_TESTS=1` existe para un E2E real contra un proyecto de prueba. Si el
        guard bloqueara igual, esa salida no serviría de nada.

        No se invoca el cliente —eso saldría a la red de verdad—: se verifica la decisión, que es
        lo único que el escape gobierna."""
        monkeypatch.setenv("SUPABASE_REAL_EN_TESTS", "1")
        monkeypatch.setattr(guard, "_decision", None)
        assert guard.bajo_tests() is False

    def test_sin_el_escape_SI_bloquea(self, monkeypatch) -> None:
        """Contracara: si `bajo_tests()` devolviera False siempre, todos los tests de arriba
        pasarían... salvo que no, saldrían a la red. Esto lo dice de frente."""
        monkeypatch.delenv("SUPABASE_REAL_EN_TESTS", raising=False)
        monkeypatch.setattr(guard, "_decision", None)
        assert guard.bajo_tests() is True

    def test_pytest_solo_ya_alcanza(self, monkeypatch) -> None:
        """🔴 La condición que NO depende de que nadie se acuerde de nada. Con `APP_ENV` en su
        default de producción, el guard tiene que seguir encendido porque pytest está importado.
        Si dependiera solo de `APP_ENV=test`, la protección estaría apagada en toda corrida que
        no exporte la variable — o sea hoy, en las dos máquinas del proyecto."""
        from config.settings import settings

        monkeypatch.setattr(settings, "app_env", "development")
        monkeypatch.delenv("SUPABASE_REAL_EN_TESTS", raising=False)
        monkeypatch.setattr(guard, "_decision", None)
        assert guard.bajo_tests() is True


class TestFalsearElClienteNoDisparaElGuard:
    """🔴 LA CONTRACARA DEL FALSO POSITIVO QUE YA SE PAGÓ, el 20/8/2026.

    La primera versión del guard vivía en `_RootProxy.__getattr__`. `monkeypatch.setattr(obj,
    name, val)` hace un `getattr(obj, name)` para guardarse el valor original **antes** de
    reemplazarlo, así que rojeaba a **21 tests de `test_usuarios.py`** que estaban falseando el
    cliente correctamente. Se movió a `_MethodProxy.__call__`: leer un atributo no es usar la
    base, invocar sí.

    Sin este test, devolver el guard a `__getattr__` no rompería nada de lo de arriba.
    """

    def test_monkeypatch_de_un_atributo_del_proxy_no_levanta(self, monkeypatch) -> None:
        monkeypatch.setattr(supabase_admin, "auth", object())

    def test_y_leer_un_atributo_tampoco(self) -> None:
        """Más directo todavía: `.table` sin invocar nada es una lectura, no un uso."""
        supabase_admin.table

    def test_pero_invocarlo_SI(self) -> None:
        """La premisa de los dos de arriba: que el guard esté encendido en este mismo proceso.
        Sin esto, los dos anteriores pasarían con el guard borrado entero."""
        with pytest.raises(RuntimeError):
            supabase_admin.table("empleados").execute()
