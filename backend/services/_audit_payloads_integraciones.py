"""
Payloads canónicos de los eventos de auditoría de las integraciones por usuario.

🔴 EL EVENTO QUE JUSTIFICA EL ARCHIVO ES LA DESCONEXIÓN. `integracion_service.disconnect` borra
FÍSICAMENTE la credencial (tokens de Google o API key), y el barrido nº 42 lo tenía declarado como
DEUDA con la frase que resume el caso: *"que alguien haya desconectado la casilla del sistema es
justo lo que hay que poder averiguar cuando los mails dejan de salir"*. Los otros tres eventos
existen porque `tests/test_auditoria_coherente.py` exige que un módulo que audita ALGO audite
TODO — y porque conectar es tan interesante como desconectar.

═══════════════════════════════════════════════════════════════════════════════
🔴 NINGÚN PAYLOAD DE ESTE ARCHIVO TOCA UN SECRETO, Y NO ES UNA PRECAUCIÓN: ES LA REGLA.
═══════════════════════════════════════════════════════════════════════════════
`integraciones` guarda `access_token`, `refresh_token` y `api_key`. `auditoria` es una tabla
INMUTABLE por diseño (nada la borra ni la edita), la lee cualquier `admin_rrhh` desde
`/auditoria`, y sus filas salen en los exports. Un token filtrado ahí adentro no se puede
retractar: quedaría para siempre, legible, y rotando la credencial en Google **el registro
seguiría estando**. Por eso los payloads enumeran campos con `_CAMPOS` en vez de volcar la fila,
que es la forma que NO se rompe sola el día que la tabla gane una columna con otro secreto: con
una lista de exclusión, esa columna nueva entraría al log sin que nadie lo decida.

Lo que sí entra —`tipo`, `email_cuenta`, `activo`, `es_remitente_sistema`, `scopes`— es lo que
permite contestar las preguntas reales: *qué* cuenta era, *si* era la casilla del sistema, y *con
qué permisos*. `scopes` es una lista de URLs de permiso de Google, no una credencial.

⚠️ `empresa_id` VA NULL EN LOS CUATRO, y es lo mismo que hacen los eventos de usuarios: una
integración cuelga de un `user_id`, no de una empresa (el `DELETE /{tipo}` del router está
declarado NO APLICA en la barrera de empresa justamente por eso). Etiquetarla con la empresa del
header diría "esta casilla es de la empresa A" solo porque el operador tenía A en el sidebar.
"""
from typing import Optional
from uuid import uuid4

from services.audit_service import _jsonable

_ENTIDAD = "integracion"

# Lo único que se fotografía. Ver el encabezado: es una ALLOWLIST a propósito, nunca una
# exclusión — `access_token`, `refresh_token` y `api_key` no se nombran ni para excluirlos.
_CAMPOS = ("tipo", "email_cuenta", "activo", "es_remitente_sistema", "scopes")

_SIN_EMPRESA = None


def _subset(fila, campos: tuple) -> dict:
    """Extrae `campos` de un dict (o modelo Pydantic) como dict JSON-serializable."""
    data = fila.model_dump() if hasattr(fila, "model_dump") else dict(fila or {})
    return {k: _jsonable(data.get(k)) for k in campos}


def payload_conexion_integracion(fila, usuario_id: Optional[str]) -> dict:
    """Evento INSERT de conectar una integración (OAuth de Google o guardar una API key).

    🔴 `registro_id` ES UN `uuid4()` DE EVENTO, NO EL ID DE LA FILA. Es el mismo criterio que
    `payload_importacion_nomina`: `save_api_key` es un UPSERT que no devuelve el id de la fila
    resultante, así que no hay id de recurso disponible en el momento de auditar. Poner el
    `user_id` ahí sería peor —`registro_id` es un uuid y el INSERT entraría, pero el log diría
    que el recurso tocado es el usuario, que no es cierto—. El `usuario_id` ya identifica de
    quién es, y `datos_nuevos.tipo` dice cuál de las tres.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(uuid4()),
        "accion": "INSERT", "evento": "conexion_integracion", "empresa_id": _SIN_EMPRESA,
        "datos_anteriores": None, "datos_nuevos": _subset(fila, _CAMPOS),
    }


def payload_remitente_sistema(fila, usuario_id: Optional[str]) -> dict:
    """Evento UPDATE de designar una casilla de Google como remitente DEL SISTEMA.

    EVENTO PROPIO Y NO `conexion_integracion`: designar la casilla no conecta nada, cambia de
    QUIÉN salen todos los mails del producto. Es el cambio de configuración de mayor alcance del
    módulo —lo hace un usuario y le cambia el remitente a todos— y tiene que poder filtrarse
    solo desde `/auditoria`. Mismo criterio que `cambio_estado_objetivo` contra `update_objetivo`.

    `datos_anteriores` va NULL a propósito: `set_remitente` desmarca la casilla vigente y marca la
    nueva en dos UPDATE sin transacción, y el service no lee cuál era la anterior. Afirmar un
    "antes" que no se leyó sería inventarlo; lo que el evento sostiene es cuál quedó.
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(uuid4()),
        "accion": "UPDATE", "evento": "designacion_remitente_sistema", "empresa_id": _SIN_EMPRESA,
        "datos_anteriores": None, "datos_nuevos": _subset(fila, _CAMPOS),
    }


def payload_baja_integracion(prior, tipo: str, usuario_id: Optional[str]) -> dict:
    """Evento DELETE de desconectar una integración. Borrado FÍSICO de la credencial.

    🔴 ESTA FOTO ES LO ÚNICO QUE QUEDA. La fila se va entera y con ella el `email_cuenta`: sin el
    evento, cuando los mails dejan de salir no hay forma de saber si la casilla se desconectó, ni
    quién, ni cuál era. `era_remitente_del_sistema` viaja explícito porque es la diferencia entre
    "un usuario desconectó su Gmail" y "se cayó el envío de todo el producto".

    `tipo` se pasa aparte además de venir en el subset: es el único dato que sobrevive si el
    `prior` no se pudo leer (el service audita igual, con `prior=None`, antes que perder el
    evento — el hecho de que alguien desconectó algo vale más que el detalle de qué).
    """
    return {
        "usuario_id": usuario_id, "entidad": _ENTIDAD, "registro_id": str(uuid4()),
        "accion": "DELETE", "evento": "baja_integracion", "empresa_id": _SIN_EMPRESA,
        "datos_anteriores": {**_subset(prior, _CAMPOS), "tipo": tipo,
                             "era_remitente_del_sistema": bool(
                                 (prior or {}).get("es_remitente_sistema"))},
        "datos_nuevos": None,
    }
