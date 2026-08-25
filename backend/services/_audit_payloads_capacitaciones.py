"""
Payloads canónicos de los eventos de auditoría de Formación: el CATÁLOGO de capacitaciones y las
ASIGNACIONES a personas.

Padre e hija en un archivo, igual que `_audit_payloads_proyectos`: la baja del catálogo y la de
una asignación se leen juntas porque una explica a la otra —desactivar un curso NO desasigna a
nadie, y quitarle el curso a una persona no toca el catálogo—, y esa diferencia es justamente la
que alguien va a querer entender leyendo el log.

🔴 LA BAJA DE UNA CAPACITACIÓN ES DE DOS FORMAS Y EL EVENTO TIENE QUE DECIR CUÁL.
`CapacitacionService.delete` hace un soft-delete (`activo=False`) si el curso tiene asignaciones y
un DELETE FÍSICO si no tiene ninguna. Las consecuencias no se parecen: en el primer caso la fila
queda y el historial de quién lo hizo sigue en pie; en el segundo la fila desaparece y el nombre
del curso ya no existe en ningún lado. Un evento que dijera solo "se eliminó la formación X" haría
indistinguibles esas dos cosas — por eso viaja `modo` (`baja_logica` | `borrado_fisico`), que es
literalmente el dato que decide si hay algo que recuperar.

🔴 LA BAJA DE UNA ASIGNACIÓN SE LLEVA EL HISTORIAL DE FORMACIÓN DE UNA PERSONA.
Es un borrado FÍSICO sin ninguna guarda, y lo que desaparece es que Fulano hizo (o tenía
pendiente) ese curso: estado, fechas y `certificado_url`. Ese último campo es el más caro —el
objeto sigue en el bucket `documentos` pero **nadie lo puede volver a encontrar**, porque la ruta
vivía en esta fila y no hay índice inverso—, así que va en el payload: es lo único que permite
rescatar el certificado después.

⚠️ `nombre_libre` TAMBIÉN VIAJA, y no es un campo cualquiera. Desde la migración 116 `empleado_id`
es nullable: una fila importada del Excel de formación puede no colgar de ningún legajo, y ahí
`nombre_libre` es **lo único que identifica a esa persona**. Sin él, el evento de baja de esas
filas saldría anónimo.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

_ENTIDAD_CAPACITACION = "capacitacion"
_ENTIDAD_ASIGNACION = "capacitacion_asignacion"

_CAMPOS_CAPACITACION = ("empresa_id", "nombre", "descripcion", "categoria", "duracion_horas",
                        "entidad_capacitadora", "modalidad", "tipo", "obligatoria", "activo")
_DERIVADOS_CAPACITACION = frozenset({"empresa_nombre", "created_at", "id"})

_CAMPOS_ASIGNACION = ("empresa_id", "capacitacion_id", "empleado_id", "nombre_libre", "estado",
                      "fecha_asignacion", "fecha_limite", "fecha_completado", "certificado_url",
                      "proyecto", "anio", "mes")
# Los cuatro nombres y el `area_id` salen de joins sobre otras tablas: cambian sin que nadie
# edite la asignación, así que en un diff serían ediciones que nadie hizo.
_DERIVADOS_ASIGNACION = frozenset({"empresa_nombre", "capacitacion_nombre", "empleado_nombre",
                                   "area_id", "area_nombre", "created_at", "id"})


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_capacitacion(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de una formación en el catálogo."""
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_CAPACITACION, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_capacitacion", "empresa_id": str(row.empresa_id),
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_CAPACITACION),
    }


def payload_update_capacitacion(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de una formación (diff antes/después)."""
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_CAPACITACION),
        sin_derivados(nuevo, _DERIVADOS_CAPACITACION))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_CAPACITACION, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": "update_capacitacion", "empresa_id": str(prior.empresa_id),
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_capacitacion(prior, fisico: bool, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja de una formación del catálogo.

    🔴 `modo` ES EL CAMPO QUE HACE ÚTIL AL EVENTO — ver el encabezado. `borrado_fisico` significa
    que la fila ya no existe y que esta foto es lo único que queda del curso; `baja_logica`
    significa que la fila sigue ahí con `activo=False` y se puede reactivar.

    `personas_con_el_curso_asignado` es la contracara: es la razón por la que la baja fue lógica
    (el service borra físico solo cuando `has_asignaciones` da False), así que decir "no arrastró
    a nadie" cuando el modo es físico no es redundante — es lo que permite descartar que se hayan
    perdido asignaciones sin ir a buscarlas.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_CAPACITACION, "registro_id": str(prior.id),
        "accion": "DELETE", "evento": "baja_capacitacion", "empresa_id": str(prior.empresa_id),
        "datos_anteriores": {**_subset(prior, _CAMPOS_CAPACITACION),
                             "modo": "borrado_fisico" if fisico else "baja_logica",
                             "personas_con_el_curso_asignado": not fisico},
        "datos_nuevos": None,
    }


def payload_alta_asignacion_capacitacion(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de asignarle una formación a una persona.

    `empresa_id` sale de la fila, que la heredó del EMPLEADO (el service la resuelve con
    `find_empresa_for_empleado`): la asignación pertenece a la sociedad de la persona.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_ASIGNACION, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_asignacion_capacitacion",
        "empresa_id": str(row.empresa_id),
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_ASIGNACION),
    }


def payload_update_asignacion_capacitacion(prior, nuevo, usuario_id: Optional[str],
                                           evento: str = "update_asignacion_capacitacion") -> dict:
    """Evento UPDATE de una asignación: cambio de estado/fechas, o carga del certificado.

    🔑 `evento` ES PARÁMETRO PORQUE LOS DOS UPDATE DEL MÓDULO SON COSAS DISTINTAS PARA QUIEN LEE
    EL LOG. "Pasó a completado" y "se subió el comprobante" tienen endpoints distintos y se
    filtran distinto en `/auditoria`; con un evento compartido, buscar quién adjuntó un
    certificado obligaría a mirar el diff de cada fila. Es el mismo criterio por el que
    `cambio_estado_objetivo` existe aparte de `update_objetivo` — pero acá alcanza un parámetro,
    porque el payload es idéntico salvo la etiqueta.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_ASIGNACION), sin_derivados(nuevo, _DERIVADOS_ASIGNACION))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_ASIGNACION, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": evento, "empresa_id": str(prior.empresa_id),
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_asignacion_capacitacion(prior, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de desasignarle una formación a una persona. Borrado FÍSICO, sin guardas.

    Lo que se pierde es el historial de formación de esa persona — ver el encabezado, en
    particular por qué `certificado_url` y `nombre_libre` están en el payload.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD_ASIGNACION, "registro_id": str(prior.id),
        "accion": "DELETE", "evento": "baja_asignacion_capacitacion",
        "empresa_id": str(prior.empresa_id),
        "datos_anteriores": _subset(prior, _CAMPOS_ASIGNACION), "datos_nuevos": None,
    }
