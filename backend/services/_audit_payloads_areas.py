"""
Payloads canónicos de los eventos de auditoría del módulo de Áreas.

🔴 POR QUÉ ESTE ARCHIVO NACE EN LA TANDA DEL 25/8/2026, Y NO SOLO PARA LA BAJA.
El barrido nº 42 (`tests/test_auditoria_destructivas.py`) tenía a `AreaService.delete_area`
declarado como DEUDA y lo llamaba "de los más caros de perder", con razón: `empleados.area_id`
referencia al área, así que dar de baja una toca legajos. Pero agregarle el evento SOLO a la baja
habría metido a `area_service.py` en el alcance del barrido nº 8
(`tests/test_auditoria_coherente.py`), que exige que un módulo que audita ALGO audite TODO —
"auditar el alta y olvidar la edición es olvido, no criterio". Por eso acá viven los tres.

🔑 LA BAJA DE UN ÁREA ES **LÓGICA** (`activo=False`, `area_repo.delete`), no física. El barrido
la marcaba igual porque indexa por NOMBRE de método y hay un `delete` físico en otros repos —
límite declarado en el encabezado de `tests/_barrido_destructivas.py`. Que sea lógica no la
vuelve inocua: la fila sobrevive pero el área desaparece de los ~15 selectores del front y de
`/api/areas/opciones`, y los legajos que la referencian quedan apuntando a un área que la UI ya
no ofrece. El evento es lo que permite contestar "¿por qué este empleado no tiene área?".

🔴 `cantidad_empleados` VIAJA EN EL PAYLOAD DE LA BAJA Y NO ES DECORATIVO. Es la diferencia entre
un log que dice *"se dio de baja el área Sistemas"* y uno que dice *"…y 13 legajos la
referenciaban"*. Sin ese número, seis meses después nadie puede saber si la baja fue inocua o si
dejó a media empresa sin área. Sale gratis: `AreaResponse` ya lo trae calculado (`_area_row`), no
hace falta ninguna query nueva.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

# Campos del alta/baja. `empresa_id` SÍ entra (a diferencia de clientes): un área pertenece a una
# empresa y esa pertenencia es justamente lo que hay que poder reconstruir.
_CAMPOS_AREA = ("empresa_id", "nombre", "descripcion", "responsable_id")

# Lo que NO es columna de `areas`: el nombre del responsable lo resuelve un join y
# `cantidad_empleados` es un COUNT sobre `empleados`. Los dos cambian sin que nadie edite el
# área, así que en un diff aparecerían como ediciones que nadie hizo — el diff fantasma que este
# repo ya pagó con 93 eventos falsos.
_DERIVADOS_AREA = frozenset({"responsable_nombre", "cantidad_empleados", "created_at", "id"})

_ENTIDAD = "area"


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_area(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de un área.

    `empresa_id` sale del ÁREA, no del header: `AreaCreate.empresa_id` es obligatorio y viaja en
    el body. Vista vs Acción — el sidebar decide qué se mira, el form decide sobre qué se hace.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_area", "empresa_id": row.empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_AREA),
    }


def payload_update_area(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de un área (diff antes/después).

    Va por `sin_derivados` y no por `_CAMPOS_AREA`: un UPDATE responde *qué cambió*, y una lista
    curada miente por omisión el día que la tabla gane una columna editable. Ver la regla en el
    encabezado de `_audit_payloads.py`.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_AREA), sin_derivados(nuevo, _DERIVADOS_AREA))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_area", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_area(prior, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja LÓGICA de un área (activo → False).

    `accion` es DELETE aunque la fila sobreviva: `accion` es el verbo CRUD y lo que el usuario
    hizo fue dar de baja. Mismo criterio que `payload_baja_cliente`.

    🔴 `legajos_que_la_referenciaban` es el campo que hace útil a este evento — ver el encabezado.
    El nombre es explícito a propósito: `cantidad_empleados` a secas se lee como un atributo del
    área, y lo que hay que poder leer seis meses después es *cuántos legajos quedaron colgando*.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_area", "empresa_id": prior.empresa_id,
        "datos_anteriores": {**_subset(prior, _CAMPOS_AREA),
                             "legajos_que_la_referenciaban": prior.cantidad_empleados},
        "datos_nuevos": None,
    }
