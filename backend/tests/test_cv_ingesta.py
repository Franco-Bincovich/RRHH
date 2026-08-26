"""
El flujo completo de la fase 5: matchear → bajar el CV → crear el candidato.

## 🔴 EL FAKE DE GMAIL DEVUELVE UN `attachmentId` DISTINTO EN CADA LECTURA

Es la decisión que hace que este archivo pruebe algo. La idempotencia se apoya en el **sha256 del
contenido**, no en el `attachmentId`, porque **la API de Gmail no garantiza que dos
`messages.get` del mismo mail devuelvan el mismo id de adjunto**. Un fake que devolviera siempre
el mismo id haría pasar por igual a las dos implementaciones: la correcta y la que usa el
attachmentId como clave. Por eso `_Gmail` incrementa el id en cada lectura y los BYTES son
idénticos — que es exactamente el escenario que rompe la clave equivocada.

`test_idempotencia_el_mismo_mail_dos_veces` corre el flujo DOS veces sobre el mismo fake, y la
segunda no puede crear nada.

## Los otros fakes, y qué puede desmentir cada uno

  · `_VacanteRepo` tiene **DOS vacantes con códigos distintos y de empresas distintas**: sin eso,
    "el candidato hereda la empresa de SU vacante" y "hereda una constante" serían lo mismo.
  · `_CandidatoRepo` mantiene un índice por `(empresa, message_id, sha)` — modela el UNIQUE de la
    migración 098, no solo la escritura.
  · `_CvService` valida de verdad por extensión: un `.png` de firma se descarta como en producción.
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
import hashlib  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from services._cv_ingesta_mail import procesar_mail  # noqa: E402
from services.cv_ingesta_service import CvIngestaService  # noqa: E402
from utils.errors import AppError  # noqa: E402

E1, E2 = str(uuid4()), str(uuid4())
V1, V2 = str(uuid4()), str(uuid4())

CV_ANA = b"%PDF-1.4 cv de ana"
CV_LUIS = b"%PDF-1.4 cv de luis"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _parte(filename, mime, att_id) -> dict:
    return {"filename": filename, "mimeType": mime,
            "body": {"size": 1024, "attachmentId": att_id}}


def _mensaje(mid: str, asunto: str, remitente: str, partes: list) -> dict:
    """Un mail con estructura ANIDADA: mixed conteniendo alternative + los adjuntos."""
    return {"id": mid, "payload": {
        "mimeType": "multipart/mixed", "filename": "", "body": {},
        "headers": [{"name": "Subject", "value": asunto},
                    {"name": "From", "value": remitente}],
        "parts": [{"mimeType": "multipart/alternative", "filename": "", "body": {},
                   "parts": [{"filename": "", "mimeType": "text/plain", "body": {"size": 5}}]},
                  *partes]}}


# ── dobles ────────────────────────────────────────────────────────────────────

class _Gmail:
    """🔴 Devuelve un attachmentId DISTINTO en cada lectura, con los MISMOS bytes."""

    def __init__(self, contenidos: dict) -> None:
        self.contenidos = contenidos          # att_base -> bytes
        self.lecturas = 0

    def get(self, url, **k):
        att = url.rsplit("/", 1)[-1]
        base = att.rsplit("#", 1)[0]          # el sufijo de lectura no forma parte de la identidad
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"data": _b64url(self.contenidos[base])})

    def mensaje(self, plantilla: dict) -> dict:
        """Rinde el mismo mail con ids de adjunto nuevos, como haría Gmail entre dos lecturas."""
        self.lecturas += 1
        import copy
        m = copy.deepcopy(plantilla)

        def _renombrar(parte):
            body = parte.get("body") or {}
            if body.get("attachmentId"):
                body["attachmentId"] = f"{body['attachmentId']}#lectura{self.lecturas}"
            for h in parte.get("parts") or []:
                _renombrar(h)

        _renombrar(m["payload"])
        return m


class _VacanteRepo:
    """DOS vacantes, códigos distintos, EMPRESAS distintas.

    🔴 `codigos()` DEVUELVE UN TERCERO (`VAC-0003`) QUE `find_by_codigo` NO RESUELVE, y no es un
    descuido del doble: es el único estado en que `vacante_desconocida` puede ocurrir desde la
    migración 122. El matcher ya no reconoce una FORMA (`VAC` + 4 dígitos) sino los códigos que
    EXISTEN, así que un código inventado por el candidato ya no llega hasta el lookup — cae antes
    como `sin_codigo`. Lo que sí puede pasar es que la lista se lea al empezar la corrida y la
    vacante se borre mientras la corrida avanza: el código sigue en la lista y el lookup ya no lo
    encuentra. Sin modelar esa asimetría, el caso `vacante_desconocida` sería inalcanzable y su
    test pasaría probando otra cosa.
    """

    def codigos(self):
        return ["VAC-0001", "VAC-0002", "VAC-0003"]

    def find_by_codigo(self, codigo):
        mapa = {"VAC-0001": (V1, E1), "VAC-0002": (V2, E2)}
        if codigo.upper() not in mapa:
            return None
        vid, emp = mapa[codigo.upper()]
        return SimpleNamespace(id=vid, empresa_id=emp, codigo=codigo.upper(), titulo="Analista")


class _CandidatoRepo:
    """Modela el UNIQUE de la 098: índice por (empresa, message_id, sha)."""

    def __init__(self) -> None:
        self.creados: list = []
        self.cvs: dict = {}
        self._indice: set = set()

    def existe_cv_de_gmail(self, empresa_id, message_id, sha256) -> bool:
        return (empresa_id, message_id, sha256) in self._indice

    def save_candidato(self, vacante_id, data, empresa_id, origen=None):
        origen = origen or {}
        clave = (empresa_id, origen.get("gmail_message_id"), origen.get("cv_sha256"))
        if clave in self._indice:
            raise AppError("duplicado", "DB_ERROR", 500)     # el índice único de la base
        self._indice.add(clave)
        # Construido A PARTIR de lo recibido: si devolviera una constante, las aserciones sobre
        # la empresa y el nombre mirarían el propio doble.
        cand = SimpleNamespace(id=f"cand-{len(self.creados) + 1}", vacante_id=vacante_id,
                               empresa_id=empresa_id, nombre=data.nombre, apellido=data.apellido,
                               email=data.email, **origen)
        self.creados.append(cand)
        return cand

    def set_cv(self, candidato_id, path) -> None:
        self.cvs[candidato_id] = path


class _CvService:
    """Valida por extensión como el real, y registra las subidas."""

    def __init__(self, falla_storage: bool = False) -> None:
        self.subidos: list = []
        self._falla = falla_storage

    def validar(self, contenido, filename, content_type) -> None:
        if not filename.lower().endswith((".pdf", ".doc", ".docx")):
            raise AppError("Formato de CV no permitido", "INVALID_CV_FORMAT", 400)

    def subir(self, empresa_id, candidato_id, contenido, filename, mime) -> str:
        if self._falla:
            raise RuntimeError("Storage caído")
        self.subidos.append((empresa_id, candidato_id, filename))
        return f"{empresa_id}/{candidato_id}/{filename}"


def _correr(mensaje, *, vacantes=None, candidatos=None, cv=None, gmail=None):
    gmail = gmail or _Gmail({"att-ana": CV_ANA, "att-luis": CV_LUIS})
    repo = vacantes or _VacanteRepo()
    return procesar_mail(gmail, "tok", mensaje, vacante_repo=repo,
                         candidato_repo=candidatos or _CandidatoRepo(), cv_service=cv or _CvService(),
                         codigos_conocidos=repo.codigos())


# ── 1. El camino feliz ────────────────────────────────────────────────────────

class TestCreacion:

    def test_crea_el_candidato_con_la_empresa_de_SU_vacante(self) -> None:
        """Dos vacantes de dos empresas: un flujo que heredara una constante rojea acá."""
        repo = _CandidatoRepo()
        gmail = _Gmail({"att-ana": CV_ANA})
        _correr(gmail.mensaje(_mensaje("m1", "[VAC-0002] CV", "Ana Pérez <ana@x.com>",
                                       [_parte("cv.pdf", "application/pdf", "att-ana")])),
                candidatos=repo, gmail=gmail)
        assert len(repo.creados) == 1
        assert repo.creados[0].empresa_id == E2 and repo.creados[0].vacante_id == V2
        assert (repo.creados[0].nombre, repo.creados[0].email) == ("Ana", "ana@x.com")

    def test_marca_la_procedencia_y_el_hash_del_contenido(self) -> None:
        repo = _CandidatoRepo()
        gmail = _Gmail({"att-ana": CV_ANA})
        _correr(gmail.mensaje(_mensaje("m1", "[VAC-0001]", "Ana <a@x.com>",
                                       [_parte("cv.pdf", "application/pdf", "att-ana")])),
                candidatos=repo, gmail=gmail)
        c = repo.creados[0]
        assert c.fuente == "gmail" and c.gmail_message_id == "m1"
        assert c.cv_sha256 == hashlib.sha256(CV_ANA).hexdigest()

    def test_sube_el_cv_y_lo_ata_al_candidato(self) -> None:
        repo, cv = _CandidatoRepo(), _CvService()
        gmail = _Gmail({"att-ana": CV_ANA})
        _correr(gmail.mensaje(_mensaje("m1", "[VAC-0001]", "Ana <a@x.com>",
                                       [_parte("cv.pdf", "application/pdf", "att-ana")])),
                candidatos=repo, cv=cv, gmail=gmail)
        assert cv.subidos == [(E1, "cand-1", "cv.pdf")]
        assert repo.cvs["cand-1"].endswith("cv.pdf")

    def test_un_mail_con_dos_cvs_crea_DOS_candidatos(self) -> None:
        """Un referente que reenvía dos CVs son dos postulaciones, no una.

        ¿Qué tendría que ser distinto para que falle? Que el fake trajera un solo adjunto: ahí
        "un candidato por CV" y "uno por mail" serían indistinguibles.
        """
        repo = _CandidatoRepo()
        gmail = _Gmail({"att-ana": CV_ANA, "att-luis": CV_LUIS})
        r = _correr(gmail.mensaje(_mensaje(
            "m1", "[VAC-0001] dos cvs", "Referente <ref@x.com>",
            [_parte("ana.pdf", "application/pdf", "att-ana"),
             _parte("luis.pdf", "application/pdf", "att-luis")])), candidatos=repo, gmail=gmail)
        assert len(repo.creados) == 2 and len(r.candidatos_creados) == 2
        assert len({c.cv_sha256 for c in repo.creados}) == 2, "los dos CVs tienen que diferir"

    def test_la_firma_de_imagen_no_genera_candidato(self) -> None:
        """Un `.png` de firma se descarta; el CV del mismo mail entra igual."""
        repo = _CandidatoRepo()
        gmail = _Gmail({"att-ana": CV_ANA, "att-logo": b"\x89PNG"})
        r = _correr(gmail.mensaje(_mensaje(
            "m1", "[VAC-0001]", "Ana <a@x.com>",
            [_parte("logo.png", "image/png", "att-logo"),
             _parte("cv.pdf", "application/pdf", "att-ana")])), candidatos=repo, gmail=gmail)
        assert len(repo.creados) == 1
        assert r.descartados == ["logo.png"]


# ── 2. Idempotencia ───────────────────────────────────────────────────────────

def test_idempotencia_el_mismo_mail_dos_veces() -> None:
    """🔴 EL TEST QUE JUSTIFICA EL sha256.

    ¿Qué tendría que ser distinto en el fake para que falle? Que `_Gmail.mensaje` devolviera el
    MISMO `attachmentId` en las dos lecturas. Con el id estable, una implementación que usara el
    attachmentId como clave pasaría igual — y en producción crearía el duplicado, porque Gmail no
    garantiza ese id entre lecturas. Acá el id cambia y los bytes no, que es el escenario real.
    """
    repo = _CandidatoRepo()
    gmail = _Gmail({"att-ana": CV_ANA})
    plantilla = _mensaje("m1", "[VAC-0001] CV", "Ana <a@x.com>",
                         [_parte("cv.pdf", "application/pdf", "att-ana")])

    primera = _correr(gmail.mensaje(plantilla), candidatos=repo, gmail=gmail)
    segunda = _correr(gmail.mensaje(plantilla), candidatos=repo, gmail=gmail)

    assert len(primera.candidatos_creados) == 1 and primera.ya_existian == 0
    assert segunda.candidatos_creados == [] and segunda.ya_existian == 1
    assert len(repo.creados) == 1, "se creó un candidato duplicado"
    # La evidencia de que el escenario fue el difícil: los ids de adjunto NO se repitieron.
    assert gmail.lecturas == 2


def test_el_mismo_cv_en_dos_mails_distintos_SI_crea_dos() -> None:
    """La clave incluye el mensaje a propósito: dos personas pueden mandar el mismo archivo (una
    plantilla de CV bajada del mismo lugar). Bloquearlo perdería una postulación real."""
    repo = _CandidatoRepo()
    gmail = _Gmail({"att-ana": CV_ANA})
    for mid in ("m1", "m2"):
        _correr(gmail.mensaje(_mensaje(mid, "[VAC-0001]", "Ana <a@x.com>",
                                       [_parte("cv.pdf", "application/pdf", "att-ana")])),
                candidatos=repo, gmail=gmail)
    assert len(repo.creados) == 2


# ── 3. Lo que NO crea nada ────────────────────────────────────────────────────

class TestPendientes:

    @pytest.mark.parametrize("asunto,motivo", [
        ("CV adjunto", "sin_codigo"),
        ("[VAC-0001] y [VAC-0002]", "codigo_ambiguo"),
        # VAC-0003 SÍ está en `codigos()` y NO lo resuelve `find_by_codigo`: ver el doble.
        ("[VAC-0003] hola", "vacante_desconocida"),
    ], ids=["sin_codigo", "ambiguo", "vacante_desconocida"])
    def test_sin_match_no_crea_nada_y_queda_pendiente(self, asunto, motivo) -> None:
        """🔴 `candidatos.empresa_id` es NOT NULL y sin vacante no hay de dónde heredarla. El mail
        queda listado para que RRHH lo asigne; inventar una empresa sería adivinar a qué sociedad
        pertenece la postulación."""
        repo = _CandidatoRepo()
        gmail = _Gmail({"att-ana": CV_ANA})
        r = _correr(gmail.mensaje(_mensaje("m1", asunto, "Ana <a@x.com>",
                                           [_parte("cv.pdf", "application/pdf", "att-ana")])),
                    candidatos=repo, gmail=gmail)
        assert repo.creados == [] and r.motivo == motivo and r.pendiente

    def test_un_mail_con_adjuntos_pero_ningun_cv_es_distinto_de_uno_sin_adjuntos(self) -> None:
        """Los dos crean 0 candidatos y piden respuestas distintas: a uno hay que pedirle el CV,
        al otro hay que mirar por qué su adjunto no pasó."""
        gmail = _Gmail({"att-logo": b"\x89PNG"})
        solo_firma = _correr(gmail.mensaje(_mensaje(
            "m1", "[VAC-0001]", "Ana <a@x.com>",
            [_parte("firma.png", "image/png", "att-logo")])), gmail=gmail)
        sin_nada = _correr(gmail.mensaje(_mensaje("m2", "[VAC-0001]", "Ana <a@x.com>", [])),
                           gmail=gmail)
        assert solo_firma.motivo == "sin_cv_valido" and solo_firma.descartados == ["firma.png"]
        assert sin_nada.motivo == "sin_adjuntos"


def test_si_storage_falla_el_candidato_NO_se_pierde() -> None:
    """El criterio de `_vacante_candidatos.agregar`, copiado: son dos mutaciones que fallan por
    separado. Revertir el candidato perdería la postulación entera por un problema de disco.

    ¿Qué tendría que ser distinto para que falle? Que `_CvService.subir` no levantara: ahí el
    camino de fallo no se recorre y el test no distinguiría "conserva" de "nunca falló"."""
    repo, cv = _CandidatoRepo(), _CvService(falla_storage=True)
    gmail = _Gmail({"att-ana": CV_ANA})
    _correr(gmail.mensaje(_mensaje("m1", "[VAC-0001]", "Ana <a@x.com>",
                                   [_parte("cv.pdf", "application/pdf", "att-ana")])),
            candidatos=repo, cv=cv, gmail=gmail)
    assert len(repo.creados) == 1, "se perdió la postulación por un fallo de Storage"
    assert repo.cvs == {}, "no debería haber quedado un CV atado"


# ── 4. La corrida completa ────────────────────────────────────────────────────

class TestCorrida:

    class _GmailSvc:
        def __init__(self, mensajes: list) -> None:
            self._m = {m["id"]: m for m in mensajes}

        def token(self):
            return "tok"

        def ids_con_adjunto(self, client, token):
            return list(self._m)

        def mensaje_completo(self, client, token, mid):
            return self._m[mid]

    def _servicio(self, mensajes, candidatos=None, audit=None, cv=None):
        return CvIngestaService(gmail=self._GmailSvc(mensajes), vacante_repo=_VacanteRepo(),
                                candidato_repo=candidatos or _CandidatoRepo(),
                                cv_service=cv or _CvService(),
                                audit=audit or SimpleNamespace(registrar=lambda **k: None))

    def test_resume_creados_y_pendientes(self) -> None:
        repo = _CandidatoRepo()
        gmail = _Gmail({"att-ana": CV_ANA})
        mensajes = [
            gmail.mensaje(_mensaje("m1", "[VAC-0001]", "Ana <a@x.com>",
                                   [_parte("cv.pdf", "application/pdf", "att-ana")])),
            gmail.mensaje(_mensaje("m2", "sin codigo", "Luis <l@x.com>",
                                   [_parte("cv.pdf", "application/pdf", "att-ana")])),
        ]
        r = self._servicio(mensajes, candidatos=repo).revisar_casilla(cliente=gmail)
        assert (r.mails_leidos, r.candidatos_creados) == (2, 1)
        assert [p.motivo for p in r.pendientes] == ["sin_codigo"]

    def test_un_evento_de_auditoria_POR_LOTE(self) -> None:
        """Regla propia del repo. Con 2 mails y 1 candidato, UN evento — no uno por candidato."""
        eventos: list = []
        gmail = _Gmail({"att-ana": CV_ANA})
        mensajes = [gmail.mensaje(_mensaje(f"m{i}", "[VAC-0001]", "Ana <a@x.com>",
                                           [_parte("cv.pdf", "application/pdf", "att-ana")]))
                    for i in (1, 2)]
        audit = SimpleNamespace(registrar=lambda **k: eventos.append(k))
        self._servicio(mensajes, audit=audit).revisar_casilla(cliente=gmail)
        assert len(eventos) == 1
        assert eventos[0]["evento"] == "ingesta_cv_gmail"
        assert eventos[0]["datos_nuevos"]["candidatos_creados"] == 2
        # empresa_id=None: una corrida puede tocar vacantes de varias empresas.
        assert eventos[0]["empresa_id"] is None

    def test_el_presupuesto_corta_y_lo_reporta(self) -> None:
        """Sin `parcial`/`sin_procesar`, una corrida que se queda sin tiempo es indistinguible de
        una que terminó — y el usuario no sabría que tiene que apretar de nuevo."""
        gmail = _Gmail({"att-ana": CV_ANA})
        mensajes = [gmail.mensaje(_mensaje(f"m{i}", "[VAC-0001]", "Ana <a@x.com>",
                                           [_parte("cv.pdf", "application/pdf", "att-ana")]))
                    for i in range(3)]
        r = self._servicio(mensajes).revisar_casilla(presupuesto=-1, cliente=gmail)
        assert r.parcial is False and r.mails_leidos == 3, "presupuesto <= 0 es SIN LÍMITE"

    def test_un_mail_roto_no_corta_la_corrida(self) -> None:
        """Un fallo suyo queda contenido: el resto se procesa igual."""
        class _Roto(self._GmailSvc):
            def mensaje_completo(self, client, token, mid):
                if mid == "m1":
                    raise RuntimeError("Gmail explotó")
                return self._m[mid]

        gmail = _Gmail({"att-ana": CV_ANA})
        mensajes = [gmail.mensaje(_mensaje("m1", "[VAC-0001]", "A <a@x.com>", [])),
                    gmail.mensaje(_mensaje("m2", "[VAC-0001]", "A <a@x.com>",
                                           [_parte("cv.pdf", "application/pdf", "att-ana")]))]
        svc = CvIngestaService(gmail=_Roto(mensajes), vacante_repo=_VacanteRepo(),
                               candidato_repo=_CandidatoRepo(), cv_service=_CvService(),
                               audit=SimpleNamespace(registrar=lambda **k: None))
        r = svc.revisar_casilla(cliente=gmail)
        assert r.candidatos_creados == 1
        assert [p.motivo for p in r.pendientes] == ["error"]
