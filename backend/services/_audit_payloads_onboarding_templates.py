"""
Payloads canónicos de los eventos de auditoría de las PLANTILLAS de onboarding y sus TAREAS.

🔴 LO QUE HACE ÚTIL AL EVENTO DE BAJA DE UNA PLANTILLA: LAS TAREAS VIAJAN ENTERAS.
Una plantilla de onboarding NO es un registro con cuatro campos: es una lista de tareas que
alguien de RRHH escribió una por una —título, descripción, semana, orden, responsable, días de
límite— y que representa el proceso de incorporación de la empresa. Borrarla las borra todas, y
`onboarding_tareas` no tiene versionado ni papelera. Un evento que dijera *"se eliminó la
plantilla Ingreso Comercial"* dejaría sin reconstruir exactamente lo que costó trabajo escribir.
Por eso `datos_anteriores.tareas` lleva la lista completa: con eso la plantilla se puede rehacer.

🔴 Y ES DE DOS FORMAS, COMO CAPACITACIONES E INVENTARIO. `onboarding_templates_repo.delete_template`
hace `activo=False` si la plantilla ya se usó en algún onboarding, y un DELETE FÍSICO si nunca se
usó. La diferencia es total —en el primer caso la fila y sus tareas quedan; en el segundo no queda
nada— así que `modo` va en el payload. Con `baja_logica`, además, las instancias en curso siguen
apuntando a la plantilla: ese es justamente el motivo de que no se borre.

⚠️ LAS TAREAS NO EMITEN SU PROPIO EVENTO CUANDO SE BORRA LA PLANTILLA, y es deliberado: el hecho
de negocio es uno solo —"se dio de baja este proceso de onboarding"— y emitir N+1 eventos por un
click convertiría `/auditoria` en ruido justo en el módulo que menos filas tiene. La lista adentro
del evento del padre da la misma información en una fila. El criterio es el mismo que en el
CASCADE de objetivos, donde `arrastro_subobjetivos_por_cascade` viaja en el evento del padre.

`empresa_id` sale de la PLANTILLA (`TemplateCreate.empresa_id` es obligatorio y viaja en el body),
y las tareas heredan el suyo de ella, así que las dos entidades se etiquetan igual.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

_ENTIDAD_TEMPLATE = "onboarding_template"
_ENTIDAD_TAREA = "onboarding_template_tarea"

_CAMPOS_TEMPLATE = ("empresa_id", "nombre", "descripcion", "es_publica", "created_by")
# `tareas`/`tareas_total` se resuelven con una consulta aparte y los dos nombres salen de joins.
# `tareas` sí entra al payload de la BAJA, pero por la vía explícita de abajo, no por el diff:
# en un UPDATE aparecería como un cambio cada vez que alguien agrega una tarea por otra puerta.
_DERIVADOS_TEMPLATE = frozenset({"empresa_nombre", "created_by_nombre", "tareas", "tareas_total",
                                 "created_at", "id"})

_CAMPOS_TAREA = ("template_id", "titulo", "descripcion", "semana", "orden",
                 "responsable_tipo", "dias_limite")
_DERIVADOS_TAREA = frozenset({"id"})


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_template(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de una plantilla de onboarding (nace vacía y pública)."""
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_TEMPLATE, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_onboarding_template",
        "empresa_id": str(row.empresa_id) if row.empresa_id else None,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_TEMPLATE),
    }


def payload_update_template(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de una plantilla (diff antes/después).

    `es_publica` entra en el diff y es el campo que más importa: volverla privada la saca de la
    vista de todos los demás operadores de RRHH, y sólo el autor puede hacerlo (`ensure_autor`).
    Es la única edición del módulo que no es colaborativa, así que es la que va a haber que poder
    explicar cuando alguien pregunte por qué dejó de ver una plantilla.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_TEMPLATE), sin_derivados(nuevo, _DERIVADOS_TEMPLATE))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_TEMPLATE, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": "update_onboarding_template",
        "empresa_id": str(prior.empresa_id) if prior.empresa_id else None,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_template(prior, fisico: bool, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja de una plantilla de onboarding.

    🔴 `tareas` LLEVA LA LISTA COMPLETA — ver el encabezado. Es lo único con lo que se puede
    rehacer la plantilla, y `modo` dice si hace falta hacerlo (`borrado_fisico`) o si alcanza con
    reactivar la fila (`baja_logica`).
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_TEMPLATE, "registro_id": str(prior.id),
        "accion": "DELETE", "evento": "baja_onboarding_template",
        "empresa_id": str(prior.empresa_id) if prior.empresa_id else None,
        "datos_anteriores": {
            **_subset(prior, _CAMPOS_TEMPLATE),
            "modo": "borrado_fisico" if fisico else "baja_logica",
            "se_uso_en_algun_onboarding": not fisico,
            "tareas": [_subset(t, _CAMPOS_TAREA) for t in (prior.tareas or [])],
        },
        "datos_nuevos": None,
    }


def payload_alta_tarea_template(row, usuario_id: Optional[str],
                                empresa_id: Optional[str]) -> dict:
    """Evento INSERT de agregar una tarea a una plantilla.

    `empresa_id` lo pasa el caller con la de la PLANTILLA padre: la tarea la hereda de ella al
    insertarse, pero `TareaResponse` no la expone, así que sale del template ya validado.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_TAREA, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_tarea_onboarding_template", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_TAREA),
    }


def payload_update_tarea_template(prior, nuevo, usuario_id: Optional[str],
                                  empresa_id: Optional[str]) -> dict:
    """Evento UPDATE de editar una tarea de la plantilla (diff antes/después)."""
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_TAREA), sin_derivados(nuevo, _DERIVADOS_TAREA))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_TAREA, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": "update_tarea_onboarding_template", "empresa_id": empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_tarea_template(prior, usuario_id: Optional[str],
                                empresa_id: Optional[str]) -> dict:
    """Evento DELETE de quitar una tarea de la plantilla. Borrado FÍSICO, sin guardas.

    El `prior` es la fila que devolvió el propio DELETE, así que lo que se fotografía es
    exactamente lo que desapareció: el título y la descripción que alguien escribió a mano.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_TAREA, "registro_id": str(prior.get("id")),
        "accion": "DELETE", "evento": "baja_tarea_onboarding_template", "empresa_id": empresa_id,
        "datos_anteriores": _subset(prior, _CAMPOS_TAREA), "datos_nuevos": None,
    }
