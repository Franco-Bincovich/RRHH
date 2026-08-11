"""
Payloads canónicos de los eventos de auditoría del catálogo de clientes.

ARCHIVO PROPIO Y NO `_audit_payloads.py`: ese está en 119/150 y su encabezado deja escrita la
regla —"si supera ~150 líneas al crecer, partirlo POR MÓDULO"—, cosa que ya se hizo seis veces
(`_rrhh`, `_costos`, `_usuarios`, `_ev`, `_cesion`, `_offboarding`). Sumarle tres payloads acá
lo dejaba al filo.

`sin_derivados` se IMPORTA del hermano; `_subset` se duplica. No es inconsistencia: es la regla
escrita en `_audit_payloads.py`. `sin_derivados` DEFINE QUÉ ENTRA EN UN DIFF, y dos copias que
se separen darían dos criterios distintos sobre lo mismo; `_subset` es una proyección trivial.

🔴 `ClienteResponse` NO TIENE NINGÚN CAMPO DERIVADO DE UN JOIN, y por eso `_DERIVADOS_CLIENTE`
está vacío. Eso NO lo vuelve decorativo: es exactamente el punto de usar `sin_derivados` en vez
de enumerar columnas. Un alta fotografía un estado y ahí una lista curada alcanza; un UPDATE
responde "¿qué cambió?" y una lista curada MIENTE POR OMISIÓN — si mañana la tabla gana una
columna y el diff enumera, esa edición no se registra y nadie se entera. Con la exclusión, la
columna nueva queda auditada sola. El día que `ClienteResponse` gane un `empresa_nombre`
resuelto por join, va acá y en ningún otro lado.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

# Campos de negocio del alta/baja. `empresa_id` NO entra: desde la migración 108 un cliente no
# pertenece a ninguna empresa, así que no hay sociedad dueña que fotografiar.
_CAMPOS_CLIENTE = ("nombre", "activo")

# Vacío A PROPÓSITO — ver el encabezado. No borrar la constante ni el argumento: sacarlos
# obligaría a volver a decidir esto desde cero la próxima vez que el schema crezca.
_DERIVADOS_CLIENTE: frozenset = frozenset()

_ENTIDAD = "cliente"

# 🔴 LOS TRES EVENTOS VAN CON `empresa_id` NULL, Y ES UNA DECISIÓN, NO UN DEFAULT OLVIDADO.
# `auditoria.empresa_id` es nullable (verificado en el catálogo), así que el INSERT entra igual.
#
# Un cliente es GLOBAL: no tiene empresa. La única empresa disponible en el contexto de estas
# escrituras sería la del header `X-Empresa-Id`, y usarla como fallback MENTIRÍA sobre de quién es
# la entidad — diría "este cliente es de la empresa A" solo porque el usuario tenía A seleccionada
# en el sidebar al apretar el botón. Es exactamente el bug que `_costos_write.py:80` tiene abierto,
# con el agravante de que acá la entidad ni siquiera TIENE empresa que declarar.
#
# ⚠️ Consecuencia asumida: estos eventos NO aparecen al filtrar `/auditoria` por empresa. Es
# correcto — no pertenecen a ninguna. Aparecen en el consolidado, que es donde corresponde
# buscarlos. Sacrificar eso es preferible a etiquetarlos con una empresa falsa.
_SIN_EMPRESA = None


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_cliente(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del alta de un cliente.

    `empresa_id` va NULL — ver la nota de `_SIN_EMPRESA` arriba.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_cliente", "empresa_id": _SIN_EMPRESA,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_CLIENTE),
    }


def payload_update_cliente(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de un cliente (diff antes/después).

    `empresa_id` va NULL — ver la nota de `_SIN_EMPRESA` arriba.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_CLIENTE), sin_derivados(nuevo, _DERIVADOS_CLIENTE))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_cliente", "empresa_id": _SIN_EMPRESA,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }


def payload_baja_cliente(prior, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de la baja LÓGICA de un cliente (activo → False).

    La acción se registra como DELETE aunque la fila sobreviva: `accion` es el verbo CRUD y lo
    que el usuario hizo fue dar de baja. El detalle de que es lógica está en `evento` y en el
    `datos_anteriores`, que fotografía el estado que tenía antes de desaparecer de los selects.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "DELETE", "evento": "baja_cliente", "empresa_id": _SIN_EMPRESA,
        "datos_anteriores": _subset(prior, _CAMPOS_CLIENTE), "datos_nuevos": None,
    }
