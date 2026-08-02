"""
El envío: presupuesto de tiempo, reporte parcial e IDEMPOTENCIA — sin red.

  1. 🔴 El reintento NO manda dos veces. El peor caso no es que tarde: es mandar 30, morir en el
     timeout de Vercel, y que el reintento mande esos 30 DE NUEVO — daño visible para 30
     personas de afuera.
  2. El presupuesto corta ENTRE mails y reporta lo que quedó, con reloj INYECTADO.
  3. Un fallo puntual no tumba el lote.
  4. La auditoría es UN evento por lote, no uno por mail.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_Log` RECUERDA a quién se le mandó y `ya_enviado` lo consulta de verdad. Un fake que
    devolviera siempre False no podría desmentir la idempotencia: el test pasaría con el chequeo
    puesto o sacado, que es el caso #1 de la regla del repo.
  · EL RELOJ ES INYECTADO, no un `sleep`. Un test que durmiera de verdad sería lento y —peor—
    dependería de la velocidad de la máquina: en un CI lento cortaría en otro mail y sería
    flakeante. Con reloj falso, en qué mail corta ES parte de la aserción.
  · `_Mailer` cuenta los envíos y falla SOLO para un destinatario elegido: sin eso, "no tumbó el
    lote" y "no falló nada" serían indistinguibles.
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

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import services.mail_envio_service as mod
from schemas.plantillas import EnvioRequest
from services._lote_mails import LoteMails
from utils.errors import AppError

EMPRESA = uuid4()
_IDS = [UUID(int=i) for i in range(1, 11)]


class _RelojFalso:
    """La PRIMERA lectura da 0 (es la línea de base de LoteMails) y cada siguiente avanza `paso`.

    Sin esa primera lectura sin avance, "1 s por mail" daría uno menos que lo que dice el nombre
    y el cálculo esperado del test sería un off-by-one difícil de leer. Molde: el reloj de
    test_nomina_presupuesto.py, que resuelve lo mismo para el import."""

    def __init__(self, paso: float = 1.0) -> None:
        self.paso, self.ahora, self._primera = paso, 0.0, True

    def __call__(self) -> float:
        if self._primera:
            self._primera = False
            return 0.0
        valor = self.ahora
        self.ahora += self.paso
        return valor


class _Plantillas:
    def find(self, clave, empresa_id=None):
        return {"clave": clave, "contexto": "empleado", "asunto": "Hola {{nombre_empleado}}",
                "cuerpo": "Bienvenida a {{empresa_nombre}}."}


class _Empleados:
    """Todos con email, salvo el que se pida sin él — para probar el fallo por dato faltante."""

    def __init__(self, sin_email=()) -> None:
        self._sin_email = {str(e) for e in sin_email}

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(
            nombre="Ana", apellido="Gómez",
            email_corporativo=None if str(id) in self._sin_email else f"{str(id)[-4:]}@k.com",
            fecha_ingreso="2024-01-01", empresa_nombre="Karstec")


class _Log:
    """RECUERDA a quién se le mandó. Es lo único que hace verificable la idempotencia."""

    def __init__(self) -> None:
        self.enviados: set = set()

    def ya_enviado(self, clave, empleado_id, desde=None):
        return (clave, str(empleado_id)) in self.enviados

    def marcar(self, clave, empleado_id):
        self.enviados.add((clave, str(empleado_id)))


class _Audit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw):
        self.eventos.append(kw)


class _Mailer:
    """Reemplaza al punto único. Cuenta los envíos y falla solo para un destinatario elegido."""

    def __init__(self, log: _Log, falla_en=None) -> None:
        self._log, self._falla_en = log, falla_en
        self.enviados: list = []

    def __call__(self, destinatario, asunto, cuerpo, **kw):
        if self._falla_en and destinatario == self._falla_en:
            raise AppError("Gmail rechazó el envío", "MAIL_ERROR_PROVEEDOR", 502)
        self.enviados.append(destinatario)
        self._log.marcar(kw["plantilla_clave"], kw["empleado_id"])
        return {"enviado": True, "mensaje_id": "m1"}


def _armar(monkeypatch, *, falla_en=None, sin_email=(), log=None):
    log = log or _Log()
    mailer = _Mailer(log, falla_en)
    monkeypatch.setattr(mod, "enviar_mail", mailer)
    audit = _Audit()
    svc = mod.MailEnvioService(plantillas=_Plantillas(), empleados=_Empleados(sin_email),
                               log=log, audit=audit)
    return svc, mailer, log, audit


def _pedido(n: int = 3) -> EnvioRequest:
    return EnvioRequest(plantilla_clave="bienvenida", empleado_ids=_IDS[:n])


# ── 1. 🔴 IDEMPOTENCIA ────────────────────────────────────────────────────────

class TestElReintentoNoMandaDosVeces:
    def test_reintentar_el_mismo_lote_no_reenvia(self, monkeypatch) -> None:
        """Para que falle: sacar el chequeo de `ya_enviado` en `_uno`."""
        svc, mailer, log, _ = _armar(monkeypatch)
        primero = svc.enviar(_pedido(3), EMPRESA, "u1")
        assert primero.enviados == 3

        segundo = svc.enviar(_pedido(3), EMPRESA, "u1")
        assert segundo.enviados == 0 and segundo.omitidos == 3
        assert len(mailer.enviados) == 3, "se reenvió a alguien que ya había recibido el mail"

    def test_un_lote_cortado_se_completa_al_reintentar(self, monkeypatch) -> None:
        """🔴 EL ESCENARIO COMPLETO, que es el motivo de todo esto: el primer intento manda 3 de
        10 y muere por presupuesto; el reintento manda los 7 que faltan y NINGUNO de los 3."""
        svc, mailer, log, _ = _armar(monkeypatch)
        corte = svc.enviar(_pedido(10), EMPRESA, "u1",
                           lote=LoteMails(presupuesto=3, reloj=_RelojFalso(1.0)))
        assert corte.enviados == 3 and corte.parcial is True and corte.sin_procesar == 7

        resto = svc.enviar(_pedido(10), EMPRESA, "u1")
        assert resto.enviados == 7 and resto.omitidos == 3
        assert len(mailer.enviados) == 10 and len(set(mailer.enviados)) == 10

    def test_los_omitidos_se_cuentan_aparte_de_los_enviados(self, monkeypatch) -> None:
        """Sin este conteo, un reintento diría "0 enviados" y parecería que no hizo nada."""
        svc, _, _, _ = _armar(monkeypatch)
        svc.enviar(_pedido(2), EMPRESA, "u1")
        out = svc.enviar(_pedido(3), EMPRESA, "u1")
        assert (out.enviados, out.omitidos) == (1, 2)

    def test_un_fallido_NO_bloquea_el_reintento(self, monkeypatch) -> None:
        """Solo los `estado='enviado'` cuentan para la idempotencia: reintentar lo que falló es
        exactamente lo que se quiere."""
        log = _Log()
        svc, _, _, _ = _armar(monkeypatch, falla_en="0002@k.com", log=log)
        primero = svc.enviar(_pedido(2), EMPRESA, "u1")
        assert primero.enviados == 1 and len(primero.fallidos) == 1

        svc2, mailer2, _, _ = _armar(monkeypatch, log=log)
        segundo = svc2.enviar(_pedido(2), EMPRESA, "u1")
        assert segundo.enviados == 1 and segundo.omitidos == 1


# ── 2. El presupuesto de tiempo ───────────────────────────────────────────────

class TestElPresupuesto:
    def test_corta_entre_mails_y_dice_cuantos_quedaron(self, monkeypatch) -> None:
        svc, mailer, _, _ = _armar(monkeypatch)
        out = svc.enviar(_pedido(10), EMPRESA, "u1",
                         lote=LoteMails(presupuesto=4, reloj=_RelojFalso(1.0)))
        assert out.enviados == 4 and out.sin_procesar == 6 and out.parcial is True
        assert len(mailer.enviados) == 4, "se mandó un mail después del corte"

    def test_un_lote_que_entra_no_se_marca_parcial(self, monkeypatch) -> None:
        """El contrapeso: si esto fallara, todo envío diría 'parcial' y el aviso perdería sentido."""
        svc, _, _, _ = _armar(monkeypatch)
        out = svc.enviar(_pedido(3), EMPRESA, "u1",
                         lote=LoteMails(presupuesto=99, reloj=_RelojFalso(1.0)))
        assert out.parcial is False and out.sin_procesar == 0 and out.enviados == 3

    def test_presupuesto_cero_significa_SIN_limite(self, monkeypatch) -> None:
        """Una configuración en 0 degrada al comportamiento previo, no corta en el primero."""
        svc, _, _, _ = _armar(monkeypatch)
        out = svc.enviar(_pedido(10), EMPRESA, "u1",
                         lote=LoteMails(presupuesto=0, reloj=_RelojFalso(5.0)))
        assert out.enviados == 10 and out.parcial is False

    def test_el_corte_no_parte_un_mail_al_medio(self, monkeypatch) -> None:
        """El margen se chequea ANTES de cada mail. Un mail mandado y no registrado haría que el
        reintento lo mande de nuevo: el corte tiene que caer entre dos, nunca adentro de uno."""
        svc, mailer, log, _ = _armar(monkeypatch)
        out = svc.enviar(_pedido(10), EMPRESA, "u1",
                         lote=LoteMails(presupuesto=2, reloj=_RelojFalso(1.0)))
        assert out.enviados == len(mailer.enviados) == len(log.enviados)


# ── 3. Un fallo puntual no tumba el lote ──────────────────────────────────────

class TestBestEffortPorDestinatario:
    def test_un_error_del_proveedor_no_corta_los_demas(self, monkeypatch) -> None:
        svc, mailer, _, _ = _armar(monkeypatch, falla_en="0002@k.com")
        out = svc.enviar(_pedido(3), EMPRESA, "u1")
        assert out.enviados == 2 and len(out.fallidos) == 1
        assert out.fallidos[0]["destinatario"] == "0002@k.com"

    def test_un_empleado_sin_email_se_reporta_y_sigue(self, monkeypatch) -> None:
        """Castigar a los otros 49 por un dato faltante de uno sería la peor opción."""
        svc, _, _, _ = _armar(monkeypatch, sin_email=[_IDS[1]])
        out = svc.enviar(_pedido(3), EMPRESA, "u1")
        assert out.enviados == 2 and "email corporativo" in out.fallidos[0]["motivo"]

    def test_una_plantilla_inexistente_si_corta(self, monkeypatch) -> None:
        """Acá sí: sin plantilla no hay nada que mandar a nadie."""
        svc, _, _, _ = _armar(monkeypatch)
        svc._plantillas = SimpleNamespace(find=lambda c, e=None: None)
        with pytest.raises(AppError) as exc:
            svc.enviar(_pedido(2), EMPRESA, "u1")
        assert exc.value.code == "PLANTILLA_NOT_FOUND"


# ── 4. Auditoría: UN evento por lote ──────────────────────────────────────────

class TestAuditoriaPorLote:
    def test_un_envio_a_diez_genera_UN_evento(self, monkeypatch) -> None:
        """Regla propia del repo. El detalle fila por fila ya vive en `mail_enviado`."""
        svc, _, _, audit = _armar(monkeypatch)
        svc.enviar(_pedido(10), EMPRESA, "u1")
        assert len(audit.eventos) == 1
        assert audit.eventos[0]["datos_nuevos"]["enviados"] == 10

    def test_el_registro_id_es_un_uuid_no_un_literal(self, monkeypatch) -> None:
        """Un literal en esa columna hace fallar el insert, `AuditService` se traga el error y el
        evento desaparece en silencio. Ya pasó con el import de nómina."""
        svc, _, _, audit = _armar(monkeypatch)
        svc.enviar(_pedido(1), EMPRESA, "u1")
        UUID(audit.eventos[0]["registro_id"])

    def test_el_evento_sale_TAMBIEN_en_el_corte_parcial(self, monkeypatch) -> None:
        """Si solo se emitiera al terminar, un corte dejaría N mails enviados sin una línea de
        auditoría — justo el caso en que más importa saber qué salió."""
        svc, _, _, audit = _armar(monkeypatch)
        svc.enviar(_pedido(10), EMPRESA, "u1",
                   lote=LoteMails(presupuesto=2, reloj=_RelojFalso(1.0)))
        assert len(audit.eventos) == 1
        assert audit.eventos[0]["datos_nuevos"]["parcial"] is True
