"""
Armado canónico de los payloads de eventos de auditoría (T18.4b/c).

Cada función pura toma el estado del registro mutado y devuelve el dict listo para
`AuditService.registrar(**payload)`. Centralizar el armado acá evita inflar cada
service de negocio con la misma lógica de diff/subset y mantiene UNA sola fuente de
verdad de la forma de cada evento. Es transversal a 18.4b (vacaciones/ausencias/
offboarding) y 18.4c (empleados/costos/empresa).

Sin IO: solo transforma datos en memoria. Los `datos_anteriores`/`datos_nuevos` se
entregan JSON-serializable (vía `_diff`/`_jsonable` de AuditService); los escalares
(`registro_id`, `empresa_id`) los normaliza `registrar()` como red de seguridad.

Si este archivo supera ~150 líneas al crecer en 18.4c, partirlo por módulo
(p. ej. `_audit_payloads_rrhh.py`, `_audit_payloads_costos.py`).

Nota de diseño: el diff se reusa de `AuditService._diff` (no se reimplementa) para no
duplicar la lógica de comparación campo-a-campo.
"""
from typing import Optional
from uuid import UUID

from services.audit_service import AuditService, _jsonable

# Campos de negocio que se auditan por entidad (evita volcar el row entero).
_CAMPOS_AUSENCIA = (
    "empleado_id", "tipo_id", "fecha_desde", "fecha_hasta", "dias", "justificada", "motivo",
)
_CAMPOS_OFFBOARDING = ("empleado_id", "motivo", "estado", "fecha_inicio")


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_cancelacion_vacacion(prior, nuevo, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento UPDATE de cancelación de una solicitud de vacaciones (diff antes/después)."""
    antes, despues = AuditService._diff(prior.model_dump(), nuevo.model_dump())
    return {
        "usuario_id": usuario_id, "entidad": "vacacion", "registro_id": prior.id,
        "accion": "UPDATE", "evento": "cancelacion_vacacion", "empresa_id": empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_alta_ausencia(row, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento INSERT de alta de ausencia: datos_nuevos = campos de negocio del row."""
    return {
        "usuario_id": usuario_id, "entidad": "ausencia", "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_ausencia", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_AUSENCIA),
    }


def payload_update_ausencia(prior, nuevo, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento UPDATE de edición de ausencia (diff antes/después)."""
    antes, despues = AuditService._diff(prior.model_dump(), nuevo.model_dump())
    return {
        "usuario_id": usuario_id, "entidad": "ausencia", "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_ausencia", "empresa_id": empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_ausencia(prior, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento DELETE de baja de ausencia: datos_anteriores = subset de estado del prior."""
    return {
        "usuario_id": usuario_id, "entidad": "ausencia", "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_ausencia", "empresa_id": empresa_id,
        "datos_anteriores": _subset(prior, _CAMPOS_AUSENCIA), "datos_nuevos": None,
    }


def payload_inicio_offboarding(row, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento INSERT de inicio de offboarding."""
    return {
        "usuario_id": usuario_id, "entidad": "offboarding", "registro_id": str(row.id),
        "accion": "INSERT", "evento": "inicio_offboarding", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_OFFBOARDING),
    }


def payload_entrevista_salida(
    instancia_id: UUID, entrevista_salida: bool, notas: Optional[str],
    usuario_id: Optional[str], empresa_id: Optional[str],
) -> dict:
    """Evento UPDATE del registro de la entrevista de salida.

    Guarda si hay notas y su largo, NO el texto: una entrevista de salida puede contener
    apreciaciones sobre terceros, y la auditoría la lee gente que no es la que la tomó.
    El texto vive en la instancia, que es donde corresponde consultarlo."""
    return {
        "usuario_id": usuario_id, "entidad": "offboarding", "registro_id": str(instancia_id),
        "accion": "UPDATE", "evento": "entrevista_salida", "empresa_id": empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {
            "entrevista_salida": entrevista_salida,
            "notas_cargadas": bool(notas), "notas_largo": len(notas or ""),
        },
    }


def payload_devolucion_activo(
    instancia_id: UUID, activo_id: UUID, devuelto: bool,
    usuario_id: Optional[str], empresa_id: Optional[str],
) -> dict:
    """Evento UPDATE de devolución/reversión de un activo dentro de un offboarding.

    El service solo togglea un bool (no hay row completo), así que el diff se arma a
    mano: prior=!devuelto → nuevo=devuelto, identificando el activo afectado.
    registro_id = instancia de offboarding (entidad auditada)."""
    activo = str(activo_id)
    return {
        "usuario_id": usuario_id, "entidad": "offboarding", "registro_id": str(instancia_id),
        "accion": "UPDATE", "evento": "devolucion_activo", "empresa_id": empresa_id,
        "datos_anteriores": {"activo_id": activo, "devuelto": not devuelto},
        "datos_nuevos": {"activo_id": activo, "devuelto": devuelto},
    }
