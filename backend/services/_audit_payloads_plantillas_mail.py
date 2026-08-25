"""
Payloads canónicos de los eventos de auditoría de las plantillas de mail editables (mig 087).

🔴 EL EVENTO QUE JUSTIFICA EL ARCHIVO ES LA BAJA, Y LO QUE LO HACE ÚTIL ES QUE LLEVA EL CUERPO.
El barrido nº 42 lo tenía declarado como DEUDA con la razón exacta: *"el texto que RRHH escribió
desaparece y no hay versión anterior de la que sacarlo"*. `plantillas_mail` no tiene historial ni
versionado —`guardar` es un UPSERT que PISA la fila— así que fuera de este evento **no existe
ningún lugar del sistema donde vivan las versiones anteriores de un mail**. Por eso `cuerpo` y
`asunto` viajan ENTEROS en `datos_anteriores` y no truncados: un mail de RRHH son unos pocos KB
de Markdown, y truncarlo convertiría el único respaldo que hay en un resumen inservible.

🔑 QUÉ SE PUEDE RECONSTRUIR CON ESTO. Con el evento de baja, alguien puede volver a crear la
plantilla tal cual estaba: clave, contexto, asunto y cuerpo son los cuatro campos que
`PlantillaUpsert` pide. Ese es el criterio con el que se eligieron los campos — no "qué es
interesante mirar" sino "qué hace falta para rehacerla".

⚠️ EL CUERPO ES MARKDOWN, NO HTML, Y ESO IMPORTA ACÁ. Es decisión cerrada del módulo (el HTML que
llega al buzón lo genera nuestro código, así la superficie de inyección desaparece), y significa
que el texto que se guarda en `auditoria` es texto plano: no hay script ni markup que un
`/auditoria` renderizando el JSONB pueda llegar a ejecutar.

`empresa_id` sale de la PLANTILLA. Es una entidad de empresa —`guardar` siempre escribe con el
`empresa_id` del request justamente para no pisar la global— así que la etiqueta es real y no un
reflejo del sidebar.
"""
from typing import Optional

from services.audit_service import AuditService, _jsonable

_ENTIDAD = "plantilla_mail"

# Los cuatro campos con los que se puede REHACER la plantilla, más `activa` (que decide si el
# módulo la usa). `empresa_id` no entra en el subset: viaja como etiqueta del evento.
_CAMPOS = ("clave", "contexto", "asunto", "cuerpo", "activa")


def _subset(fila, campos: tuple) -> dict:
    """Extrae `campos` de un dict (o modelo Pydantic) como dict JSON-serializable."""
    data = fila.model_dump() if hasattr(fila, "model_dump") else dict(fila or {})
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_guardar_plantilla(prior, fila, usuario_id: Optional[str],
                              empresa_id: Optional[str]) -> dict:
    """Evento del UPSERT de una plantilla: INSERT si es nueva, UPDATE con diff si ya existía.

    🔴 UN SOLO PAYLOAD PARA LOS DOS CASOS PORQUE LA ESCRITURA ES UNA SOLA. `guardar` es un upsert
    y el service no puede saber de antemano cuál de las dos cosas va a pasar sin una query extra:
    lo que decide es si `prior` se pudo leer. Partirlo en dos funciones obligaría a esa query en
    el camino de alta, que es el más frecuente, para no ganar nada.

    🔑 EL CASO INTERESANTE ES EL SEGUNDO: editar una plantilla PISA el texto anterior sin dejar
    versión. `datos_anteriores` con el cuerpo viejo es lo único que permite volver atrás — la
    misma razón por la que la baja lo lleva.
    """
    nuevo = _subset(fila, _CAMPOS)
    if prior is None:
        return {
            "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(fila["id"]),
            "accion": "INSERT", "evento": "alta_plantilla_mail", "empresa_id": empresa_id,
            "datos_anteriores": None, "datos_nuevos": nuevo,
        }
    antes, despues = AuditService._diff(_subset(prior, _CAMPOS), nuevo)
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(fila["id"]),
        "accion": "UPDATE", "evento": "update_plantilla_mail", "empresa_id": empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_plantilla_mail(prior, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de borrar una plantilla de mail. Borrado FÍSICO: esta foto es el respaldo.

    El `prior` es la fila que devolvió el propio DELETE (PostgREST retorna lo borrado), así que no
    hay ninguna query extra ni ninguna ventana entre leer y borrar: lo que se fotografía es
    exactamente lo que desapareció.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(prior["id"]),
        "accion": "DELETE", "evento": "baja_plantilla_mail",
        "empresa_id": _jsonable(prior.get("empresa_id")),
        "datos_anteriores": _subset(prior, _CAMPOS), "datos_nuevos": None,
    }
