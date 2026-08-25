"""
Payloads canónicos de los eventos de auditoría del CATÁLOGO de inventario (`inventario_items`).

🔴 LA BAJA DE UN ÍTEM ES DE DOS FORMAS Y EL EVENTO TIENE QUE DECIR CUÁL — mismo patrón que
`_audit_payloads_capacitaciones`, y por el mismo motivo. `InventarioItemsService.delete` hace un
soft-delete (`estado='baja'`) si el ítem tiene historial de asignaciones, y un DELETE FÍSICO si
nunca se le asignó a nadie. En el primer caso la fila queda y el historial de quién lo tuvo sigue
en pie; en el segundo la fila desaparece y con ella el `numero_serie`, que es lo único que
identifica físicamente al equipo. Por eso viaja `modo`.

🔑 `numero_serie` Y `costo` SON LOS DOS CAMPOS QUE JUSTIFICAN EL PAYLOAD. Un inventario existe
para poder responder *"¿dónde está la notebook con serie X, y cuánto salió?"*; si la fila se borra
y el evento solo dice "se eliminó un ítem", esa pregunta queda sin respuesta para siempre. `costo`
además es el único registro contable del equipo dentro del sistema.

⚠️ EL SERVICE RECHAZA BORRAR UN ÍTEM ASIGNADO (`ITEM_ASIGNADO`, 409): primero hay que registrar la
devolución. O sea que ninguna baja de este módulo deja a alguien con un equipo que el sistema ya
no conoce, y `estado` en el payload lo deja escrito.

`empresa_id` sale del ÍTEM: `ItemCreate.empresa_id` es obligatorio y viaja en el body, así que la
etiqueta es real y no un reflejo del selector del sidebar (Vista vs Acción).
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

_ENTIDAD = "inventario_item"

_CAMPOS = ("empresa_id", "nombre", "tipo", "descripcion", "numero_serie",
           "estado", "fecha_alta", "costo", "notas")
# `asignado_a` es el NOMBRE del empleado que lo tiene, resuelto por join sobre las asignaciones
# vigentes: cambia cada vez que el equipo se entrega o se devuelve, sin que nadie edite el ítem.
_DERIVADOS = frozenset({"empresa_nombre", "asignado_a", "created_at", "id"})


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_item(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de un ítem en el catálogo."""
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(row.id),
        "accion": "INSERT", "evento": "alta_item_inventario", "empresa_id": str(row.empresa_id),
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS),
    }


def payload_update_item(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de un ítem (diff antes/después).

    El `estado` entra en el diff, y es el que más va a importar: es el campo por el que el ítem
    aparece o desaparece de los selectores de asignación.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS), sin_derivados(nuevo, _DERIVADOS))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(prior.id),
        "accion": "UPDATE", "evento": "update_item_inventario",
        "empresa_id": str(prior.empresa_id),
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_item(prior, fisico: bool, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja de un ítem del catálogo.

    🔴 `modo` es lo que hace útil al evento — ver el encabezado. `borrado_fisico` significa que la
    fila ya no existe y que este payload es el único lugar donde queda el `numero_serie`;
    `baja_logica` significa que la fila sigue, con `estado='baja'`, y su historial de asignaciones
    también.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(prior.id),
        "accion": "DELETE", "evento": "baja_item_inventario",
        "empresa_id": str(prior.empresa_id),
        "datos_anteriores": {**_subset(prior, _CAMPOS),
                             "modo": "borrado_fisico" if fisico else "baja_logica",
                             "tenia_historial_de_asignaciones": not fisico},
        "datos_nuevos": None,
    }
