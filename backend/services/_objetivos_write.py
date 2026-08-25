"""
Las dos escrituras de objetivos que NO orquestan validaciones de campo: el cambio de estado del
kanban y la baja.

Salió de `objetivo_service.py`, que con los cambios de la migración 119 quedaba en 154 contra un
tope de 150. Molde: `_vacaciones_write.py`, `_costos_write.py` y `_eventos_write.py` — funciones
libres que reciben el repo, sin estado ni `self`.

🔴 LAS DOS AUDITAN, Y LAS CUATRO ESCRITURAS DEL MÓDULO TAMBIÉN (24/8/2026). Hasta esa fecha
`/objetivos` era el ÚNICO módulo del sistema con borrado desde la UI y CERO eventos de auditoría,
y eso ya se cobró un dato: un objetivo real de Karstec desapareció entre el 17/8 y el 24/8 y no
hay forma de saber quién ni cuándo. El borrado es FÍSICO y arrastra los hijos por CASCADE, así
que no quedó ni una fila de la que reconstruirlo. Los payloads viven en
`services/_audit_payloads_objetivos.py`, con el porqué de cada campo.

🔴 POR QUÉ SALIERON ESTAS DOS Y NO `create`/`update`, QUE SON MÁS LARGAS.
El docstring del service declara que ese archivo se queda con la ORQUESTACIÓN: *qué* se valida y
en *qué orden*. En `create` y `update` ese orden es load-bearing —el gate del responsable va antes
del insert, la barrera de empresa antes de cualquier chequeo de estado, `ensure_padre_valido`
antes que `ensure_no_tiene_hijos`— y leerlo de corrido es lo único que hace evidente que está
bien. Sacarlas dejaría al service sin la única cosa que justifica que exista.
Estas dos, en cambio, no orquestan nada: verifican que el objetivo exista dentro de la empresa y
delegan. Son las que se pueden mover sin que se pierda información al leer.

⚠️ El 404 se repite en las dos y es el MISMO literal que usa el service. No se centralizó en un
helper como `empleado_or_404` porque acá son dos call sites en un archivo de 60 líneas: un
`objetivo_or_404` sería una indirección para ahorrar una línea. Si aparece un tercer caller, ese
es el momento.
"""
from typing import Optional
from uuid import UUID

from schemas.objetivo import CambiarEstadoRequest, ESTADOS, ObjetivoResponse
from services._audit_payloads_objetivos import payload_baja_objetivo, payload_estado_objetivo
from utils.errors import AppError
from utils.logger import logger


def cambiar_estado(repo, audit, id: UUID, data: CambiarEstadoRequest,
                   empresa_id: Optional[UUID] = None,
                   usuario_id: Optional[str] = None) -> ObjetivoResponse:
    """Mueve el objetivo a otro estado del kanban. Alimenta los botones ← y → del tablero.

    🔴 EL ORDEN DE LOS DOS CHEQUEOS SÍ IMPORTA acá, aunque el resto no orqueste nada: el estado
    se valida ANTES de buscar el objetivo. Al revés, pedir un estado inválido sobre un id de otra
    empresa devolvería 422 en vez de 404 — y ese 422 confirmaría que el id existe, que es
    exactamente el oráculo de enumeración que la barrera de empresa cierra. Hay un test que lo
    fija (`test_el_estado_se_valida_ANTES_de_buscar_el_objetivo`).

    🔑 El `tipo` NO se toca al mover una tarjeta: la vista a la que pertenece el objetivo es
    independiente de en qué columna del kanban está.

    🔑 EL `prior` SE GUARDA, no se descarta: el `find_by_id` que verifica que el objetivo exista
    es el MISMO valor que el diff necesita como "antes". Volver a leerlo después del update sería
    una segunda ida a la base para obtener el estado NUEVO dos veces — el diff diría
    "haciendo → haciendo", que es el bug que `_candidato_contratar` documenta con el mismo nombre.

    Args:
        repo: ObjetivoRepo (o doble).
        audit: AuditService (o doble).
        id: Objetivo a mover.
        data: El estado destino.
        empresa_id: Empresa del request. None = consolidado.
        usuario_id: Operador, para la trazabilidad del evento.

    Returns:
        El objetivo con el estado nuevo.

    Raises:
        AppError: ESTADO_INVALIDO (422), OBJETIVO_NOT_FOUND (404).
    """
    if data.estado not in ESTADOS:
        raise AppError(f"Estado inválido. Valores: {sorted(ESTADOS)}", "ESTADO_INVALIDO", 422)
    prior = repo.find_by_id(str(id), empresa_id)
    if not prior:
        raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
    updated = repo.set_estado(str(id), data.estado, empresa_id)
    audit.registrar(**payload_estado_objetivo(prior, updated, usuario_id))
    logger.info("Estado de objetivo cambiado",
                extra={"objetivo_id": str(id), "estado": data.estado})
    return updated


def eliminar(repo, audit, id: UUID, empresa_id: Optional[UUID] = None,
             usuario_id: Optional[str] = None) -> None:
    """Elimina el objetivo permanentemente (no hay historial que preservar).

    Borrado FÍSICO, no lógico, y es una decisión: un objetivo no tiene historial que conservar,
    a diferencia de un cliente (baja lógica) o de una nómina. De eso depende además que el índice
    único siga siendo correcto sin ser parcial — una fila borrada libera su clave de verdad. Está
    escrito en el encabezado de la migración 111.

    🔴 El CASCADE se lleva a los subobjetivos: la FK `parent_id` es ON DELETE CASCADE (migración
    095). Borrar un padre borra a sus hijos, y eso es lo que la pantalla tiene que advertir.

    🔴 EL EVENTO SE ARMA ANTES DEL DELETE Y SE REGISTRA DESPUÉS. Antes, porque después de borrar
    no hay fila que fotografiar y el borrado es FÍSICO: este evento es lo único que va a quedar.
    Después, porque un evento emitido antes del DELETE afirmaría una baja que todavía puede
    fallar. Lo mismo vale para `tiene_hijos`, que se consulta con la fila viva.

    Args:
        repo: ObjetivoRepo (o doble).
        audit: AuditService (o doble).
        id: Objetivo a borrar.
        empresa_id: Empresa del request. None = consolidado.
        usuario_id: Operador, para la trazabilidad del evento.

    Raises:
        AppError: OBJETIVO_NOT_FOUND (404) si no existe o es de otra empresa.
    """
    prior = repo.find_by_id(str(id), empresa_id)
    if not prior:
        raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
    evento = payload_baja_objetivo(prior, repo.tiene_hijos(str(id), empresa_id), usuario_id)
    repo.delete(str(id), empresa_id)
    audit.registrar(**evento)
    logger.info("Objetivo eliminado", extra={"objetivo_id": str(id)})
