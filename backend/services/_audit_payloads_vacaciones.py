"""
Payloads de auditoría del módulo de vacaciones que no entran en `_audit_payloads.py`, que ya
está en 167 líneas contra un límite de 150. Mismo criterio y mismo molde que
`_audit_payloads_cesion.py`, que lo dice en su propio encabezado.

Cubre dos entidades del mismo módulo:
  - "vacacion_pendiente" → alta / update / baja de los días NO tomados (tabla nueva, mig. 083).
  - "vacacion"           → el update de una licencia tomada (típicamente `dias_liquidados`).
    La CANCELACIÓN sigue viviendo en `_audit_payloads.payload_cancelacion_vacacion`; no se
    movió para no tocar lo que ya funciona, y comparten el mismo `entidad`/`registro_id`.

Funciones puras: cada una devuelve el dict para AuditService.registrar(**payload).

🔴 Los diffs usan `sin_derivados` (IMPORTADO de _audit_payloads, no duplicado) y NO una lista
curada de campos. Un alta o una baja fotografían un estado y ahí enumerar alcanza; un UPDATE
responde "¿qué cambió?", y ahí una lista curada MIENTE POR OMISIÓN: si alguien edita una
columna que no está en la lista, el log dice que no pasó nada. Excluyendo, una columna nueva
queda auditada sola y lo único que hay que declarar es lo que NO es una columna — que es por
qué `periodo` y `dias_liquidados` se auditan sin tocar nada de esto.
"""
from typing import Optional

from services._audit_payloads import _DERIVADOS_VACACION, sin_derivados
from services.audit_service import AuditService

# Lo que NO es columna de vacaciones_pendientes: nombres resueltos por join en el *Response.
_DERIVADOS = frozenset({"empresa_nombre", "empleado_nombre", "area_id", "area_nombre"})


def payload_alta_pendiente(p, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de alta de días pendientes."""
    return {
        "usuario_id": usuario_id, "entidad": "vacacion_pendiente", "registro_id": p.id,
        "accion": "INSERT", "evento": "alta_vacacion_pendiente", "empresa_id": p.empresa_id,
        "datos_anteriores": None, "datos_nuevos": sin_derivados(p, _DERIVADOS),
    }


def payload_update_pendiente(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de edición de días pendientes (diff antes/después)."""
    antes, despues = AuditService._diff(sin_derivados(prior, _DERIVADOS), sin_derivados(nuevo, _DERIVADOS))
    return {
        "usuario_id": usuario_id, "entidad": "vacacion_pendiente", "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_vacacion_pendiente", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_pendiente(p, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de baja de días pendientes. Snapshot ANTES de borrar (la fila ya no existe después)."""
    return {
        "usuario_id": usuario_id, "entidad": "vacacion_pendiente", "registro_id": p.id,
        "accion": "DELETE", "evento": "baja_vacacion_pendiente", "empresa_id": p.empresa_id,
        "datos_anteriores": sin_derivados(p, _DERIVADOS), "datos_nuevos": None,
    }


def payload_update_vacacion(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de edición de una licencia tomada (diff antes/después).

    Reusa `_DERIVADOS_VACACION` de _audit_payloads —el mismo set que usa la cancelación— para
    que los dos eventos de la misma entidad no puedan aplicar criterios distintos sobre qué
    es una columna. Ahí está incluido `estado`, que es calculado y cambia solo con el paso del
    tiempo: sin excluirlo, un update registraría una edición que nadie hizo.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_VACACION), sin_derivados(nuevo, _DERIVADOS_VACACION))
    return {
        "usuario_id": usuario_id, "entidad": "vacacion", "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_vacacion", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }
