"""
Los mails de la casilla que NO se resolvieron solos, y la asignación manual de uno de ellos.

## 🔴 LOS PENDIENTES NO SE PERSISTEN — LA CASILLA ES LA FUENTE DE VERDAD

No hay tabla de "mails pendientes": se releen de Gmail cada vez que se abre la pantalla. Guardar
una copia obligaría a sincronizar dos estados —¿qué pasa si RRHH borra el mail?, ¿si lo reenvía?,
¿si el código estaba mal y lo corrige?— y toda desincronización terminaría mostrando una lista
que no existe. Con relectura, el estado es el buzón y no puede mentir.

De ahí salen las dos consecuencias que hacen que el diseño cierre:
  · **Un mail asignado desaparece solo.** Al crear el candidato se guarda su `gmail_message_id`,
    y la lectura siguiente lo saltea. No hay que marcar nada.
  · **Descartar es archivar o etiquetar EN GMAIL.** No se construye un descarte propio: sería un
    segundo estado, del que la casilla no se entera, sobre un mail que sigue ahí.

## 🔴 CUESTA N+1 LLAMADAS Y CERO DESCARGAS DE ADJUNTOS

Que esto sea barato no es casualidad, es lo que lo hace viable:

  1. `messages.list` con `has:attachment` — 1 llamada;
  2. `message_ids_procesados` — 1 query contra `idx_candidatos_gmail_message` (mig 098), ANTES de
     tocar la red. Sin este paso habría que bajar los adjuntos de cada mail ya resuelto para
     descubrir que ya estaba: `existe_cv_de_gmail` se apoya en el sha256 del CONTENIDO;
  3. `messages.get?format=full` por cada mail no procesado — N llamadas.

**Los adjuntos NO se bajan.** Cuántos CVs válidos trae se responde con lo que el propio mensaje ya
declara: `filename`, `mimeType` y `body.size`, que es exactamente lo que `cv_service.validar`
mira. Los bytes recién se piden al ASIGNAR, o sea sobre el mail que RRHH eligió.
"""
from dataclasses import dataclass
from typing import List, Optional

from services._cv_alta import crear_de_un_cv
from services._gmail_adjuntos import descargar_cvs
from services._gmail_matcher import codigos_en
from services._gmail_mensaje import adjuntos_de
from services.cv_service import _EXT, _ext
from utils.errors import AppError
from utils.files import MAX_SIZE_CV
from utils.logger import logger


@dataclass
class MailPendiente:
    message_id: str
    asunto: str
    remitente: str
    fecha: str
    adjuntos_validos: int
    nombres_adjuntos: List[str]
    motivo: str


def _headers(mensaje: dict) -> dict:
    payload = mensaje.get("payload") or {}
    return {h.get("name", ""): h.get("value", "") for h in (payload.get("headers") or [])}


def _cuenta_adjuntos_validos(mensaje: dict) -> tuple:
    """(cuántos parecen CV, sus nombres) SIN bajar un solo byte.

    Usa el mismo criterio que `cv_service.validar` —extensión y tamaño— pero sobre lo que el
    mensaje ya declara (`body.size`). El set de extensiones se IMPORTA de `cv_service`: duplicar
    la lista haría que la pantalla contara distinto de lo que después acepta el alta.
    """
    partes = [p for p in adjuntos_de(mensaje.get("payload"))
              if _ext(p.filename) in _EXT and p.tamano <= MAX_SIZE_CV]
    return len(partes), [p.filename for p in partes]


def pendiente_de(mensaje: dict, motivo: str) -> MailPendiente:
    """Arma la fila que ve RRHH a partir del mensaje ya traído."""
    h = _headers(mensaje)
    validos, nombres = _cuenta_adjuntos_validos(mensaje)
    return MailPendiente(
        message_id=str(mensaje.get("id") or ""), asunto=h.get("Subject", ""),
        remitente=h.get("From", ""), fecha=h.get("Date", ""),
        adjuntos_validos=validos, nombres_adjuntos=nombres, motivo=motivo)


def motivo_de(mensaje: dict, vacante_repo) -> Optional[str]:
    """Por qué este mail no se resolvió solo, o None si sí matchea una vacante.

    Repite el matcheo de `procesar_mail` sin crear nada: la pantalla tiene que mostrar el mismo
    veredicto que la ingesta, y calcularlo con otro criterio los haría divergir.
    """
    encontrados = codigos_en(_headers(mensaje).get("Subject", ""))
    if not encontrados:
        return "sin_codigo"
    if len(encontrados) > 1:
        return "codigo_ambiguo"
    return None if vacante_repo.find_by_codigo(encontrados[0]) else "vacante_desconocida"


def asignar(client, access_token: str, mensaje: dict, vacante, *, candidato_repo,
            cv_service) -> List[str]:
    """Crea los candidatos de un mail sobre la vacante que ELIGIÓ RRHH. Devuelve sus ids.

    Mismo alta que la ingesta automática (`_cv_alta.crear_de_un_cv`): desde que hay vacante para
    adelante no hay una sola diferencia entre los dos caminos.

    🔴 La empresa sale de la VACANTE ELEGIDA, nunca del header. Es Vista vs Acción: asignar es
    una acción y la empresa es la de la entidad. Y es la única fuente posible — un mail no aporta
    ninguna empresa, que es exactamente por qué sin match no se creaba nada.

    ⚠️ Un mail con VARIOS CVs crea VARIOS candidatos, todos sobre la misma vacante: es el caso
    del referente que reenvía tres postulaciones juntas.

    Raises: CV_SIN_ADJUNTOS (422) si el mail no tiene ningún CV utilizable — asignarlo no crearía
        nada y devolver "0 creados" sin motivo dejaría a RRHH sin saber qué pasó.
    """
    adjuntos = descargar_cvs(client, access_token, mensaje, cv_service)
    if not adjuntos.cvs:
        descartados = ", ".join(d.filename for d in adjuntos.descartados)
        raise AppError(
            f"El mail no trae ningún CV utilizable{f' (descartados: {descartados})' if descartados else ''}.",
            "CV_SIN_ADJUNTOS", 422)
    res = _Acumulador(str(mensaje.get("id") or ""))
    hmap = _headers(mensaje)
    for cv in adjuntos.cvs:
        crear_de_un_cv(res, cv, vacante, hmap, candidato_repo=candidato_repo, cv_service=cv_service)
    logger.info("Mail asignado a una vacante a mano",
                extra={"message_id": res.message_id, "creados": len(res.candidatos_creados)})
    return res.candidatos_creados


class _Acumulador:
    """Lo mínimo que `crear_de_un_cv` escribe. Existe para no arrastrar `ResultadoMail`, que
    lleva el vocabulario del matcheo (código, motivo) y acá no significa nada."""

    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        self.candidatos_creados: List[str] = []
        self.ya_existian = 0
