"""
FASE 6: los mails que no matchearon, y su asignación a mano.

## 🔴 EL FAKE TIENE UN MAIL YA PROCESADO Y OTRO NO

Es la decisión que hace que el test del salteo pruebe algo. Con un solo mail, "saltea los ya
procesados" y "trae todo" devuelven listas que no se distinguen: una de largo 0 y otra de largo 1
son consistentes con las dos implementaciones si no hay con qué comparar. Con dos —uno con
candidato y otro sin— la lista correcta tiene exactamente uno y es el que corresponde.

Y el fake de Gmail **cuenta las llamadas**: el diseño se apoya en que los ya procesados se
saltean ANTES de tocar la red. Si el salteo se hiciera después de traer el mensaje, el resultado
sería el mismo y el costo el doble — por eso se afirma sobre `mensajes_pedidos`, no solo sobre la
salida.

## Los otros fakes

  · `_VacanteRepo` tiene DOS vacantes de DOS empresas: sin eso, "la empresa sale de la vacante
    elegida" y "sale de una constante" serían lo mismo.
  · `_CandidatoRepo` guarda lo que recibe, así que las aserciones miran lo que el flujo escribió
    y no un objeto prefabricado.
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

import base64  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from services.cv_pendientes_service import CvPendientesService  # noqa: E402
from utils.errors import AppError  # noqa: E402
from utils.files import MAX_SIZE_CV  # noqa: E402

E1, E2 = str(uuid4()), str(uuid4())
V1, V2 = str(uuid4()), str(uuid4())
CV = b"%PDF-1.4 cv"


def _b64url(d: bytes) -> str:
    return base64.urlsafe_b64encode(d).decode().rstrip("=")


def _parte(filename, mime, att_id, size=1024) -> dict:
    return {"filename": filename, "mimeType": mime,
            "body": {"size": size, "attachmentId": att_id}}


def _mensaje(mid, asunto, remitente="Ana Pérez <ana@x.com>", partes=None, fecha="Mon, 3 Aug 2026") -> dict:
    return {"id": mid, "payload": {
        "mimeType": "multipart/mixed", "filename": "", "body": {},
        "headers": [{"name": "Subject", "value": asunto},
                    {"name": "From", "value": remitente},
                    {"name": "Date", "value": fecha}],
        "parts": [{"mimeType": "multipart/alternative", "filename": "", "body": {},
                   "parts": [{"filename": "", "mimeType": "text/plain", "body": {"size": 5}}]},
                  *(partes or [])]}}


class _VacanteRepo:
    """DOS vacantes, códigos distintos, EMPRESAS distintas."""

    def find_by_codigo(self, codigo):
        m = {"VAC-0001": (V1, E1), "VAC-0002": (V2, E2)}
        if codigo.upper() not in m:
            return None
        vid, emp = m[codigo.upper()]
        return SimpleNamespace(id=vid, empresa_id=emp, codigo=codigo.upper(), titulo="Analista")

    def find_by_id(self, vid, empresa_id=None):
        m = {V1: E1, V2: E2}
        emp = m.get(str(vid))
        if not emp or (empresa_id and str(emp) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(vid), empresa_id=emp, titulo="Analista")


class _CandidatoRepo:
    def __init__(self, procesados=None) -> None:
        self.creados: list = []
        self.cvs: dict = {}
        self._procesados = set(procesados or [])

    def message_ids_procesados(self, ids) -> set:
        return {i for i in ids if i in self._procesados}

    def existe_cv_de_gmail(self, *a) -> bool:
        return False

    def save_candidato(self, vacante_id, data, empresa_id, origen=None):
        c = SimpleNamespace(id=f"cand-{len(self.creados) + 1}", vacante_id=vacante_id,
                            empresa_id=empresa_id, nombre=data.nombre, email=data.email,
                            **(origen or {}))
        self.creados.append(c)
        return c

    def set_cv(self, cid, path) -> None:
        self.cvs[cid] = path


class _CvService:
    def validar(self, contenido, filename, mime) -> None:
        if not filename.lower().endswith((".pdf", ".doc", ".docx")):
            raise AppError("Formato no permitido", "INVALID_CV_FORMAT", 400)

    def subir(self, empresa_id, cid, contenido, filename, mime) -> str:
        return f"{empresa_id}/{cid}/{filename}"


class _Gmail:
    """Service de Gmail falso que CUENTA cuántos mensajes se pidieron."""

    def __init__(self, mensajes: list) -> None:
        self._m = {m["id"]: m for m in mensajes}
        self.mensajes_pedidos: list = []

    def token(self):
        return "tok"

    def ids_con_adjunto(self, client, token):
        return list(self._m)

    def mensaje_completo(self, client, token, mid):
        self.mensajes_pedidos.append(mid)
        return self._m[mid]


class _Client:
    def get(self, url, **k):
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"data": _b64url(CV)})


def _svc(mensajes, candidatos=None, gmail=None):
    g = gmail or _Gmail(mensajes)
    return CvPendientesService(gmail=g, vacante_repo=_VacanteRepo(),
                               candidato_repo=candidatos or _CandidatoRepo(),
                               cv_service=_CvService(),
                               audit=SimpleNamespace(registrar=lambda **k: None)), g


# ── 1. La lectura saltea lo ya procesado ──────────────────────────────────────

class TestSalteoDeProcesados:

    def _mensajes(self) -> list:
        return [_mensaje("ya", "sin codigo", partes=[_parte("cv.pdf", "application/pdf", "a1")]),
                _mensaje("nuevo", "tampoco", partes=[_parte("cv.pdf", "application/pdf", "a2")])]

    def test_el_ya_procesado_no_aparece(self) -> None:
        """🔴 EL TEST DEL ENUNCIADO.

        ¿Qué tendría que ser distinto en el fake para que falle? Que hubiera UN SOLO mail: ahí
        "saltea los procesados" y "trae todo" darían listas indistinguibles, porque no habría con
        qué comparar. Con dos, la lista correcta tiene exactamente el que no se procesó.
        """
        svc, _ = _svc(self._mensajes(), candidatos=_CandidatoRepo(procesados={"ya"}))
        assert [m.message_id for m in svc.pendientes(cliente=_Client())] == ["nuevo"]

    def test_el_salteo_ocurre_ANTES_de_pedir_el_mensaje(self) -> None:
        """El diseño se apoya en esto: sin el salteo previo habría que BAJAR los adjuntos de cada
        mail ya resuelto para descubrir que ya estaba. Se afirma sobre las llamadas, no sobre la
        salida — un salteo posterior daría la misma lista con el doble de costo."""
        svc, gmail = _svc(self._mensajes(), candidatos=_CandidatoRepo(procesados={"ya"}))
        svc.pendientes(cliente=_Client())
        assert gmail.mensajes_pedidos == ["nuevo"], "se pidió un mail ya procesado"

    def test_sin_procesados_vienen_los_dos(self) -> None:
        """El control: con el mismo fake y sin nada procesado, la lista trae los dos."""
        svc, _ = _svc(self._mensajes(), candidatos=_CandidatoRepo())
        assert len(svc.pendientes(cliente=_Client())) == 2

    def test_un_mail_que_SI_matchea_no_es_pendiente(self) -> None:
        """La pantalla muestra lo que quedó afuera, no todo lo que hay en la casilla."""
        svc, _ = _svc([_mensaje("m1", "[VAC-0001] cv",
                                partes=[_parte("cv.pdf", "application/pdf", "a1")])])
        assert svc.pendientes(cliente=_Client()) == []


# ── 2. Lo que la pantalla muestra ─────────────────────────────────────────────

class TestFilaDelPendiente:

    def test_cuenta_los_adjuntos_validos_SIN_bajarlos(self) -> None:
        """La firma de imagen no cuenta, el CV sí — y no se descarga ni uno.

        ¿Qué tendría que ser distinto para que falle? Que `_Client.get` se llamara: el fake de
        red está, pero si el conteo bajara los archivos este test no lo notaría. Por eso también
        se afirma que el service NO pidió nada más allá del mensaje."""
        svc, gmail = _svc([_mensaje("m1", "sin codigo", partes=[
            _parte("cv.pdf", "application/pdf", "a1"),
            _parte("firma.png", "image/png", "a2")])])
        fila = svc.pendientes(cliente=_Client())[0]
        assert fila.adjuntos_validos == 1 and fila.nombres_adjuntos == ["cv.pdf"]
        assert gmail.mensajes_pedidos == ["m1"]

    def test_un_adjunto_demasiado_grande_no_cuenta(self) -> None:
        """Mismo criterio que `cv_service.validar`, pero sobre el `body.size` declarado."""
        svc, _ = _svc([_mensaje("m1", "sin codigo", partes=[
            _parte("enorme.pdf", "application/pdf", "a1", size=MAX_SIZE_CV + 1)])])
        assert svc.pendientes(cliente=_Client())[0].adjuntos_validos == 0

    @pytest.mark.parametrize("asunto,motivo", [
        ("mando mi cv", "sin_codigo"),
        ("[VAC-0001] y [VAC-0002]", "codigo_ambiguo"),
        ("[VAC-9999]", "vacante_desconocida"),
    ], ids=["sin_codigo", "ambiguo", "desconocida"])
    def test_el_motivo_es_el_mismo_que_calcula_la_ingesta(self, asunto, motivo) -> None:
        """Calcularlo con otro criterio haría que la pantalla y la corrida automática dijeran
        cosas distintas del mismo mail."""
        svc, _ = _svc([_mensaje("m1", asunto, partes=[_parte("cv.pdf", "application/pdf", "a1")])])
        assert svc.pendientes(cliente=_Client())[0].motivo == motivo

    def test_trae_remitente_asunto_y_fecha(self) -> None:
        svc, _ = _svc([_mensaje("m1", "hola", remitente="Luis <l@x.com>", fecha="Tue, 4 Aug 2026",
                                partes=[_parte("cv.pdf", "application/pdf", "a1")])])
        f = svc.pendientes(cliente=_Client())[0]
        assert (f.remitente, f.asunto, f.fecha) == ("Luis <l@x.com>", "hola", "Tue, 4 Aug 2026")


# ── 3. La asignación ──────────────────────────────────────────────────────────

class TestAsignar:

    def test_crea_el_candidato_con_la_empresa_de_la_VACANTE_ELEGIDA(self) -> None:
        """🔴 No la del header. Es la única fuente posible: un mail sin match no aporta empresa,
        que es exactamente por qué la ingesta no creaba nada.

        ¿Qué tendría que ser distinto en el fake para que falle? Que las dos vacantes fueran de
        la misma empresa: ahí "sale de la vacante" y "sale del header" darían lo mismo.
        """
        repo = _CandidatoRepo()
        svc, _ = _svc([_mensaje("m1", "sin codigo",
                                partes=[_parte("cv.pdf", "application/pdf", "a1")])],
                      candidatos=repo)
        # El header dice E1; la vacante elegida es de E2.
        r = svc.asignar_mail("m1", V2, empresa_id=None, cliente=_Client())
        assert len(repo.creados) == 1
        assert repo.creados[0].empresa_id == E2 and repo.creados[0].vacante_id == V2
        assert r.candidatos_creados == ["cand-1"]

    def test_marca_la_procedencia_para_que_no_vuelva_a_aparecer(self) -> None:
        """Es lo que hace que el mail desaparezca solo de la lista: sin `gmail_message_id`, la
        lectura siguiente no lo podría saltear y el pendiente reaparecería para siempre."""
        repo = _CandidatoRepo()
        svc, _ = _svc([_mensaje("m1", "sin codigo",
                                partes=[_parte("cv.pdf", "application/pdf", "a1")])],
                      candidatos=repo)
        svc.asignar_mail("m1", V1, cliente=_Client())
        assert repo.creados[0].gmail_message_id == "m1"
        assert repo.creados[0].fuente == "gmail"

    def test_un_mail_con_dos_cvs_crea_dos_candidatos_en_la_misma_vacante(self) -> None:
        repo = _CandidatoRepo()
        svc, _ = _svc([_mensaje("m1", "sin codigo", partes=[
            _parte("ana.pdf", "application/pdf", "a1"),
            _parte("luis.pdf", "application/pdf", "a2")])], candidatos=repo)
        svc.asignar_mail("m1", V1, cliente=_Client())
        assert len(repo.creados) == 2
        assert {c.vacante_id for c in repo.creados} == {V1}

    def test_sube_el_cv_y_lo_ata(self) -> None:
        repo = _CandidatoRepo()
        svc, _ = _svc([_mensaje("m1", "sin codigo",
                                partes=[_parte("cv.pdf", "application/pdf", "a1")])],
                      candidatos=repo)
        svc.asignar_mail("m1", V1, cliente=_Client())
        assert repo.cvs["cand-1"].endswith("cv.pdf")

    def test_una_vacante_de_otra_empresa_se_rechaza(self) -> None:
        """La barrera: el header acota a qué vacante se puede apuntar."""
        repo = _CandidatoRepo()
        svc, _ = _svc([_mensaje("m1", "sin codigo",
                                partes=[_parte("cv.pdf", "application/pdf", "a1")])],
                      candidatos=repo)
        with pytest.raises(AppError) as exc:
            svc.asignar_mail("m1", V2, empresa_id=E1, cliente=_Client())
        assert (exc.value.code, exc.value.status_code) == ("VACANTE_NOT_FOUND", 404)
        assert repo.creados == [], "se creó un candidato sobre una vacante de otra empresa"

    def test_un_mail_sin_cv_utilizable_no_crea_nada_y_lo_dice(self) -> None:
        """Devolver "0 creados" sin motivo dejaría a RRHH sin saber qué pasó."""
        repo = _CandidatoRepo()
        svc, _ = _svc([_mensaje("m1", "sin codigo",
                                partes=[_parte("firma.png", "image/png", "a1")])],
                      candidatos=repo)
        with pytest.raises(AppError) as exc:
            svc.asignar_mail("m1", V1, cliente=_Client())
        assert exc.value.code == "CV_SIN_ADJUNTOS" and exc.value.status_code == 422
        assert repo.creados == []

    def test_audita_la_asignacion_con_la_empresa_de_la_vacante(self) -> None:
        eventos: list = []
        gmail = _Gmail([_mensaje("m1", "sin codigo",
                                 partes=[_parte("cv.pdf", "application/pdf", "a1")])])
        svc = CvPendientesService(gmail=gmail, vacante_repo=_VacanteRepo(),
                                  candidato_repo=_CandidatoRepo(), cv_service=_CvService(),
                                  audit=SimpleNamespace(registrar=lambda **k: eventos.append(k)))
        svc.asignar_mail("m1", V2, cliente=_Client())
        assert len(eventos) == 1 and eventos[0]["evento"] == "asignacion_manual_cv"
        assert eventos[0]["empresa_id"] == E2
