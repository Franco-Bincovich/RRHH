"""
Armado de payloads de auditoría para adjuntos (B4.1).

Salieron de services/_audit_payloads_rrhh.py, que quedó sin lugar para los eventos nuevos del
módulo. Mismo criterio con el que ese archivo ya había expulsado costos, usuarios e importación
de nómina a módulos propios: cuando un dominio no entra, se muda entero con sus dos payloads.
Mismo contrato: cada función pura devuelve el dict para `AuditService.registrar(**payload)`.
"""
from typing import Optional


def payload_alta_adjunto(adj, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de alta de adjunto. Se registra bajo la ENTIDAD PADRE (entidad/entidad_id
    del adjunto) para que aparezca en el historial de ese registro (ej. empleado)."""
    return {
        "usuario_id": usuario_id, "entidad": adj.entidad, "registro_id": adj.entidad_id,
        "accion": "INSERT", "evento": "alta_adjunto", "empresa_id": adj.empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {"adjunto_id": adj.id, "nombre_archivo": adj.nombre_archivo, "categoria": adj.categoria},
    }


def payload_principal_adjunto(adj, principal: bool, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE del marcado/desmarcado de adjunto principal, bajo la entidad padre (mismo
    criterio que el alta y la baja).

    `adj` es el estado ANTES del update (sale de `_get_owned`), así que `adj.es_principal` es el
    valor anterior y `principal` el nuevo. Van los dos: "cambió el principal" sin decir cuál era
    no permite reconstruir qué se reemplazó, que es justamente lo que un log de auditoría tiene
    que poder contestar."""
    return {
        "usuario_id": usuario_id, "entidad": adj.entidad, "registro_id": adj.entidad_id,
        "accion": "UPDATE", "evento": "cambio_principal_adjunto", "empresa_id": adj.empresa_id,
        "datos_anteriores": {"adjunto_id": adj.id, "es_principal": adj.es_principal},
        "datos_nuevos": {"adjunto_id": adj.id, "es_principal": principal},
    }


def payload_baja_adjunto(adj, usuario_id: Optional[str]) -> dict:
    """Evento DELETE (soft) de adjunto, bajo la entidad padre (mismo criterio que el alta)."""
    return {
        "usuario_id": usuario_id, "entidad": adj.entidad, "registro_id": adj.entidad_id,
        "accion": "DELETE", "evento": "baja_adjunto", "empresa_id": adj.empresa_id,
        "datos_anteriores": {"adjunto_id": adj.id, "nombre_archivo": adj.nombre_archivo},
        "datos_nuevos": None,
    }
