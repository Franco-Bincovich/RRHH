"""
De una excepción del proveedor de IA al motivo que ve RRHH. El detalle técnico queda en el log.

## 🔴 EL BUG QUE ESTO CIERRA

En producción, una corrida sin saldo dejó esto escrito en la ficha de un candidato:

    No se pudo clasificar: Error code: 400 - {'type': 'error', 'error': {'type':
    'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic
    API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011C…'}

Tres cosas mal a la vez: **no le dice a RRHH qué hacer**, está **en inglés**, y **expone detalle
interno del proveedor** —`request_id`, tipo de error, el nombre de la API— en una pantalla de
Recursos Humanos. Es el mismo criterio que ya se aplicó en `require_empresa_id`, que decía
"empresa_id requerido" y pasó a explicar la acción.

El resto de las integraciones del repo ya lo hacían bien (`"Error al consultar Gmail"`,
`"No se pudo enviar el mail"`): el clasificador quedó afuera porque su fallo **se persiste** en
vez de levantar un `AppError`, y nadie llevó el criterio hasta ese camino.

## 🔴 QUÉ SE PUEDE DISTINGUIR DE VERDAD, Y QUÉ NO

Verificado contra el SDK instalado (`anthropic==0.34.2`):

  · **NO existe `.type` en las excepciones.** Esa property es de SDKs posteriores; acá
    `APIStatusError` solo trae `args`. No se puede leer el `error.type` del cuerpo sin parsearlo.
  · Las **clases** sí distinguen, y con eso alcanza para tres de las cuatro categorías:
    `RateLimitError` (429), `InternalServerError` (5xx/529), `APIConnectionError` y su hija
    `APITimeoutError`, `AuthenticationError` (401), `PermissionDeniedError` (403).

🟡 **La de saldo es la única que NO se puede distinguir por clase, y hay que decirlo.** El error
de facturación llega como **`BadRequestError` (400)** con `error.type='invalid_request_error'` —
exactamente el mismo par que una request malformada por un bug nuestro. El único señalizador es
el TEXTO del proveedor, así que se busca por marcas (`_MARCAS_SALDO`). Es best-effort:

  · Si el proveedor cambia el wording, un caso de saldo cae en `configuracion` — que igual manda
    a avisarle a quien administra, o sea la acción correcta con menos detalle. **Degrada bien.**
  · Un 400 que NO matchee cae en `configuracion` y no en "reintentá": un 400 nunca se arregla
    reintentando, y mandar a RRHH a apretar el botón diez veces es peor que no decir nada.

Nunca se cae a `desconocido` desde un 400: el fallback de la familia HTTP es el que sabe que
reintentar no sirve.

## Lo que NO se pierde

`str(exc)` completo —con `request_id` incluido— va al log en `_screening_candidato`, junto con la
clase de la excepción y la categoría resuelta. Ahí sirve: es lo que permite pedirle a Anthropic
que rastree un request puntual. En la ficha del candidato no le sirve a nadie.
"""
from typing import Tuple

import anthropic

#: Marcas de facturación dentro del mensaje del proveedor. Minúsculas, se compara en minúsculas.
#: Cubren el texto real visto en producción ("credit balance", "Plans & Billing", "credits") y
#: las variantes habituales. Ver el encabezado: esto es best-effort a propósito.
_MARCAS_SALDO: Tuple[str, ...] = (
    "credit balance", "credits", "billing", "quota", "insufficient", "payment", "saldo",
)

#: El prefijo estable del motivo. Sirve en el export, donde la columna "Clasificación" dice
#: "Sin clasificar" y esta es la que explica por qué. Los mensajes continúan la frase.
PREFIJO_FALLO = "No se pudo clasificar"

MENSAJES = {
    "saldo": "el servicio se quedó sin saldo. Avisale a quien administra el sistema para que lo "
             "recargue, y después volvé a apretar el botón.",
    "sobrecarga": "el servicio está sobrecargado en este momento. Probá de nuevo en unos minutos.",
    "conexion": "no se pudo conectar con el servicio. Probá de nuevo en unos minutos.",
    "configuracion": "el servicio no está habilitado para este sistema. Avisale a quien "
                     "administra el sistema; reintentar no lo va a resolver.",
    "desconocido": "el servicio no está disponible. Probá de nuevo en unos minutos y, si sigue "
                   "igual, avisale a quien administra el sistema.",
}


def categoria_de(exc: BaseException) -> str:
    """La categoría del fallo. Se resuelve por CLASE salvo el saldo — ver el encabezado."""
    # El orden importa: `APITimeoutError` hereda de `APIConnectionError`, y las de status
    # heredan todas de `APIStatusError`. Se va de lo específico a lo general.
    if isinstance(exc, (anthropic.RateLimitError, anthropic.InternalServerError)):
        return "sobrecarga"
    if isinstance(exc, anthropic.APIConnectionError):  # incluye APITimeoutError
        return "conexion"
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return "configuracion"
    if isinstance(exc, anthropic.BadRequestError):
        # 🟡 Lo único que separa "sin saldo" de "armamos mal el request" es el texto. Ver arriba.
        texto = str(exc).lower()
        return "saldo" if any(m in texto for m in _MARCAS_SALDO) else "configuracion"
    if isinstance(exc, anthropic.APIStatusError):
        # Otro status (409, 404, 422…): no es de red ni de saldo, y reintentar no lo arregla.
        return "configuracion"
    return "desconocido"


def motivo_de(exc: BaseException) -> str:
    """El texto que se PERSISTE en `clasificacion_motivo` y que RRHH lee en la ficha.

    🔴 No concatena `str(exc)`. Es la regla entera de este módulo: el mensaje del proveedor no
    entra en la pantalla ni en la base, va al log.
    """
    return f"{PREFIJO_FALLO}: {MENSAJES[categoria_de(exc)]}"
