"""
🔒 El envío de mails EXIGE una empresa concreta — y lo exige el ENDPOINT, no la pantalla.

`POST /api/plantillas/enviar` usaba `get_empresa_id` (Optional), a diferencia del `guardar` y el
`borrar` del mismo router. Con `None`, `PlantillaMailRepo.find` saltea la plantilla PROPIA y
resuelve la GLOBAL. Dos desenlaces, y el peligroso es el segundo:
  · sin global con esa clave → 404 PLANTILLA_NOT_FOUND. Ruidoso, tolerable.
  · 🔴 CON una global con esa clave → el mail sale con un TEXTO DISTINTO del que se ve en
    pantalla, con 200 y sin ninguna señal. Y el evento de auditoría queda con `empresa_id` NULL,
    o sea fuera del filtro por empresa de `/auditoria`.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 `_PlantillasConGlobal` MODELA LAS DOS FILAS —una PROPIA de la empresa y una GLOBAL con la
     MISMA clave y cuerpo DISTINTO— y elige según `empresa_id`, como hace el repo real. Es LA
     condición del archivo: el fake de `test_mail_envio.py` devuelve la misma plantilla siempre,
     así que con él "usó la propia" y "usó la global" son indistinguibles y **el bug no se puede
     expresar**. Que ese fake no modelara la diferencia es exactamente por qué esto vivió meses.
     Hay un test que verifica que los dos cuerpos difieran: si alguien los iguala, las aserciones
     de abajo se vuelven vacuas y ese guardián rojea primero.
  2. El mailer CAPTURA el cuerpo renderizado, no solo cuenta envíos. Contando, los dos caminos
     dan "1 enviado" y el test pasa con el texto equivocado saliendo hacia afuera.
  3. Los tests del router llaman a la FUNCIÓN REAL del endpoint con un `Request` real (molde:
     `test_reporte_area.py`), no revisan el código fuente. Un router que "recibe empresa_id" y no
     lo usa se lee igual que uno que sí — la regla del repo es seguir el parámetro hasta abajo.
  4. HAY CONTRAPESO: con empresa elegida el envío tiene que seguir funcionando. Sin ese caso, un
     endpoint que rechace SIEMPRE pasaría el test de rechazo y dejaría la feature muerta.
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

from types import SimpleNamespace  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402
from starlette.requests import Request  # noqa: E402

import routers.plantillas as router_mod  # noqa: E402
import services.mail_envio_service as svc_mod  # noqa: E402
from schemas.plantillas import EnvioRequest  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()
_IDS = [UUID(int=i) for i in range(1, 4)]


class _PlantillasConGlobal:
    """🔴 EL FAKE QUE HACE EXPRESABLE EL BUG: la MISMA clave existe dos veces, con cuerpos
    distintos, y `find` elige según `empresa_id` igual que `PlantillaMailRepo.find`."""

    PROPIA = "Bienvenida a SERVICIOS Y CONSULTORIA."
    GLOBAL = "Bienvenida a la empresa."

    def find(self, clave, empresa_id=None):
        return {"clave": clave, "contexto": "empleado", "asunto": "Hola",
                "cuerpo": self.PROPIA if empresa_id else self.GLOBAL}


class _Empleados:
    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(nombre="Ana", apellido="Gómez", email_corporativo="ana@k.com",
                               fecha_ingreso="2024-01-01", empresa_nombre="Karstec")


class _Log:
    def ya_enviado(self, clave, empleado_id, desde=None):
        return False


class _Audit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw):
        self.eventos.append(kw)


class _MailerQueCaptura:
    """Guarda el CUERPO de cada mail. Contar envíos no alcanza: los dos caminos mandan uno."""

    def __init__(self) -> None:
        self.cuerpos: list = []

    def __call__(self, destinatario, asunto, cuerpo, **kw):
        self.cuerpos.append(cuerpo)
        return {"enviado": True, "mensaje_id": "m1"}


def _armar(monkeypatch):
    mailer = _MailerQueCaptura()
    monkeypatch.setattr(svc_mod, "enviar_mail", mailer)
    audit = _Audit()
    svc = svc_mod.MailEnvioService(plantillas=_PlantillasConGlobal(), empleados=_Empleados(),
                                   log=_Log(), audit=audit)
    return svc, mailer, audit


def _pedido() -> EnvioRequest:
    return EnvioRequest(plantilla_clave="bienvenida", empleado_ids=_IDS[:1])


def _request(empresa_id, ip: str) -> Request:
    """Request real y no `SimpleNamespace`: `enviar` está decorado con el rate limiter, que
    necesita un Request de starlette para leer la IP. Molde: `test_reporte_area.py`.

    IP distinta por test: la franja es 20/hora compartida y el store es por proceso, así que con
    una sola IP los tests se contaminarían entre sí a medida que se sumen casos."""
    req = Request({"type": "http", "path": "/api/plantillas/enviar", "headers": [],
                   "client": (ip, 1)})
    req.state.user = {"id": "u1"}
    req.state.empresa_id = empresa_id
    return req


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_modela_DOS_plantillas_distintas() -> None:
    """Si los dos cuerpos fueran iguales, todo lo de abajo pasaría sin comparar nada: "usó la
    propia" y "usó la global" darían el mismo resultado. Es la falla que este archivo persigue,
    aplicada a su propio fake."""
    assert _PlantillasConGlobal.PROPIA != _PlantillasConGlobal.GLOBAL


# ── 1. Por qué importa: sin empresa, sale OTRO texto ──────────────────────────

class TestSinEmpresaSaldriaLaGlobal:
    """El daño concreto, medido en el service. Es lo que el endpoint tiene que impedir."""

    def test_con_empresa_sale_la_plantilla_PROPIA(self, monkeypatch) -> None:
        svc, mailer, _ = _armar(monkeypatch)

        svc.enviar(_pedido(), EMPRESA, "u1")

        assert mailer.cuerpos == [_PlantillasConGlobal.PROPIA]

    def test_sin_empresa_sale_la_GLOBAL_sin_ningun_error(self, monkeypatch) -> None:
        """200, mail entregado, y el texto no es el que la pantalla mostraba. Este test NO afirma
        que esté bien: documenta por qué el endpoint no puede dejar pasar `None`."""
        svc, mailer, _ = _armar(monkeypatch)

        out = svc.enviar(_pedido(), None, "u1")

        assert out.enviados == 1 and out.fallidos == []
        assert mailer.cuerpos == [_PlantillasConGlobal.GLOBAL]

    def test_y_el_evento_de_auditoria_queda_sin_empresa(self, monkeypatch) -> None:
        """El otro daño: con `empresa_id` NULL el evento se cae del filtro por empresa de
        `/auditoria`, así que el envío es invisible para quien audita esa empresa."""
        svc, _, audit = _armar(monkeypatch)

        svc.enviar(_pedido(), None, "u1")

        assert audit.eventos[0]["empresa_id"] is None

    def test_con_empresa_el_evento_SI_la_lleva(self, monkeypatch) -> None:
        """Contrapeso: sin esto, "queda sin empresa" pasaría con el campo siempre en None."""
        svc, _, audit = _armar(monkeypatch)

        svc.enviar(_pedido(), EMPRESA, "u1")

        assert audit.eventos[0]["empresa_id"] == str(EMPRESA)


# ── 2. Lo rechaza el ENDPOINT, no la pantalla ─────────────────────────────────

class TestElEndpointExigeEmpresa:

    async def test_sin_empresa_el_endpoint_rechaza_con_400(self, monkeypatch) -> None:
        llamadas: list = []
        monkeypatch.setattr(router_mod, "MailEnvioService",
                            lambda: SimpleNamespace(enviar=lambda *a, **k: llamadas.append(a)))

        with pytest.raises(AppError) as exc:
            await router_mod.enviar(body=_pedido(), request=_request(None, "10.0.0.1"))

        assert exc.value.code == "EMPRESA_ID_REQUIRED" and exc.value.status_code == 400
        # 🔴 Lo importante NO es el status: es que el service NUNCA se llamó. Un endpoint que
        # dejara pasar el None y fallara más abajo daría otro error, pero el mail ya habría salido.
        assert llamadas == [], "el envío llegó al service con la empresa sin resolver"

    async def test_con_empresa_elegida_el_envio_SIGUE_funcionando(self, monkeypatch) -> None:
        """El contrapeso. Sin él, un endpoint que rechace siempre pasa el test de arriba y deja
        la feature muerta — que es peor que el bug, porque no manda nada a nadie."""
        recibido: dict = {}

        def _fake_enviar(body, empresa_id, usuario_id):
            recibido.update(body=body, empresa_id=empresa_id, usuario_id=usuario_id)
            return "OK"

        monkeypatch.setattr(router_mod, "MailEnvioService",
                            lambda: SimpleNamespace(enviar=_fake_enviar))

        out = await router_mod.enviar(body=_pedido(), request=_request(str(EMPRESA), "10.0.0.2"))

        assert out == "OK"
        # Y llega la empresa REAL, no None: seguir el parámetro hasta abajo es la regla del repo.
        assert recibido["empresa_id"] == EMPRESA
        assert recibido["usuario_id"] == "u1"

    async def test_una_empresa_distinta_viaja_tal_cual(self, monkeypatch) -> None:
        """Sin esto, "llega la empresa" podría estar pasando con un valor hardcodeado."""
        otra = uuid4()
        recibido: dict = {}
        monkeypatch.setattr(router_mod, "MailEnvioService", lambda: SimpleNamespace(
            enviar=lambda body, empresa_id, usuario_id: recibido.update(e=empresa_id)))

        await router_mod.enviar(body=_pedido(), request=_request(str(otra), "10.0.0.3"))

        assert recibido["e"] == otra


# ── 3. El mensaje es para RRHH, no para un dev ────────────────────────────────

class TestElErrorEsAccionable:

    async def test_dice_que_hay_que_elegir_una_empresa_en_el_selector(self, monkeypatch) -> None:
        monkeypatch.setattr(router_mod, "MailEnvioService",
                            lambda: SimpleNamespace(enviar=lambda *a, **k: None))

        with pytest.raises(AppError) as exc:
            await router_mod.enviar(body=_pedido(), request=_request(None, "10.0.0.4"))

        mensaje = exc.value.message
        assert "elegí una empresa" in mensaje.lower()
        assert "selector" in mensaje.lower()

    async def test_y_NO_le_muestra_el_nombre_del_parametro(self, monkeypatch) -> None:
        """El front muestra el `message` tal cual. "empresa_id requerido para esta operación" es
        jerga de backend en una pantalla de RRHH: quien lo lee no sabe que eso es el sidebar.
        Sin este caso, el de arriba pasaría con la jerga vieja pegada al mensaje nuevo."""
        monkeypatch.setattr(router_mod, "MailEnvioService",
                            lambda: SimpleNamespace(enviar=lambda *a, **k: None))

        with pytest.raises(AppError) as exc:
            await router_mod.enviar(body=_pedido(), request=_request(None, "10.0.0.5"))

        assert "empresa_id" not in exc.value.message
        # El CODE sí sigue siendo el mismo: es contrato, no texto para leer.
        assert exc.value.code == "EMPRESA_ID_REQUIRED"


# ── 4. El router es COHERENTE con sus hermanos ────────────────────────────────

def test_los_tres_endpoints_que_escriben_exigen_empresa() -> None:
    """`guardar`, `borrar` y `enviar` resuelven la empresa igual. La divergencia de `enviar` fue
    el bug, y era invisible leyendo el endpoint solo: se veía al comparar con los hermanos."""
    import inspect

    fuente = inspect.getsource(router_mod)
    for nombre in ("guardar", "borrar", "enviar"):
        cuerpo = fuente.split(f"async def {nombre}(")[1].split("@router")[0]
        assert "require_empresa_id(request)" in cuerpo, f"{nombre} no exige empresa"
        assert "get_empresa_id(request)" not in cuerpo, f"{nombre} volvió al Optional"
