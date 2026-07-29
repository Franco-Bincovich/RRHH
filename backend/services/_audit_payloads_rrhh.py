"""
Armado de payloads de auditoría para empleados y empresa (T18.4c), adjuntos (B4.1)
y períodos cerrados (B3.1).

Continuación de services/_audit_payloads.py (18.4b): se separó en un módulo propio
porque sumar estos eventos cruzaba el límite de 150 líneas del helper original. Costos y
usuarios volvieron a salir de acá por el mismo motivo, a _audit_payloads_costos.py y
_audit_payloads_usuarios.py.
Mismo contrato: cada función pura devuelve el dict para `AuditService.registrar(**payload)`.

Decisión sobre los helpers: `_subset` se DUPLICA acá (3 líneas triviales). `sin_derivados`
en cambio SÍ se importa del hermano, a propósito: define qué entra en un diff de auditoría, y
dos copias que se separen darían dos criterios distintos sobre lo mismo — exactamente la clase
de divergencia silenciosa que la regla de ese módulo existe para evitar. El diff se reusa de
`AuditService._diff` (no se reimplementa).
"""
from typing import Optional

from services._audit_payloads import sin_derivados

# `payload_importacion_nomina` se MUDÓ a _audit_payloads_import.py (este archivo estaba en
# 149/150 y la consolidación de auditoría del import lo va a extender). Se re-exporta desde acá
# para que el path de import viejo siga funcionando: mover un símbolo no tiene por qué ser un
# cambio incompatible para quien lo importa. Los callers nuevos deben usar el módulo nuevo.
from services._audit_payloads_import import payload_importacion_nomina  # noqa: F401
from services.audit_service import AuditService, _jsonable

_CAMPOS_EMPLEADO = ("nombre", "apellido", "legajo", "roles", "area_id", "estado", "seniority")
_CAMPOS_EMPRESA = ("nombre", "cuit", "activa")
# Lo que NO es columna de `empleados`: los tres nombres los resuelve el SELECT con joins.
_DERIVADOS_EMPLEADO = frozenset({"area_nombre", "empresa_nombre", "manager_nombre"})


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_empleado(row, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento INSERT de alta de empleado."""
    return {
        "usuario_id": usuario_id, "entidad": "empleado", "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_empleado", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_EMPLEADO),
    }


def payload_update_empleado(prior, nuevo, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento UPDATE de edición de empleado (diff antes/después) sobre columnas reales.

    El subset NO es una optimización: `prior` viene de un SELECT con joins y `nuevo` de un
    `UPDATE ... RETURNING` que no los trae, así que difear los responses completos registraba
    `area_nombre`/`empresa_nombre` pasando a null en CADA edición — un cambio inexistente.
    Excluye los derivados en vez de enumerar columnas: `_CAMPOS_EMPLEADO` (que usan el alta y
    la baja para fotografiar un estado) cubre 7 campos, y `empleados` tiene 29 columnas más que
    se pueden editar —`manager_id`, `dni`, `email_corporativo`, `fecha_ingreso`…—. Enumerar
    dejaría de registrar esas ediciones EN SILENCIO, que en un log de auditoría es peor que el
    fantasma que este cambio vino a sacar. Ver la regla en el docstring de _audit_payloads.py."""
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_EMPLEADO), sin_derivados(nuevo, _DERIVADOS_EMPLEADO),
    )
    return {
        "usuario_id": usuario_id, "entidad": "empleado", "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_empleado", "empresa_id": empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_empleado(prior, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento DELETE (baja lógica) de empleado: datos_anteriores = subset de estado."""
    return {
        "usuario_id": usuario_id, "entidad": "empleado", "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_empleado", "empresa_id": empresa_id,
        "datos_anteriores": _subset(prior, _CAMPOS_EMPLEADO), "datos_nuevos": None,
    }


def payload_alta_empresa(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de alta de empresa. empresa_id del audit = registro_id = id de la empresa."""
    return {
        "usuario_id": usuario_id, "entidad": "empresa", "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_empresa", "empresa_id": row.id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_EMPRESA),
    }


def payload_toggle_empresa(empresa_id: str, activa: bool, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de activación/desactivación de empresa. registro_id = empresa_id."""
    return {
        "usuario_id": usuario_id, "entidad": "empresa", "registro_id": empresa_id,
        "accion": "UPDATE", "evento": "toggle_empresa_activa", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": {"activa": activa},
    }


def payload_alta_adjunto(adj, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de alta de adjunto. Se registra bajo la ENTIDAD PADRE (entidad/entidad_id
    del adjunto) para que aparezca en el historial de ese registro (ej. empleado)."""
    return {
        "usuario_id": usuario_id, "entidad": adj.entidad, "registro_id": adj.entidad_id,
        "accion": "INSERT", "evento": "alta_adjunto", "empresa_id": adj.empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {"adjunto_id": adj.id, "nombre_archivo": adj.nombre_archivo, "categoria": adj.categoria},
    }


def payload_baja_adjunto(adj, usuario_id: Optional[str]) -> dict:
    """Evento DELETE (soft) de adjunto, bajo la entidad padre (mismo criterio que el alta)."""
    return {
        "usuario_id": usuario_id, "entidad": adj.entidad, "registro_id": adj.entidad_id,
        "accion": "DELETE", "evento": "baja_adjunto", "empresa_id": adj.empresa_id,
        "datos_anteriores": {"adjunto_id": adj.id, "nombre_archivo": adj.nombre_archivo},
        "datos_nuevos": None,
    }


def payload_cierre_periodo(p, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de cierre de período (bloqueo). registro_id = id del período."""
    return {
        "usuario_id": usuario_id, "entidad": "periodo", "registro_id": p.id,
        "accion": "INSERT", "evento": "cierre_periodo", "empresa_id": p.empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": {"modulo": p.modulo, "desde": str(p.desde), "hasta": str(p.hasta)},
    }


def payload_reapertura_periodo(p, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de reapertura de un período (estado cerrado → abierto)."""
    return {
        "usuario_id": usuario_id, "entidad": "periodo", "registro_id": p.id,
        "accion": "UPDATE", "evento": "reapertura_periodo", "empresa_id": p.empresa_id,
        "datos_anteriores": {"estado": "cerrado"}, "datos_nuevos": {"estado": "abierto"},
    }

