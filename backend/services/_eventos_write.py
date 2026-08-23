"""
Write path de la agenda de eventos: alta, edición, toggle de resuelta y baja, con su auditoría.

Separado de `evento_agenda_service.py` DESDE EL PRINCIPIO, no cuando reviente: son cuatro
operaciones y cada una emite su evento, y el service tiene además tres lecturas. El corte es el
mismo de `_recategorizaciones_write.py`.

🔴 LAS CUATRO EMPIEZAN POR LA MISMA RELECTURA GATEADA, y por eso `_visible_o_404` existe.
`find_by_id(id, empresa_id, user_id, rol)` aplica los DOS ejes (empresa ∩ visibilidad) en el
WHERE, así que un id de otra empresa o un evento privado ajeno vuelven `None` — y las cuatro
responden el MISMO 404 que un id inexistente. Un 403, o un mensaje distinto, confirmaría que la
fila existe y de quién es: el oráculo de enumeración que la Fase 2 cerró.

🔑 Y la relectura no es solo el gate: es el SNAPSHOT `prior`. La edición lo necesita para el
diff y la baja para el evento de auditoría, que se arma ANTES de borrar porque después no hay
fila que fotografiar.
"""
from typing import Optional
from uuid import UUID

from repositories.evento_agenda_repo import EventoAgendaRepo
from schemas.evento_agenda import EventoCreate, EventoResponse, EventoUpdate
from services._audit_payloads_eventos import (
    payload_alta_evento, payload_baja_evento, payload_resolucion_evento, payload_update_evento,
)
from utils.errors import AppError

# El literal canónico del 404 del módulo. Uno solo, para que "no existe", "es de otra empresa" y
# "es privado de otro" no puedan divergir en mensaje, code ni status.
# 🔴 El MENSAJE dice "Recordatorio" (es lo que ve RRHH) y el `code` sigue siendo
# EVENTO_NOT_FOUND: un code es un identificador de contrato, no texto de pantalla, y el front
# lo matchea. Misma regla que el renombre a "Colaboradores".
NO_ENCONTRADO = ("Recordatorio no encontrado", "EVENTO_NOT_FOUND", 404)


def _visible_o_404(repo: EventoAgendaRepo, id: UUID, empresa_id: Optional[UUID],
                   user_id: Optional[str], rol: Optional[str]) -> EventoResponse:
    """La fila, o 404 indistinguible. Devuelve el modelo para que el caller lo reuse como
    `prior` en vez de volver a consultarlo."""
    fila = repo.find_by_id(str(id), empresa_id, user_id, rol)
    if not fila:
        raise AppError(*NO_ENCONTRADO)
    return fila


def _o_error(fila: Optional[EventoResponse]) -> EventoResponse:
    """La relectura posterior a una escritura. `None` acá NO es "no lo encontré": la fila existía
    hace un instante y el gate ya pasó, así que es un fallo real de la base y sale como 500 —
    devolver un 404 diría que el recurso no existe cuando acabamos de escribirlo."""
    if not fila:
        raise AppError("No se pudo leer el recordatorio después de guardarlo", "DB_ERROR", 500)
    return fila


def crear(repo: EventoAgendaRepo, audit, data: EventoCreate, empresa_id: UUID,
          dias_aviso: int, user_id: str) -> EventoResponse:
    """Alta. `dias_aviso` ya viene resuelto por el service (el propio o el de la empresa)."""
    fila = _o_error(repo.save(data, empresa_id, dias_aviso, user_id))
    audit.registrar(**payload_alta_evento(fila, user_id))
    return fila


def editar(repo: EventoAgendaRepo, audit, id: UUID, data: EventoUpdate,
           empresa_id: Optional[UUID], user_id: Optional[str],
           rol: Optional[str]) -> EventoResponse:
    """Edición parcial. Gatea, guarda el `prior` para el diff, escribe y relee."""
    prior = _visible_o_404(repo, id, empresa_id, user_id, rol)
    nuevo = _o_error(repo.update(str(id), data))
    audit.registrar(**payload_update_evento(prior, nuevo, user_id))
    return nuevo


def resolver(repo: EventoAgendaRepo, audit, id: UUID, resuelta: bool,
             empresa_id: Optional[UUID], user_id: Optional[str],
             rol: Optional[str]) -> EventoResponse:
    """Marca o desmarca como resuelto. Un solo camino para los dos sentidos.

    ⚠️ NO corta si el estado ya era el pedido. Marcar dos veces es idempotente en la base y el
    segundo evento de auditoría dice la verdad —alguien apretó el botón—, mientras que un
    "no hagas nada si ya estaba" abriría la pregunta de qué responder y agregaría una rama que
    ninguna pantalla necesita: el toggle del front manda el valor que quiere, no un incremento.
    """
    _visible_o_404(repo, id, empresa_id, user_id, rol)
    nuevo = _o_error(repo.set_resuelta(str(id), resuelta, user_id))
    audit.registrar(**payload_resolucion_evento(nuevo, user_id))
    return nuevo


def borrar(repo: EventoAgendaRepo, audit, id: UUID, empresa_id: Optional[UUID],
           user_id: Optional[str], rol: Optional[str]) -> None:
    """Baja física. El evento de auditoría se arma con el snapshot PREVIO y se emite después de
    que el borrado salió bien: al revés registraría una baja que pudo no ocurrir."""
    prior = _visible_o_404(repo, id, empresa_id, user_id, rol)
    repo.delete(str(id))
    audit.registrar(**payload_baja_evento(prior, user_id))
