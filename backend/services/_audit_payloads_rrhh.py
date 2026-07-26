"""
Armado de payloads de auditoría para empleados, costos, empresa (T18.4c), adjuntos (B4.1)
y períodos cerrados (B3.1).

Continuación de services/_audit_payloads.py (18.4b): se separó en un módulo propio
porque sumar estos 7 eventos cruzaba el límite de 150 líneas del helper original.
Mismo contrato: cada función pura devuelve el dict para `AuditService.registrar(**payload)`.

Decisión sobre `_subset`: se DUPLICA acá (3 líneas triviales) en vez de importarlo
sibling-a-sibling desde _audit_payloads.py — evita un import helper→helper y respeta
que aquel archivo no se modifique. El diff se reusa de `AuditService._diff` (no se
reimplementa).
"""
from typing import Optional
from uuid import uuid4

from services.audit_service import AuditService, _jsonable

_CAMPOS_EMPLEADO = ("nombre", "apellido", "legajo", "roles", "area_id", "estado", "seniority")
_CAMPOS_NOMINA = ("empleado_id", "mes", "anio", "monto_bruto", "monto_neto")
_CAMPOS_PRESUPUESTO = ("area_id", "mes", "anio", "presupuesto")
_CAMPOS_EMPRESA = ("nombre", "cuit", "activa")


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
    """Evento UPDATE de edición de empleado (diff antes/después)."""
    antes, despues = AuditService._diff(prior.model_dump(), nuevo.model_dump())
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


def payload_carga_nomina(nomina, usuario_id: Optional[str], empresa_id: Optional[str], prior=None) -> dict:
    """Evento de carga de nómina (upsert). Con `prior` (la nómina previa del mismo
    empleado/mes/anio) arma el diff antes/después → accion UPDATE. Sin `prior` es la
    primera carga → accion INSERT sin diff. Mismo patrón que payload_update_empleado."""
    base = {
        "usuario_id": usuario_id, "entidad": "nomina", "registro_id": nomina.id,
        "evento": "carga_nomina", "empresa_id": empresa_id,
    }
    if prior is None:
        return {**base, "accion": "INSERT",
                "datos_anteriores": None, "datos_nuevos": _subset(nomina, _CAMPOS_NOMINA)}
    antes, despues = AuditService._diff(_subset(prior, _CAMPOS_NOMINA), _subset(nomina, _CAMPOS_NOMINA))
    return {**base, "accion": "UPDATE", "datos_anteriores": antes, "datos_nuevos": despues}


def payload_set_presupuesto(presupuesto, usuario_id: Optional[str], empresa_id: Optional[str]) -> dict:
    """Evento UPDATE de configuración de presupuesto de área (upsert, sin diff)."""
    return {
        "usuario_id": usuario_id, "entidad": "presupuesto", "registro_id": presupuesto.id,
        "accion": "UPDATE", "evento": "set_presupuesto", "empresa_id": empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(presupuesto, _CAMPOS_PRESUPUESTO),
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


def payload_alta_usuario(user_id: str, username: str, rol: str, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de alta de un usuario del sistema. NUNCA incluye la contraseña temporal.
    empresa_id = None: los usuarios son globales, no pertenecen a una empresa."""
    return {
        "usuario_id": usuario_id, "entidad": "usuario", "registro_id": user_id,
        "accion": "INSERT", "evento": "alta_usuario", "empresa_id": None,
        "datos_anteriores": None, "datos_nuevos": {"username": username, "rol": rol},
    }


def payload_baja_usuario(user_id: str, username: Optional[str], usuario_id: Optional[str]) -> dict:
    """Evento DELETE de baja de un usuario del sistema. NUNCA incluye contraseñas.
    empresa_id = None: los usuarios son globales, no pertenecen a una empresa."""
    return {
        "usuario_id": usuario_id, "entidad": "usuario", "registro_id": user_id,
        "accion": "DELETE", "evento": "baja_usuario", "empresa_id": None,
        "datos_anteriores": {"username": username}, "datos_nuevos": None,
    }


def payload_cambio_password(user_id: str) -> dict:
    """Evento UPDATE de cambio de contraseña propia (self-service). NUNCA incluye
    contraseñas: registra solo que el usuario cambió su clave. usuario_id = registro_id
    (el usuario se audita a sí mismo). empresa_id = None (los usuarios son globales)."""
    return {
        "usuario_id": user_id, "entidad": "usuario", "registro_id": user_id,
        "accion": "UPDATE", "evento": "cambio_password", "empresa_id": None,
        "datos_anteriores": None, "datos_nuevos": None,
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


def payload_importacion_nomina(
    archivo: str, creados: int, actualizados: int, con_faltantes: int, no_cargados: int,
    usuario_id: Optional[str],
) -> dict:
    """Evento de auditoría de un lote de import de nómina de empleados (UN evento por lote).
    Refleja el resumen: nuevos, actualizados (dedup DNI), con faltantes y no cargados.
    empresa_id None: el lote puede crear empleados en varias empresas (columna Organismo)."""
    return {
        # registro_id = id DE EVENTO (uuid4 generado), no de recurso: el import de nómina no
        # persiste un lote con id propio (a diferencia de evaluaciones). NO "corregir" a un id real.
        "usuario_id": usuario_id, "entidad": "empleado", "registro_id": str(uuid4()),
        "accion": "INSERT", "evento": "importacion_nomina", "empresa_id": None,
        "datos_anteriores": None,
        "datos_nuevos": {
            "archivo": archivo, "creados": creados, "actualizados": actualizados,
            "con_faltantes": con_faltantes, "no_cargados": no_cargados,
        },
    }
