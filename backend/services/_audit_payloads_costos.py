"""
Payloads de auditoría del dominio de costos: carga de nómina y presupuesto de área.

Extraído de _audit_payloads_rrhh.py, que estaba en 189 líneas contra un límite de 150. El
corte por dominio ya estaba anotado en el docstring de _audit_payloads.py ("partirlo por
módulo, p. ej. _audit_payloads_rrhh.py, _audit_payloads_costos.py"): esto lo ejecuta. El
movimiento es puro — las dos funciones son idénticas a las que estaban allá.

Las tuplas `_CAMPOS_*` listan COLUMNAS REALES de la tabla, nunca nombres resueltos por join.
El porqué está en el docstring de _audit_payloads.py; vale para todos los módulos hermanos.
"""
from typing import Optional

from services.audit_service import AuditService, _jsonable

_CAMPOS_NOMINA = ("empleado_id", "mes", "anio", "monto_bruto", "monto_neto")
_CAMPOS_PRESUPUESTO = ("area_id", "mes", "anio", "presupuesto")


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


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
