"""
Payloads canónicos de los eventos de auditoría de recategorizaciones.

ARCHIVO PROPIO Y NO `_audit_payloads.py`: ese está en 119/150 y su encabezado deja escrita la
regla — "si supera ~150 líneas al crecer, partirlo POR MÓDULO". Ya se hizo ocho veces.

`sin_derivados` se IMPORTA del hermano; `_subset` se duplica. Es la regla escrita allá:
`sin_derivados` DEFINE QUÉ ENTRA EN UN DIFF y dos copias darían dos criterios sobre lo mismo;
`_subset` es una proyección trivial.

🔴 ENTIDAD PROPIA `"recategorizacion"`, Y ES UNA DECISIÓN.
Registrar una recategorización dispara DOS eventos: éste y el `update_empleado` que emite
`_empleados_write.actualizar` cuando se pisan `roles`/`seniority`/`categoria`. Si los dos
llevaran `entidad="empleado"`, caerían sobre el mismo `registro_id` con dos minutos de
diferencia y en `/auditoria` se leerían como ruido duplicado — y lo peor: quien filtre por
entidad `empleado` no podría distinguir un cambio de rol registrado con motivo y fecha efectiva
de una edición suelta del legajo.
**Con entidad propia los dos eventos dicen cosas distintas**: éste es el registro de NEGOCIO
(qué cambió, desde cuándo rige, por qué, con qué impacto) y el otro el registro TÉCNICO (qué
columnas se pisaron). Ninguno reemplaza al otro.

🔴 `empresa_id` VA CON LA EMPRESA DE LA ENTIDAD — o sea la del EMPLEADO —, al revés que
`perfiles_puesto`, que va con NULL porque es del grupo. No es una inconsistencia entre los dos
módulos: es la MISMA regla aplicada a dos entidades distintas. Una recategorización SÍ tiene
sociedad dueña (`recategorizaciones.empresa_id` es NOT NULL, con FK compuesta al empleado), así
que ponerla en NULL la sacaría del filtro por empresa de `/auditoria` sin ningún motivo. Y no
sale del header `X-Empresa-Id`: sale de la fila, que es la única fuente que no puede mentir.
"""
from typing import Optional

from services._audit_payloads import sin_derivados
from services.audit_service import AuditService, _jsonable

# Campos de negocio del alta. `impacto_salarial` NO entra: el evento de auditoría es legible por
# cualquiera con `Seccion.AUDITORIA`, y meter un monto adentro saltearía el gate de COSTOS que
# la respuesta del módulo sí aplica. Es el mismo argumento por el que `mailer/_variables` excluye
# el sueldo de las variables de mail. Que el monto cambió se ve igual: el diff del UPDATE lo
# registra, y ahí el valor viaja porque el evento nace de una edición explícita.
_CAMPOS_ALTA = ("empleado_id", "fecha_efectiva", "motivo",
                "rol_anterior", "rol_nuevo",
                "seniority_anterior", "seniority_nueva",
                "categoria_anterior", "categoria_nueva")

# 🔴 Los TRES nombres resueltos por join. No son datos de la fila: son resultado de cómo se la
# leyó, y el `find_by_id` los trae mientras que un INSERT crudo los devolvería en null. Sin esta
# exclusión, cada edición registraría un cambio que no ocurrió — el "diff fantasma" que generó
# 93 eventos falsos en producción y que `sin_derivados` vino a cerrar.
_DERIVADOS_RECAT = frozenset({"empleado_nombre", "empresa_nombre", "registrado_por_nombre"})

_ENTIDAD = "recategorizacion"


def _subset(obj: object, campos: tuple) -> dict:
    """Extrae `campos` de un modelo Pydantic (o dict) como dict JSON-serializable."""
    data = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)  # type: ignore[arg-type]
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_alta_recategorizacion(row, usuario_id: Optional[str]) -> dict:
    """Evento INSERT del registro de una recategorización.

    `empresa_id` sale de la FILA (que a su vez la heredó del empleado), nunca del header.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": row.id,
        "accion": "INSERT", "evento": "alta_recategorizacion", "empresa_id": row.empresa_id,
        "datos_anteriores": None, "datos_nuevos": _subset(row, _CAMPOS_ALTA),
    }


def payload_update_recategorizacion(prior, nuevo, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de la edición de una recategorización (diff antes/después).

    El diff EXCLUYE derivados en vez de enumerar campos, así que **los `*_anterior`
    recalculados quedan auditados solos** — que es justo lo que hace falta acá: mover la fecha
    efectiva cambia cuál es la recategorización previa y por lo tanto los valores anteriores, y
    ese recálculo es un cambio real del registro que alguien tiene que poder ver.
    """
    antes, despues = AuditService._diff(
        sin_derivados(prior, _DERIVADOS_RECAT), sin_derivados(nuevo, _DERIVADOS_RECAT))
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": prior.id,
        "accion": "UPDATE", "evento": "update_recategorizacion", "empresa_id": prior.empresa_id,
        "datos_anteriores": antes, "datos_nuevos": despues,
    }
