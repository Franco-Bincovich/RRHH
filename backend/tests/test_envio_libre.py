"""
Envío a una DIRECCIÓN ESCRITA A MANO: la regla de las variables, el formato, y que el envío
quede registrado igual que cualquier otro.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL FAKE TIENE DOS PLANTILLAS: una CON `{{variables}}` y otra SIN. Es la condición del
     archivo: con una sola, "detecta variables" y "no detecta nada" dan el mismo resultado y la
     barrera se podría borrar sin que nada rojee. Hay un guardián que verifica que las dos sean
     distintas — si alguien las iguala, ese falla primero y no las aserciones de abajo.
  2. EL MAILER CAPTURA destinatario Y cuerpo, no cuenta envíos. Contando, "salió a la dirección
     correcta" y "salió a cualquier lado" son indistinguibles.
  3. `_Log` RECUERDA a quién se le mandó y `ya_enviado` lo consulta DE VERDAD, por destinatario.
     Un fake que devolviera siempre False no podría desmentir la idempotencia del modo libre —
     que es justo la parte nueva, porque acá no hay `empleado_id` con el que preguntar.
  4. Cada barrera se prueba en sus DOS lados (con variables / sin variables · formato bueno /
     formato malo · modo puro / modo mixto). Con un solo lado, una barrera incondicional pasaría
     y dejaría la feature muerta en vez de rota.
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

import services._envio_libre as libre_mod  # noqa: E402
import services.mail_envio_service as mod  # noqa: E402
from schemas.plantillas import EnvioRequest  # noqa: E402
from services._envio_libre import (  # noqa: E402
    email_valido, normalizar, plantilla_usa_variables, validar,
)
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()

# 🔴 LAS DOS PLANTILLAS. Sin la de arriba, la barrera no se puede desmentir.
CON_VARIABLES = {"clave": "bienvenida", "contexto": "empleado",
                 "asunto": "Hola {{nombre_empleado}}", "cuerpo": "Te damos la bienvenida."}
SIN_VARIABLES = {"clave": "corte_luz", "contexto": "ninguno",
                 "asunto": "Corte de luz el viernes", "cuerpo": "El viernes no hay luz."}


class _Plantillas:
    """Devuelve la plantilla que se le haya cargado. Modela las DOS formas por construcción."""

    def __init__(self, plantilla) -> None:
        self._p = plantilla

    def find(self, clave, empresa_id=None):
        return self._p


class _Empleados:
    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(nombre="Ana", apellido="Gómez", email_corporativo="ana@k.com",
                               fecha_ingreso="2024-01-01", empresa_nombre="Karstec")


class _Log:
    """RECUERDA los envíos. Es lo único que hace verificable la idempotencia del modo libre."""

    def __init__(self) -> None:
        self.enviados: set = set()
        self.filas: list = []

    def ya_enviado(self, clave, empleado_id=None, desde=None, destinatario=None):
        return (clave, empleado_id or destinatario) in self.enviados

    def marcar(self, clave, destino):
        self.enviados.add((clave, destino))


class _Mailer:
    """Captura destinatario, cuerpo y el `empleado_id` con el que se registró cada envío."""

    def __init__(self, log: _Log) -> None:
        self._log = log
        self.envios: list = []

    def __call__(self, destinatario, asunto, cuerpo, **kw):
        self.envios.append({"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo,
                            "empleado_id": kw.get("empleado_id"),
                            "plantilla_clave": kw.get("plantilla_clave")})
        self._log.marcar(kw["plantilla_clave"], kw.get("empleado_id") or destinatario)
        return {"enviado": True, "mensaje_id": "m1"}


def _armar(monkeypatch, plantilla, log=None):
    log = log or _Log()
    mailer = _Mailer(log)
    # 🔴 SE PARCHEAN LOS DOS MÓDULOS. Cada uno importa `enviar_mail` por nombre, así que quedan
    # dos referencias distintas: parchear solo `mail_envio_service` deja al camino LIBRE llamando
    # al mailer REAL. La primera versión de este archivo hacía eso y los tests salieron a la red
    # (httpx.ConnectError) — que además es la única razón por la que se notó.
    monkeypatch.setattr(mod, "enviar_mail", mailer)
    monkeypatch.setattr(libre_mod, "enviar_mail", mailer)
    audit = SimpleNamespace(eventos=[], registrar=lambda **kw: audit.eventos.append(kw))
    svc = mod.MailEnvioService(plantillas=_Plantillas(plantilla), empleados=_Empleados(),
                               log=log, audit=audit)
    return svc, mailer, log, audit


def _pedido_libre(*direcciones) -> EnvioRequest:
    return EnvioRequest(plantilla_clave="x", empleado_ids=[], destinatarios_libres=list(direcciones))


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_trae_una_plantilla_CON_variables_y_otra_SIN() -> None:
    """Si las dos fueran iguales, todo el archivo pasaría sin comparar nada."""
    assert plantilla_usa_variables(CON_VARIABLES) is True
    assert plantilla_usa_variables(SIN_VARIABLES) is False


# ── 1. 🔴 La regla de producto ────────────────────────────────────────────────

class TestUnaPlantillaConVariablesNoVaADireccionLibre:

    def test_se_rechaza_con_un_motivo_legible(self, monkeypatch) -> None:
        svc, mailer, _, _ = _armar(monkeypatch, CON_VARIABLES)

        with pytest.raises(AppError) as exc:
            svc.enviar(_pedido_libre("ana@k.com"), EMPRESA, "u1")

        assert exc.value.code == "PLANTILLA_CON_VARIABLES" and exc.value.status_code == 422
        assert "solo se puede enviar a colaboradores" in exc.value.message
        # Lo que importa: NO salió ningún mail. Un rechazo después de mandar no sirve de nada.
        assert mailer.envios == []

    def test_una_variable_en_el_CUERPO_tambien_bloquea(self, monkeypatch) -> None:
        """El asunto y el cuerpo se miran los dos: un hueco en el cuerpo es igual de malo."""
        solo_cuerpo = {**SIN_VARIABLES, "cuerpo": "Hola {{nombre_empleado}}, ¿todo bien?"}
        svc, mailer, _, _ = _armar(monkeypatch, solo_cuerpo)

        with pytest.raises(AppError) as exc:
            svc.enviar(_pedido_libre("ana@k.com"), EMPRESA, "u1")

        assert exc.value.code == "PLANTILLA_CON_VARIABLES"
        assert mailer.envios == []

    def test_una_plantilla_SIN_variables_SI_se_puede_mandar(self, monkeypatch) -> None:
        """🔴 EL CONTRAPESO. Sin esto, una barrera que rechace SIEMPRE pasaría el test de arriba
        y dejaría la feature muerta — que es peor que el bug, porque no manda nada a nadie."""
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES)

        out = svc.enviar(_pedido_libre("ana@k.com"), EMPRESA, "u1")

        assert out.enviados == 1
        assert mailer.envios[0]["destinatario"] == "ana@k.com"

    def test_la_plantilla_CON_variables_sigue_yendo_a_EMPLEADOS(self, monkeypatch) -> None:
        """La regla acota UN modo, no rompe el otro: es el camino normal del módulo."""
        svc, mailer, _, _ = _armar(monkeypatch, CON_VARIABLES)

        out = svc.enviar(EnvioRequest(plantilla_clave="x", empleado_ids=[UUID(int=1)]),
                         EMPRESA, "u1")

        assert out.enviados == 1 and mailer.envios[0]["destinatario"] == "ana@k.com"


# ── 2. El formato lo valida el BACKEND, no solo la pantalla ───────────────────

class TestElFormatoSeValidaAca:

    # `""` NO está en la lista a propósito: un token vacío no es un typo, es una coma de más al
    # final de un pegado. `normalizar` lo descarta y el envío sigue — rechazar el lote por eso
    # sería castigar a alguien por cómo terminó de pegar la lista.
    @pytest.mark.parametrize("mala", ["ana@", "@k.com", "ana k.com", "ana@k", "ana.k.com"])
    def test_una_direccion_mal_escrita_se_rechaza(self, monkeypatch, mala) -> None:
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES)

        with pytest.raises(AppError) as exc:
            svc.enviar(_pedido_libre("bien@k.com", mala), EMPRESA, "u1")

        assert exc.value.code == "EMAIL_INVALIDO" and exc.value.status_code == 422
        # 🔴 EL LOTE ENTERO SE RECHAZA: la lista la acaba de escribir una persona y corregirla es
        # inmediato. Mandar la mitad dejaría un envío a medias imposible de razonar.
        assert mailer.envios == []

    @pytest.mark.parametrize("buena", ["ana@k.com", "ana.gomez@karstec.com.ar",
                                       "ana+rrhh@k.io", "a@b.co"])
    def test_las_bien_escritas_pasan(self, buena) -> None:
        """Contrapeso del parametrize de arriba: un validador que rechace todo lo pasaría."""
        assert email_valido(buena) is True

    def test_el_mensaje_dice_CUALES_estan_mal(self, monkeypatch) -> None:
        """Con diez direcciones pegadas, "hay direcciones inválidas" obliga a revisarlas a ojo."""
        svc, _, _, _ = _armar(monkeypatch, SIN_VARIABLES)

        with pytest.raises(AppError) as exc:
            svc.enviar(_pedido_libre("bien@k.com", "rota@", "otra@k.com"), EMPRESA, "u1")

        assert "rota@" in exc.value.message and "bien@k.com" not in exc.value.message

    def test_el_tope_de_direcciones_se_respeta(self, monkeypatch) -> None:
        svc, _, _, _ = _armar(monkeypatch, SIN_VARIABLES)

        with pytest.raises(AppError) as exc:
            svc.enviar(_pedido_libre(*[f"u{i}@k.com" for i in range(60)]), EMPRESA, "u1")

        assert exc.value.code == "DEMASIADOS_DESTINATARIOS"


class TestNormalizacion:

    def test_dedup_case_insensitive_conservando_la_primera_forma(self) -> None:
        """Pegar dos veces la misma dirección es normal; mandar dos mails iguales, no."""
        assert normalizar([" Ana@K.com ", "ana@k.com", ""]) == ["Ana@K.com"]

    def test_una_lista_repetida_manda_UN_solo_mail(self, monkeypatch) -> None:
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES)

        out = svc.enviar(_pedido_libre("ana@k.com", "ANA@k.com"), EMPRESA, "u1")

        assert out.enviados == 1 and len(mailer.envios) == 1


# ── 3. Los dos modos no se mezclan ────────────────────────────────────────────

class TestLosModosSonExcluyentes:

    def test_mandar_las_dos_cosas_juntas_se_rechaza(self, monkeypatch) -> None:
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES)
        pedido = EnvioRequest(plantilla_clave="x", empleado_ids=[UUID(int=1)],
                              destinatarios_libres=["ana@k.com"])

        with pytest.raises(AppError) as exc:
            svc.enviar(pedido, EMPRESA, "u1")

        assert exc.value.code == "ENVIO_MODO_MIXTO" and mailer.envios == []

    def test_cada_modo_por_separado_funciona(self, monkeypatch) -> None:
        """Contrapeso: sin esto, un rechazo incondicional pasaría el test de arriba."""
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES)
        assert svc.enviar(_pedido_libre("ana@k.com"), EMPRESA, "u1").enviados == 1

        svc2, mailer2, _, _ = _armar(monkeypatch, SIN_VARIABLES)
        assert svc2.enviar(EnvioRequest(plantilla_clave="x", empleado_ids=[UUID(int=1)]),
                           EMPRESA, "u1").enviados == 1


# ── 4. Queda registrado igual que cualquier otro envío ────────────────────────

class TestQuedaEnElLogYEnLaAuditoria:

    def test_el_envio_libre_se_registra_SIN_empleado_id(self, monkeypatch) -> None:
        """`mail_enviado.empleado_id` es nullable justamente para esto. El historial lo lista
        igual: su query no filtra ni agrupa por empleado."""
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES)

        svc.enviar(_pedido_libre("proveedor@otra.com"), EMPRESA, "u1")

        assert mailer.envios[0]["empleado_id"] is None
        assert mailer.envios[0]["destinatario"] == "proveedor@otra.com"
        assert mailer.envios[0]["plantilla_clave"] == "corte_luz"

    def test_sale_UN_evento_de_auditoria_por_lote(self, monkeypatch) -> None:
        """La regla del repo no cambia por el modo: un lote, un evento."""
        svc, _, _, audit = _armar(monkeypatch, SIN_VARIABLES)

        svc.enviar(_pedido_libre("a@k.com", "b@k.com", "c@k.com"), EMPRESA, "u1")

        assert len(audit.eventos) == 1
        assert audit.eventos[0]["datos_nuevos"]["enviados"] == 3

    def test_la_idempotencia_vale_TAMBIEN_para_direcciones_libres(self, monkeypatch) -> None:
        """🔴 Sin `empleado_id`, la pregunta va por destinatario. Sin esto, un lote cortado por
        presupuesto reenviaría a las direcciones que ya recibieron el mail — el daño visible
        para gente de afuera que todo este módulo existe para evitar."""
        log = _Log()
        svc, mailer, _, _ = _armar(monkeypatch, SIN_VARIABLES, log=log)
        primero = svc.enviar(_pedido_libre("ana@k.com", "beto@k.com"), EMPRESA, "u1")
        assert primero.enviados == 2

        svc2, mailer2, _, _ = _armar(monkeypatch, SIN_VARIABLES, log=log)
        segundo = svc2.enviar(_pedido_libre("ana@k.com", "beto@k.com"), EMPRESA, "u1")

        assert segundo.enviados == 0 and segundo.omitidos == 2
        assert mailer2.envios == [], "se reenvió a una dirección que ya había recibido el mail"


# ── 5. El validador, directo ──────────────────────────────────────────────────

class TestValidar:

    def test_devuelve_la_lista_normalizada_cuando_todo_esta_bien(self) -> None:
        assert validar(SIN_VARIABLES, [" a@k.com ", "b@k.com"]) == ["a@k.com", "b@k.com"]

    def test_la_barrera_de_variables_corre_ANTES_que_la_de_formato(self) -> None:
        """Con una plantilla con variables Y una dirección rota, el motivo que se muestra tiene
        que ser el que NO se puede resolver escribiendo mejor la dirección."""
        with pytest.raises(AppError) as exc:
            validar(CON_VARIABLES, ["rota@"])

        assert exc.value.code == "PLANTILLA_CON_VARIABLES"
