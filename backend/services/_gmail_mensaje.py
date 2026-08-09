"""
Lo que se puede saber de un mensaje de Gmail SIN volver a hablar con Gmail.

Extraído de `gmail_service.py`, que estaba en 145/150. Funciones puras sobre lo que la API ya
devolvió: no abren conexiones, no tocan la base y **no saben nada de vacantes ni de candidatos**.

## El criterio del corte: LA RED

`gmail_service` se queda con las conversaciones HTTP con la API de mensajes y con el caso de uso;
acá vive la interpretación del contenido, que no necesita red. La descarga de un adjunto —que sí
abre una conexión— vive en `services/_gmail_adjuntos.py`, que era el corte anotado y que se creó
cuando por fin tuvo algo adentro.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.

`_parse_from_header` y `_is_cv_email` conservan su guion bajo porque el movimiento fue verbatim y
los callers —incluido `tests/test_gmail_candidatos.py`— los referencian así. Molde de
importación: `repositories/_inventario_items_row.py::_build`.
"""
import base64
from dataclasses import dataclass
from typing import List, Optional

_CV_KEYWORDS = ("cv", "curriculum", "postulacion", "candidatura", "postulación")


@dataclass(frozen=True)
class ParteAdjunta:
    """Una hoja del árbol MIME que trae un archivo.

    `attachment_id` y `contenido_inline` son EXCLUYENTES y los dos pueden faltar en teoría, pero
    Gmail siempre manda uno: los adjuntos grandes viajan por referencia (`body.attachmentId`, hay
    que ir a buscarlos) y los CHICOS vienen embebidos en `body.data`, ya en el mensaje. Modelar
    solo el primero haría que un CV de pocos KB se perdiera en silencio.
    """
    filename: str
    mime: str
    tamano: int
    attachment_id: Optional[str] = None
    contenido_inline: Optional[str] = None


def _parse_from_header(from_header: str) -> tuple[str, str, str]:
    """Extrae (email, nombre, apellido) del header From de un email."""
    if "<" in from_header and ">" in from_header:
        name_part = from_header[: from_header.index("<")].strip().strip('"')
        email_part = from_header[from_header.index("<") + 1 : from_header.index(">")].strip()
    else:
        name_part = ""
        email_part = from_header.strip()
    parts = name_part.split(maxsplit=1)
    nombre = parts[0] if parts else email_part.split("@")[0]
    apellido = parts[1] if len(parts) > 1 else ""
    return email_part, nombre, apellido


def _is_cv_email(subject: str, snippet: str) -> bool:
    """Retorna True si el email parece una postulación por palabras clave."""
    return any(kw in f"{subject} {snippet}".lower() for kw in _CV_KEYWORDS)


def adjuntos_de(payload: Optional[dict]) -> List[ParteAdjunta]:
    """Todas las hojas con archivo de un `payload` de `messages.get?format=full`.

    🔴 EL RECORRIDO ES RECURSIVO PORQUE EL ÁRBOL ANIDA, Y ANIDAR ES LO NORMAL.
    Un mail con adjunto casi nunca es plano: el caso típico es `multipart/mixed` conteniendo un
    `multipart/alternative` (texto + HTML) MÁS la parte del archivo, y los clientes anidan
    distinto entre sí — Outlook, iPhone y el webmail no producen el mismo árbol para el mismo
    mail. Un recorrido de un solo nivel funciona con el ejemplo que uno arma a mano y **falla en
    silencio con los mails reales**: no da error, simplemente no encuentra el CV.

    ⚠️ Devuelve TODO lo que tenga `filename`, sin filtrar por tipo: las firmas de imagen y los
    logos entran acá igual que un CV. Quién es un CV lo decide `cv_service.validar`, no este
    recorrido — mezclar las dos cosas escondería el estado "el mail traía adjuntos y ninguno
    servía", que es distinto de "el mail no traía nada". Ver `_gmail_adjuntos`.

    `format=metadata` NO trae `parts[]`: con ese formato esto devuelve siempre lista vacía.
    """
    encontrados: List[ParteAdjunta] = []

    def _recorrer(parte: Optional[dict]) -> None:
        if not isinstance(parte, dict):
            return
        body = parte.get("body") or {}
        filename = (parte.get("filename") or "").strip()
        if filename:
            encontrados.append(ParteAdjunta(
                filename=filename, mime=parte.get("mimeType") or "",
                tamano=int(body.get("size") or 0),
                attachment_id=body.get("attachmentId"), contenido_inline=body.get("data"),
            ))
        for hijo in parte.get("parts") or []:
            _recorrer(hijo)

    _recorrer(payload)
    return encontrados


def decodificar_base64url(data: str) -> bytes:
    """Decodifica el `body.data` de Gmail, que viene en base64**url** SIN padding.

    🔴 DOS diferencias con base64 estándar, y las dos rompen distinto:
      · el alfabeto usa `-` y `_` donde el estándar usa `+` y `/`. Con `b64decode` a secas, un
        adjunto que contenga esos caracteres se decodifica MAL —bytes corruptos, sin excepción—
        y el PDF resultante no abre.
      · Gmail **omite el padding** `=`. Sin reponerlo, `b64decode` levanta
        `binascii.Error: Incorrect padding` en cualquier contenido cuyo largo no sea múltiplo de
        4, que es el caso normal y no el borde.
    """
    faltante = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + "=" * faltante)
