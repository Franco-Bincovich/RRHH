"""
Payloads de auditoría del módulo de OFFBOARDING (inicio, entrevista de salida, devolución de
activos).

Separados de `_audit_payloads.py` siguiendo la instrucción que ese mismo archivo dejó escrita:
al pasar de ~150 líneas se parte POR MÓDULO, como ya se hizo con `_rrhh`, `_costos`, `_usuarios`,
`_ev` y `_cesion`. La 🔴 REGLA del diff (nunca sobre el *Response completo, nunca sobre campos
derivados de joins) sigue viviendo en el encabezado de `_audit_payloads.py` y rige también acá.

⚠️ `_subset` se DUPLICA a propósito, igual que en los otros cinco hermanos — a diferencia de
`sin_derivados`, que se importa. `_subset` solo proyecta campos; `sin_derivados` DEFINE qué entra
en un diff, y dos copias que se separen darían dos criterios distintos sobre lo mismo.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from services.audit_service import _jsonable

_CAMPOS_OFFBOARDING = ("empleado_id", "motivo", "estado", "fecha_inicio")


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_inicio_offboarding(row, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento INSERT de inicio de offboarding."""
    return {
        "usuario_id": usuario_id, "entidad": "offboarding", "registro_id": str(row.id),
        "accion": "INSERT", "evento": "inicio_offboarding", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_OFFBOARDING),
    }


def payload_efectivizacion_baja(
    instancia_id: UUID, empleado_id: str, fecha_egreso: date,
    usuario_id: Optional[str], empresa_id: Optional[str],
) -> dict:
    """Evento UPDATE de la baja EFECTIVA del empleado y cierre de la instancia.

    🔴 `empresa_id` SALE DE LA INSTANCIA Y NO ES NULL. Un empleado no es una entidad global: su
    baja pertenece a la sociedad que lo tenía. Con `None` el evento quedaría fuera del filtro por
    empresa de `/auditoria`, o sea invisible para quien audita esa empresa — el mismo error que ya
    se corrigió en el import de costos.

    Registra las DOS cosas que cambiaron, que es lo que hace el evento útil al leerlo: el empleado
    pasó a `baja` con su fecha real, y la instancia pasó a `completado`. `fecha_ultimo_dia` NO
    aparece a propósito: no se tocó, y listarla haría creer que sí.
    """
    return {
        "usuario_id": usuario_id, "entidad": "offboarding", "registro_id": str(instancia_id),
        "accion": "UPDATE", "evento": "efectivizacion_baja", "empresa_id": empresa_id,
        "datos_anteriores": {"empleado_estado": "activo", "estado": "iniciado"},
        "datos_nuevos": {
            "empleado_id": str(empleado_id), "empleado_estado": "baja",
            "fecha_egreso": str(fecha_egreso), "estado": "completado",
        },
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
