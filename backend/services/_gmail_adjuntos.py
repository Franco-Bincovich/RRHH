"""
Bajar los CVs de un mensaje de Gmail: la única pieza del recorrido que abre una conexión.

Este era el corte anotado desde el principio ("el recorrido MIME, la descarga y el decode"), y se
crea recién ahora porque hasta hoy no tenía nada adentro: `gmail_service` pedía los mensajes con
`format=metadata`, que ni siquiera trae `payload.parts[]`.

**Qué quedó de cada lado.** El recorrido del árbol y el decode base64url son funciones PURAS sobre
el dict del mensaje y viven en `_gmail_mensaje.py`. Acá vive lo que las compone y lo único que
necesita red: `GET /messages/{id}/attachments/{attachmentId}`.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service.

## 🔴 UN ADJUNTO MALO NO PUEDE TUMBAR EL LOTE

`cv_service.validar` levanta `INVALID_CV_FORMAT` (400) y `CV_TOO_LARGE` (413): códigos pensados
para UN upload por HTTP, donde abortar la request es correcto. En un lote de mails no lo es — un
solo `.png` de firma o un PDF de 20 MB haría fallar la revisión entera y los otros 19 mails no se
procesarían: el usuario vería un error y ningún CV.

Por eso **cada adjunto se valida en su propio `try`** y lo que no pasa se acumula en `descartados`
CON su motivo. La excepción no se traga: se convierte en un dato que alguien puede mirar. Mismo
criterio que el `sin_candidato` del matcheo de evaluaciones y los tres grupos de proyectos.

## 🔴 "TRAÍA ADJUNTOS Y NINGUNO SERVÍA" ES UN ESTADO PROPIO

Un mail real trae la firma de imagen del remitente como una parte con `filename`. Si el resultado
fuera una lista pelada de CVs, ese mail y uno que no adjuntó nada devolverían lo mismo: `[]`. Son
situaciones distintas y piden respuestas distintas —al segundo hay que pedirle el CV, al primero
hay que mirar por qué su adjunto no pasó—, así que `AdjuntosDelMensaje` las distingue con
`tenia_adjuntos` y `sin_cv_util`. Un vacío ambiguo es cómo se pierde una postulación.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from services._gmail_mensaje import ParteAdjunta, adjuntos_de, decodificar_base64url
# El criterio de qué extensión es un CV vive en cv_service y NO se duplica: se importa. Acá solo
# se usa para NO gastar una llamada a Gmail bajando la firma de imagen de cada mail — la
# validación de verdad la sigue haciendo `validar` sobre los bytes ya descargados.
from services.cv_service import _EXT, _ext
from utils.errors import AppError
from utils.logger import logger

_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


@dataclass(frozen=True)
class CvDescargado:
    """Un CV con sus bytes en memoria y de qué mail salió. No persiste nada."""
    message_id: str
    filename: str
    mime: str
    contenido: bytes
    attachment_id: Optional[str] = None


@dataclass(frozen=True)
class AdjuntoDescartado:
    """Un adjunto que existía y no sirvió, con el motivo. NO es un error del lote."""
    filename: str
    motivo: str          # code del AppError: INVALID_CV_FORMAT · CV_TOO_LARGE · GMAIL_ERROR
    detalle: str = ""


@dataclass
class AdjuntosDelMensaje:
    message_id: str
    cvs: List[CvDescargado] = field(default_factory=list)
    descartados: List[AdjuntoDescartado] = field(default_factory=list)

    @property
    def tenia_adjuntos(self) -> bool:
        """¿El mail traía algún archivo, sirviera o no?"""
        return bool(self.cvs or self.descartados)

    @property
    def sin_cv_util(self) -> bool:
        """🔴 Traía adjuntos y ninguno pasó. Distinto de 'no adjuntó nada' — ver el encabezado."""
        return self.tenia_adjuntos and not self.cvs


def descargar_cvs(client, access_token: str, mensaje: dict, cv_service) -> AdjuntosDelMensaje:
    """Baja y valida los adjuntos de UN mensaje ya traído con `format=full`.

    Args:
        client: cliente httpx ya abierto. Se recibe en vez de crearse para que un lote reuse la
            misma conexión: son 1+N llamadas por mail y abrir un cliente por adjunto las
            multiplica sin ganar nada.
        access_token: token de la CASILLA DEL SISTEMA (ver `_casilla_sistema`).
        mensaje: el dict de `messages.get?format=full`.
        cv_service: CvService (o doble) con `validar(contenido, filename, content_type)`.

    Returns:
        AdjuntosDelMensaje. Nunca levanta por un adjunto: los fallos van a `descartados`.
    """
    resultado = AdjuntosDelMensaje(message_id=str(mensaje.get("id") or ""))
    for parte in adjuntos_de(mensaje.get("payload")):
        if _ext(parte.filename) not in _EXT:
            # La firma de imagen del remitente y los logos caen acá, sin gastar una llamada.
            resultado.descartados.append(AdjuntoDescartado(
                parte.filename, "INVALID_CV_FORMAT", "la extensión no es de CV"))
            continue
        try:
            contenido = _bytes_de(client, access_token, resultado.message_id, parte)
            cv_service.validar(contenido, parte.filename, parte.mime or None)
        except AppError as exc:
            # El adjunto se descarta; el lote sigue. Ver el encabezado.
            resultado.descartados.append(AdjuntoDescartado(parte.filename, exc.code, exc.message))
            continue
        resultado.cvs.append(CvDescargado(
            message_id=resultado.message_id, filename=parte.filename, mime=parte.mime,
            contenido=contenido, attachment_id=parte.attachment_id))
    if resultado.sin_cv_util:
        logger.info("Mail con adjuntos y ningún CV válido",
                    extra={"message_id": resultado.message_id,
                           "descartados": [d.filename for d in resultado.descartados]})
    return resultado


def _bytes_de(client, access_token: str, message_id: str, parte: ParteAdjunta) -> bytes:
    """Los bytes de un adjunto, vengan embebidos o haya que ir a buscarlos.

    Gmail manda los adjuntos CHICOS dentro del propio mensaje (`body.data`) y los grandes por
    referencia (`body.attachmentId`). Preguntar primero por el inline ahorra una llamada entera
    en el caso chico; ir siempre a `/attachments` fallaría con 404 en ese caso, porque no hay
    ningún attachmentId que pedir.

    Raises:
        AppError: GMAIL_ERROR (502) si la descarga falla o el cuerpo no trae `data`.
    """
    if parte.contenido_inline:
        return decodificar_base64url(parte.contenido_inline)
    if not parte.attachment_id:
        raise AppError("El adjunto no trae contenido ni referencia", "GMAIL_ERROR", 502)
    try:
        resp = client.get(
            f"{_GMAIL_BASE}/messages/{message_id}/attachments/{parte.attachment_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json().get("data")
    except Exception as exc:  # noqa: BLE001 — se traduce a un code propio, no se propaga crudo
        logger.error("Error al bajar un adjunto de Gmail",
                     extra={"message_id": message_id, "error": str(exc)})
        raise AppError("No se pudo descargar el adjunto", "GMAIL_ERROR", 502)
    if not data:
        raise AppError("El adjunto vino sin contenido", "GMAIL_ERROR", 502)
    return decodificar_base64url(data)
