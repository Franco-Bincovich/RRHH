"""
Cuándo NO registrar un evento de auditoría.

Archivo propio porque `audit_service.py` pasaba de 135 a 164 líneas al sumar esta regla y su
justificación, contra un límite de 150. Es un predicado puro, sin IO ni estado — mismo criterio
que `_limite_export.py`, que también aísla una sola regla con el porqué al lado.
`AuditService` lo importa y lo aplica en `registrar`.
"""
from typing import Optional


def es_update_sin_cambios(accion: str, antes: Optional[dict], despues: Optional[dict]) -> bool:
    """True si es un UPDATE cuyo diff salió VACÍO — un evento que no registra nada.

    🔴 LA DISTINCIÓN ENTRE `{}` Y `None` ES LO QUE HACE ESTO SEGURO, no la puede perder nadie:
      · `{}`   = "difeé antes/después y NO encontré diferencias" → el evento no dice nada, se omite.
      · `None` = "acá no se guarda dato, a propósito" → el evento SÍ significa algo y se registra.
    El caso que lo prueba es `payload_cambio_password`: es un UPDATE con los DOS campos en `None`
    porque nunca puede incluir contraseñas, y su valor está entero en el `evento`. Si esta función
    mirara "falsy" en vez de `== {}`, borraría el registro de que alguien cambió su clave.
    Lo mismo con `payload_toggle_empresa`, que trae `datos_anteriores=None`.

    El escenario que lo motiva: reimportar el mismo CSV de nómina. Las filas ya cargadas entran
    por la rama de update, escriben los MISMOS valores, y `AuditService._diff` devuelve `({}, {})`.
    Antes de esto, reimportar 73 filas insertaba 73 filas en `auditoria` sin una sola diferencia
    adentro. Y encima quedaban indistinguibles de un cambio de password, porque el armado del
    payload en `registrar` colapsa `{}` a `None` — razón extra para cortar ANTES, sobre los
    argumentos crudos, y no más adelante.

    Aplica a TODO el sistema, no solo al import: una edición manual que no cambia nada tampoco
    tiene por qué dejar un evento. Los payloads que no salen de un diff (`toggle_empresa`,
    `finalizar_evaluacion`, `reapertura_periodo`) nunca traen los dos en `{}`, así que no los toca.

    La guarda de `accion` no es decorativa: un INSERT o un DELETE con datos vacíos SÍ se registra
    (no son un diff, son una fotografía). Hay un test que lo fija.
    """
    return accion == "UPDATE" and antes == {} and despues == {}
