"""
Las dos escrituras de las plantillas de mail: guardar (upsert) y borrar.

Salió de `plantillas_service.py`, que al sumarle los eventos de auditoría de la tanda del
25/8/2026 quedaba en 162 contra un tope de 150. Molde: `_objetivos_write.py` y `_areas_write.py`
— funciones libres que reciben el repo y el AuditService, sin estado ni `self`.

🔴 POR QUÉ SALIERON ESTAS DOS Y NO EL PREVIEW, QUE ES LO MÁS LARGO DEL MÓDULO.
El encabezado de `plantillas_service.py` declara tres decisiones y las tres son sobre LECTURA:
que el preview use el MISMO renderer que el envío (si fueran dos, divergen), que use datos REALES
en vez de inventados (con datos inventados los huecos reales no se ven, y son el problema que hoy
existe) y que el preview con datos reales quede gateado también por lectura de EMPLEADOS. Sacar
eso dejaría al service sin lo único que justifica leerlo. Estas dos, en cambio, validan, escriben
y auditan.

Los payloads viven en `services/_audit_payloads_plantillas_mail.py`, con el porqué de que la baja
lleve el cuerpo entero: la tabla NO tiene versionado, así que ese evento es el único respaldo del
texto que RRHH escribió.
"""
from typing import Optional
from uuid import UUID

from schemas.plantillas import PlantillaResponse, PlantillaUpsert
from services._audit_payloads_plantillas_mail import (
    payload_baja_plantilla_mail, payload_guardar_plantilla,
)
from services.mailer._render import contexto_valido, variables_invalidas
from utils.errors import AppError
from utils.logger import logger


def guardar(repo, audit, data: PlantillaUpsert, empresa_id: UUID, a_response,
            usuario_id: Optional[str] = None) -> PlantillaResponse:
    """Crea o edita una plantilla DE LA EMPRESA. Valida el contexto y las variables.

    🔴 Siempre escribe con el `empresa_id` del request, aunque se esté editando una global: editar
    la global desde una empresa la cambiaría para TODAS. Lo que pasa es que se crea la versión
    propia de esta empresa, que a partir de ahí pisa a la global (ver el repo).

    ⚠️ `a_response` entra por parámetro y no se importa: el mapper vive en `plantillas_service` y
    lo usan también las lecturas. Importarlo acá crearía el ciclo service ↔ write.

    Args:
        repo: PlantillaMailRepo (o doble).
        audit: AuditService (o doble).
        data: La plantilla a crear o editar.
        empresa_id: Empresa dueña de la versión que se escribe.
        a_response: Mapper fila → PlantillaResponse.
        usuario_id: Operador, para la trazabilidad del evento.

    Raises:
        AppError: PLANTILLA_CONTEXTO_INVALIDO (422) si el contexto no está en el catálogo.
        AppError: PLANTILLA_VARIABLES_INVALIDAS (422) con la lista de las que sobran.
        AppError: PLANTILLA_SAVE_ERROR (500) si el upsert no devuelve la fila.
    """
    if not contexto_valido(data.contexto):
        raise AppError(f"Contexto desconocido: {data.contexto}",
                       "PLANTILLA_CONTEXTO_INVALIDO", 422)
    malas = variables_invalidas(data.contexto, data.asunto, data.cuerpo)
    if malas:
        raise AppError(
            "Estas variables no existen para este tipo de mail: " + ", ".join(malas)
            + ". Usá el listado de variables disponibles.",
            "PLANTILLA_VARIABLES_INVALIDAS", 422)
    fila = {"clave": data.clave, "contexto": data.contexto, "asunto": data.asunto,
            "cuerpo": data.cuerpo, "activa": data.activa, "empresa_id": str(empresa_id)}
    if data.id:
        fila["id"] = str(data.id)
    # El PRIOR solo se busca cuando la edición trae id: en el alta no hay nada que leer, y una
    # query de más en el camino más frecuente no compraría nada. Va por `find_by_id` y NO por
    # `find(clave, empresa)`, que cae a la global y daría un diff contra otra fila. Ver el payload.
    prior = repo.find_by_id(data.id) if data.id else None
    guardada = repo.guardar(fila)
    if not guardada:
        raise AppError("No se pudo guardar la plantilla", "PLANTILLA_SAVE_ERROR", 500)
    audit.registrar(**payload_guardar_plantilla(prior, guardada, usuario_id, str(empresa_id)))
    logger.info("Plantilla de mail guardada", extra={"clave": data.clave})
    return a_response(guardada)


def borrar(repo, audit, id_: UUID, empresa_id: UUID, usuario_id: Optional[str] = None) -> None:
    """Borra una plantilla de la empresa. Nunca una global (lo impide el repo).

    🔴 El evento lleva el CUERPO entero: `plantillas_mail` no tiene versionado, así que el texto
    que RRHH escribió no sobrevive en ningún otro lado. La fila que se fotografía es la que
    devuelve el propio DELETE, así que no hay ventana entre leerla y borrarla.

    Args:
        repo: PlantillaMailRepo (o doble).
        audit: AuditService (o doble).
        id_: Plantilla a borrar.
        empresa_id: Empresa del request — el repo lo usa para no tocar una global.
        usuario_id: Operador, para la trazabilidad del evento.

    Raises:
        AppError: PLANTILLA_NOT_FOUND (404) si no existe o no es de esta empresa.
    """
    prior = repo.borrar(id_, empresa_id)
    if not prior:
        raise AppError("Plantilla no encontrada", "PLANTILLA_NOT_FOUND", 404)
    audit.registrar(**payload_baja_plantilla_mail(prior, usuario_id))
