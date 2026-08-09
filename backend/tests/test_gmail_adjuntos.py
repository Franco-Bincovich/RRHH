"""
Bajar el CV de un mail: recorrido del árbol MIME, decode base64url y descarte por adjunto.

## 🔴 LOS ÁRBOLES DEL FAKE SON ANIDADOS, NO PLANOS

Es la decisión que hace que este archivo sirva. **Con un solo árbol plano —`payload.parts` con
la parte del archivo en el primer nivel— un recorrido NO recursivo pasa todos los tests**, y el
bug aparece recién contra un mail real: no da error, simplemente no encuentra el CV.

Por eso los casos de `_ARBOLES` incluyen, como mínimo, los cuatro que el enunciado pide:
  1. plano con un adjunto — el caso fácil, que es el que engaña;
  2. `multipart/mixed` conteniendo `multipart/alternative` (texto + HTML) MÁS el adjunto, que es
     la forma NORMAL de un mail con archivo, no el caso raro;
  3. uno con firma de imagen ADEMÁS del CV — el `.png` tiene `filename` igual que el PDF;
  4. uno con adjuntos pero NINGÚN CV válido, que tiene que ser distinguible de "no adjuntó nada".

Y uno más que aparece solo en producción: el adjunto CHICO, que Gmail manda embebido en
`body.data` en vez de por `attachmentId`. Bajarlo con una llamada a `/attachments` daría 404.

## El decode

`test_decode` usa contenidos SIN padding a propósito: base64url sin `=` es lo que Gmail manda
siempre, no un borde. Y usa bytes que producen `-` y `_` en el alfabeto url, que son justo los
que `b64decode` estándar decodifica MAL —sin excepción, con bytes corruptos—.
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

import pytest  # noqa: E402

from services._gmail_adjuntos import descargar_cvs  # noqa: E402
from services._gmail_mensaje import adjuntos_de, decodificar_base64url  # noqa: E402
from services.cv_service import CvService  # noqa: E402
from utils.files import MAX_SIZE_CV  # noqa: E402


def _b64url(data: bytes) -> str:
    """Como lo manda Gmail: base64url y SIN padding."""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _parte(filename: str, mime: str, *, att_id=None, inline=None, size=1024) -> dict:
    body = {"size": size}
    if att_id:
        body["attachmentId"] = att_id
    if inline:
        body["data"] = inline
    return {"filename": filename, "mimeType": mime, "body": body}


# ── los árboles ───────────────────────────────────────────────────────────────

PLANO = {"mimeType": "multipart/mixed", "filename": "", "body": {},
         "parts": [
             {"filename": "", "mimeType": "text/plain", "body": {"size": 10}},
             _parte("cv.pdf", "application/pdf", att_id="att-1"),
         ]}

# 🔴 EL CASO NORMAL: el adjunto cuelga del mixed, y al lado hay un alternative con dos hojas.
ANIDADO = {"mimeType": "multipart/mixed", "filename": "", "body": {},
           "parts": [
               {"mimeType": "multipart/alternative", "filename": "", "body": {},
                "parts": [
                    {"filename": "", "mimeType": "text/plain", "body": {"size": 10}},
                    {"filename": "", "mimeType": "text/html", "body": {"size": 20}},
                ]},
               _parte("cv.pdf", "application/pdf", att_id="att-1"),
           ]}

# Tres niveles: related dentro de alternative dentro de mixed, con el CV en el fondo.
MUY_ANIDADO = {"mimeType": "multipart/mixed", "filename": "", "body": {},
               "parts": [{"mimeType": "multipart/alternative", "filename": "", "body": {},
                          "parts": [{"mimeType": "multipart/related", "filename": "", "body": {},
                                     "parts": [_parte("cv.docx", "application/msword",
                                                      att_id="att-9")]}]}]}

CON_FIRMA = {"mimeType": "multipart/mixed", "filename": "", "body": {},
             "parts": [
                 {"mimeType": "multipart/related", "filename": "", "body": {},
                  "parts": [
                      {"filename": "", "mimeType": "text/html", "body": {"size": 30}},
                      _parte("logo.png", "image/png", att_id="att-logo"),
                  ]},
                 _parte("cv.pdf", "application/pdf", att_id="att-1"),
             ]}

SIN_CV_VALIDO = {"mimeType": "multipart/mixed", "filename": "", "body": {},
                 "parts": [
                     _parte("firma.png", "image/png", att_id="att-logo"),
                     _parte("foto.jpg", "image/jpeg", att_id="att-foto"),
                 ]}

SIN_ADJUNTOS = {"mimeType": "multipart/alternative", "filename": "", "body": {},
                "parts": [{"filename": "", "mimeType": "text/plain", "body": {"size": 10}}]}


# ── 1. El recorrido ───────────────────────────────────────────────────────────

class TestRecorridoMime:

    @pytest.mark.parametrize("arbol,esperados", [
        (PLANO, ["cv.pdf"]),
        (ANIDADO, ["cv.pdf"]),
        (MUY_ANIDADO, ["cv.docx"]),
        (CON_FIRMA, ["logo.png", "cv.pdf"]),
        (SIN_CV_VALIDO, ["firma.png", "foto.jpg"]),
        (SIN_ADJUNTOS, []),
    ], ids=["plano", "mixed>alternative", "tres_niveles", "con_firma", "sin_cv", "sin_adjuntos"])
    def test_encuentra_las_hojas_con_filename(self, arbol, esperados) -> None:
        """¿Qué tendría que ser distinto en el fake para que falle? Que TODOS los árboles fueran
        planos: ahí un recorrido de un solo nivel pasaría igual. Los casos `mixed>alternative` y
        `tres_niveles` son los que solo puede resolver la recursión."""
        assert [p.filename for p in adjuntos_de(arbol)] == esperados

    def test_el_recorrido_no_filtra_por_tipo(self) -> None:
        """La firma de imagen SALE del recorrido: quién es un CV lo decide `validar`, no esto.
        Mezclarlo escondería el estado 'traía adjuntos y ninguno servía'."""
        assert "logo.png" in [p.filename for p in adjuntos_de(CON_FIRMA)]

    def test_metadata_no_trae_parts_y_da_lista_vacia(self) -> None:
        """Con `format=metadata` el payload solo trae headers. Es la razón de B1."""
        assert adjuntos_de({"headers": [{"name": "From", "value": "a@b.com"}]}) == []
        assert adjuntos_de(None) == []

    def test_distingue_inline_de_referencia(self) -> None:
        p = adjuntos_de({"parts": [_parte("chico.pdf", "application/pdf", inline="QUJD")]})[0]
        assert p.contenido_inline == "QUJD" and p.attachment_id is None


# ── 2. El decode ──────────────────────────────────────────────────────────────

class TestDecodeBase64Url:

    @pytest.mark.parametrize("crudo", [b"A", b"AB", b"ABC", b"ABCD", b"%PDF-1.4 hola mundo"],
                             ids=["1b", "2b", "3b", "4b", "pdf"])
    def test_reponer_el_padding_que_gmail_omite(self, crudo) -> None:
        """Sin padding es el caso NORMAL. ¿Qué tendría que ser distinto para que falle? Que
        `_b64url` NO hiciera `rstrip('=')`: ahí el padding vendría puesto y un decode que no lo
        repone pasaría igual."""
        codificado = _b64url(crudo)
        assert "=" not in codificado
        assert decodificar_base64url(codificado) == crudo

    def test_el_alfabeto_url_no_es_el_estandar(self) -> None:
        """🔴 Bytes elegidos para que la codificación contenga `-` y `_`. Con `b64decode` estándar
        esto NO levanta excepción: devuelve bytes distintos, y el PDF resultante no abre."""
        crudo = bytes([0xFB, 0xEF, 0xBE])
        codificado = _b64url(crudo)
        assert "-" in codificado or "_" in codificado, "el caso no ejercita el alfabeto url"
        assert decodificar_base64url(codificado) == crudo
        with pytest.raises(Exception):
            base64.b64decode(codificado, validate=True)


# ── 3. La descarga y el descarte ──────────────────────────────────────────────

class _Client:
    """Devuelve un PDF por cada attachmentId, y registra qué se pidió."""

    def __init__(self, contenido: bytes = b"%PDF-1.4 cv", falla: bool = False) -> None:
        self.pedidos, self._contenido, self._falla = [], contenido, falla

    def get(self, url, **k):
        self.pedidos.append(url)
        if self._falla:
            raise RuntimeError("500 de Gmail")
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"data": _b64url(self._contenido)})


def _mensaje(payload: dict) -> dict:
    return {"id": "msg-1", "payload": payload}


class TestDescarga:

    def test_baja_el_cv_y_deja_los_bytes_en_memoria(self) -> None:
        c = _Client()
        r = descargar_cvs(c, "tok", _mensaje(ANIDADO), CvService())
        assert [cv.filename for cv in r.cvs] == ["cv.pdf"]
        assert r.cvs[0].contenido == b"%PDF-1.4 cv"
        assert r.cvs[0].message_id == "msg-1"

    def test_la_firma_de_imagen_no_gasta_una_llamada(self) -> None:
        """El `.png` se descarta por extensión ANTES de bajarlo: 1 pedido, no 2."""
        c = _Client()
        r = descargar_cvs(c, "tok", _mensaje(CON_FIRMA), CvService())
        assert len(c.pedidos) == 1 and "att-1" in c.pedidos[0]
        assert [d.filename for d in r.descartados] == ["logo.png"]

    def test_un_adjunto_inline_no_se_va_a_buscar(self) -> None:
        """Gmail manda los chicos embebidos; pedirlos a `/attachments` daría 404."""
        c = _Client()
        payload = {"parts": [_parte("cv.pdf", "application/pdf", inline=_b64url(b"%PDF-1.4 x"))]}
        r = descargar_cvs(c, "tok", _mensaje(payload), CvService())
        assert c.pedidos == [] and r.cvs[0].contenido == b"%PDF-1.4 x"

    def test_traia_adjuntos_y_ninguno_servia_es_distinguible(self) -> None:
        """🔴 B6. `sin_cv_util` separa este caso del mail que no adjuntó nada — los dos tienen
        `cvs == []` y piden respuestas distintas."""
        vacio = descargar_cvs(_Client(), "tok", _mensaje(SIN_ADJUNTOS), CvService())
        malo = descargar_cvs(_Client(), "tok", _mensaje(SIN_CV_VALIDO), CvService())
        assert (vacio.cvs, vacio.tenia_adjuntos, vacio.sin_cv_util) == ([], False, False)
        assert malo.cvs == [] and malo.tenia_adjuntos and malo.sin_cv_util
        assert [d.filename for d in malo.descartados] == ["firma.png", "foto.jpg"]

    def test_un_adjunto_grande_no_tumba_el_lote(self) -> None:
        """🔴 B5. `validar` levanta CV_TOO_LARGE (413), pensado para un upload HTTP. Acá se captura
        POR ADJUNTO: el CV bueno del mismo mail tiene que llegar igual."""
        payload = {"parts": [_parte("enorme.pdf", "application/pdf", att_id="att-big"),
                             _parte("cv.pdf", "application/pdf", inline=_b64url(b"%PDF-1.4 ok"))]}
        c = _Client(contenido=b"x" * (MAX_SIZE_CV + 1))
        r = descargar_cvs(c, "tok", _mensaje(payload), CvService())
        assert [cv.filename for cv in r.cvs] == ["cv.pdf"], "el grande se llevó puesto al bueno"
        assert r.descartados[0].motivo == "CV_TOO_LARGE"

    def test_un_fallo_de_red_se_descarta_no_propaga(self) -> None:
        r = descargar_cvs(_Client(falla=True), "tok", _mensaje(ANIDADO), CvService())
        assert r.cvs == [] and r.descartados[0].motivo == "GMAIL_ERROR"
        assert r.sin_cv_util

    def test_el_token_viaja_en_el_header(self) -> None:
        capturado: list = []

        class _C(_Client):
            def get(self, url, **k):
                capturado.append(k.get("headers", {}).get("Authorization"))
                return super().get(url, **k)

        descargar_cvs(_C(), "tok-sistema", _mensaje(ANIDADO), CvService())
        assert capturado == ["Bearer tok-sistema"]
