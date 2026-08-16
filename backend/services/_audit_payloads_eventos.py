"""
Payloads canónicos de los eventos de auditoría de la agenda (migración 113).

ARCHIVO PROPIO Y NO `_audit_payloads.py`: ese está en 119/150 y su encabezado deja escrita la
regla — "si supera ~150 líneas al crecer, partirlo POR MÓDULO". Ya se hizo nueve veces.

`sin_derivados` se IMPORTA del hermano; `_subset` se duplica. Es la regla escrita allá:
`sin_derivados` DEFINE QUÉ ENTRA EN UN DIFF y dos copias darían dos criterios sobre lo mismo;
`_subset` es una proyección trivial.

🔴 POR QUÉ LA AGENDA AUDITA, SI ES "SOLO UN RECORDATORIO". Porque es el único módulo del repo
donde el BORRADO es parte del flujo normal (decisión de producto: un evento cargado por error no
tiene por qué quedar) y donde una fila puede ser PRIVADA. Las dos juntas dejan un agujero que
ningún listado puede contestar: un evento privado que se creó y se borró no dejó rastro en
ninguna pantalla, ni siquiera para quien lo cargó. El snapshot de la baja es lo que lo cierra.
`tests/test_auditoria_coherente.py` hace el resto: un módulo que audita el alta y se olvida de
la baja da rojo.

🔴 CUATRO EVENTOS Y NO TRES: `resolucion_evento` ES PROPIO Y NO UN `update_evento`.
Resolver es lo que hace desaparecer un evento del dashboard, y es REVERSIBLE. Metido dentro del
diff genérico se leería como "alguien cambió tres columnas", que es exactamente lo que NO
interesa saber: la pregunta de negocio es quién lo dio por atendido y cuándo, y esa respuesta
tiene que poder filtrarse por `evento` sin leer el JSONB de cada UPDATE.

⚠️ `empresa_id` SALE DE LA FILA, NUNCA DEL HEADER. `eventos_agenda.empresa_id` es NOT NULL: el
evento tiene sociedad dueña, y tomarla del `X-Empresa-Id` haría que una baja hecha desde la vista
consolidada quedara con `empresa_id` NULL y fuera del filtro por empresa de `/auditoria`. Es la
misma regla que en recategorizaciones, aplicada a otra entidad.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

# Campos de negocio del alta y de la baja. Son los mismos: las dos FOTOGRAFÍAN un estado, y ahí
# una lista curada es correcta (a diferencia de un UPDATE, donde omitir un campo MIENTE por
# omisión — por eso el diff excluye derivados en vez de enumerar).
_CAMPOS_FOTO = ("nombre", "fecha", "descripcion", "dias_aviso", "es_publica",
                "resuelta", "created_by")

# 🔴 Los TRES nombres resueltos por join. No son datos de la fila: son resultado de cómo se la
# leyó. Sin esta exclusión, cada edición registraría un cambio que no ocurrió — el "diff
# fantasma" que generó 93 eventos falsos en producción y que `sin_derivados` vino a cerrar.
_DERIVADOS_EVENTO = frozenset({"empresa_nombre", "created_by_nombre", "resuelta_por_nombre"})

_ENTIDAD = "evento_agenda"


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_evento(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de un evento de agenda."""
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_evento", "empresa_id": row.empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_FOTO),
    }


def payload_update_evento(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de un evento (diff antes/después).

    El diff EXCLUYE derivados en vez de enumerar campos, así que una columna nueva de la tabla
    queda auditada sola y lo único que hay que declarar es lo que NO es una columna.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_EVENTO), sin_derivados(nuevo, _DERIVADOS_EVENTO))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_evento", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_resolucion_evento(nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE del toggle de resuelta, en los dos sentidos.

    Lleva el estado RESULTANTE y no un diff: el cambio es de una sola cosa y el valor nuevo la
    describe entera. `resuelta=false` es la marcha atrás, y queda registrada igual — sin eso, un
    evento resuelto por error y revertido dejaría en el log solo la mitad que confunde.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": nuevo.id,
        "accion": "UPDATE", "evento": "resolucion_evento", "empresa_id": nuevo.empresa_id,
        "datos_anteriores": None,
        "datos_nuevos": _subset(nuevo, ("resuelta", "resuelta_at", "resuelta_por")),
    }


def payload_baja_evento(prior, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja. El snapshot se toma ANTES de borrar: después no hay fila."""
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_evento", "empresa_id": prior.empresa_id,
        "datos_anteriores": _subset(prior, _CAMPOS_FOTO), "datos_nuevos": None,
    }
