"""
Payload canónico del único evento auditable de la vista "Horas por cliente": la baja.

Archivo propio y no `_audit_payloads.py` (119/150): es la séptima división por módulo del mismo
patrón —`_rrhh`, `_costos`, `_usuarios`, `_ev`, `_cesion`, `_offboarding`, `_clientes`— y la
regla está escrita en el encabezado del original.

🔴 SOLO HAY UN EVENTO PORQUE SOLO HAY UNA ESCRITURA. `test_auditoria_coherente` exige que un
módulo que audita ALGO las audite TODAS; este service borra y nada más, así que "todas" es una.
El día que se agregue el editar (ver el análisis en `horas_cliente_service`), su evento es
obligatorio o el barrido falla — y eso es exactamente lo que se quiere.

⚠️ La carga NO se audita, y no es una omisión de este archivo: la escriben los empleados desde el
link público, donde no hay `usuario_id` que poner (`auditoria.usuario_id` es FK a `users` y los
empleados no tienen cuenta). Ese flujo deja su rastro en `intentos_identificacion` y en la propia
fila. Acá el que borra SÍ es un usuario del sistema, así que el evento tiene autor.
"""
from typing import Optional

from services.audit_service import _jsonable

_ENTIDAD = "hora"
# 🔴 LOS TRES DEL CAMINO POR PROYECTO ENTRAN, Y NO SON DECORATIVOS. `valor_hora_snapshot` es el
# precio CONGELADO al insertar: con `horas` es lo único que permite reconstruir el costo de la
# fila borrada, y ese número no se puede volver a derivar —la asignación pudo cambiar de valor, o
# no existir ya—. `proyecto_id` y `asignacion_id` dicen a qué se imputaba. Las cargas del link
# público los traen en NULL y ahí el evento los muestra vacíos, que es la verdad.
_CAMPOS = ("empleado_id", "cliente_id", "fecha", "horas", "modalidad",
           "proyecto_texto", "tarea_texto", "descripcion",
           "proyecto_id", "asignacion_id", "valor_hora_snapshot")


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_baja_hora(prior, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento DELETE de una carga de horas.

    🔴 `empresa_id` LO PASA EL CALLER CON LA EMPRESA DE LA ENTIDAD, no con la del header. En modo
    consolidado el header es None, y etiquetar el evento con eso lo dejaría fuera del filtro por
    empresa de `/auditoria`. Es el principio Vista vs Acción — borrar es una ACCIÓN — y es el bug
    que `_costos_write.py:80` todavía tiene abierto.

    `datos_anteriores` NO lleva los campos derivados de joins (`cliente_nombre`,
    `empleado_nombre`, `empleado_empresa_nombre`, `costo`): no son datos del registro sino
    resultado de cómo se lo leyó. Por eso se enumera con `_CAMPOS` en vez de volcar el response.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_hora", "empresa_id": empresa_id,
        "datos_anteriores": _subset(prior, _CAMPOS), "datos_nuevos": None,
    }
