"""
LA CASILLA DEL SISTEMA como origen de las credenciales de Google: una sola resolución para el
envío de mails y para la lectura de postulaciones.

Extraído de `services/mailer/engine.py`, que lo tenía embebido y estaba en 141/150.

## 🔴 EL CORTE ES POR LO QUE SE COMPARTE, no por líneas

Hasta hoy esto lo usaba un solo caso de uso (mandar un mail). Con la lectura de CVs pasan a ser
dos, y si la lectura se copiara su propia versión, cualquier arreglo de la resolución del
remitente quedaría hecho en un lado solo — el modo de falla que este repo ya pagó con los
filtros duplicados front/back y que `_google_token.py` documenta con las mismas palabras.

## 🔴 NO HAY FALLBACK A "LA CUENTA DEL QUE APRETÓ EL BOTÓN", Y ES DELIBERADO

Es la decisión que este módulo existe para hacer cumplir en los DOS caminos:

  · **Con fallback, el resultado depende de quién pregunta.** En la lectura eso significa que a
    un usuario le aparecen CVs y a otro no, sobre la misma vacante, sin ningún error — y nadie
    puede explicar por qué. Hoy no se nota porque hay UNA sola integración en la base y esa fila
    es a la vez la del usuario y la marcada `es_remitente_sistema`: las dos rutas resuelven al
    mismo buzón por casualidad. Se rompe el día que un segundo usuario conecte su Google.
  · **Un proceso automático no tiene `user_id` que aportar.** Sin esto, la automatización futura
    del CV screening es directamente imposible: no hay a quién pedirle el token.
  · **El circuito de prueba y el real tienen que ser el mismo.** Es el argumento textual por el
    que se creó la casilla del sistema para el envío (ver `integracion_remitente_repo`).

Mejor un error que dice qué hacer que un fallback que adivina.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service.
"""
from typing import Optional

from services._google_token import access_token_valido
from utils.errors import AppError

# Los dos mensajes son distintos A PROPÓSITO: nombran la consecuencia concreta de que falte la
# casilla en cada camino. "No se pueden enviar mails" y "no se pueden leer postulaciones" mandan
# a la misma pantalla, pero el que lo lee está haciendo cosas distintas y necesita saber cuál se
# le rompió. La segunda mitad de la frase —a dónde ir— sí es idéntica: es la misma acción.
_DONDE = "Conectá una cuenta de Gmail en Configuración y marcala como casilla del sistema."
MSG_ENVIO = f"No hay una casilla de correo configurada para enviar. {_DONDE}"
MSG_LECTURA = f"No hay una casilla de correo configurada para recibir postulaciones. {_DONDE}"


def fila_o_error(repo, mensaje: str, code: str) -> dict:
    """La fila entera de la casilla del sistema, o un `AppError` accionable.

    Args:
        repo: IntegracionRemitenteRepo (o doble) con `get_remitente()`.
        mensaje: qué se rompió y dónde arreglarlo (ver MSG_ENVIO / MSG_LECTURA).
        code: código del error, propio de cada camino.

    Raises:
        AppError: `code` (400) si no hay casilla designada, o si la que hay no tiene `user_id`.
    """
    fila = repo.get_remitente()
    # El `user_id` se exige además de la fila: `get_remitente` trae la integración ENTERA y de
    # ahí sale el dueño con el que se renueva el token. Una fila sin él no sirve para nada, y
    # fallar acá da el mensaje accionable en vez de un KeyError más abajo.
    if not fila or not fila.get("user_id"):
        raise AppError(mensaje, code, 400)
    return fila


def repo_de(remitente: dict):
    """Adapta la fila del remitente a lo que `access_token_valido` espera de un repo.

    La fila YA tiene los tokens (`get_remitente` trae la integración entera), así que volver a
    consultarla por `user_id` sería una query de más en el camino de cada mail de un lote.
    `actualizar_token` sí delega en el repo real: el token renovado tiene que persistirse.
    """
    from repositories.integracion_repo import IntegracionRepo

    real = IntegracionRepo()

    class _Fija:
        def get_by_user_and_tipo(self, user_id, tipo):
            return remitente

        def actualizar_token(self, user_id, access_token, token_expiry):
            real.actualizar_token(user_id, access_token, token_expiry)

    return _Fija()


def token_de_lectura(remitente_repo, mensaje: Optional[str] = None) -> str:
    """Un access_token vigente de la casilla del sistema, para LEER el buzón.

    Atajo de `fila_o_error` + `repo_de` + `access_token_valido` para los callers que solo
    necesitan el token y no la fila. El envío no lo usa porque además necesita el
    `email_cuenta` para el log, y porque pide el token DENTRO de su try para registrar el fallo.

    Raises:
        AppError: GMAIL_SIN_CASILLA (400) si no hay casilla del sistema designada.
        AppError: GMAIL_NOT_CONFIGURED (400) — de `_google_token`.
        AppError: GMAIL_TOKEN_EXPIRED (502) | GMAIL_RENOVACION_FALLIDA (502) — íd. 🔴 Son 502
            y no 401: una integración caída no es una sesión vencida, y el front leía ese 401
            como 'te venció la sesión' y deslogueaba. Ver `services/_google_token_fallo.py`.
    """
    fila = fila_o_error(remitente_repo, mensaje or MSG_LECTURA, "GMAIL_SIN_CASILLA")
    return access_token_valido(repo_de(fila), fila["user_id"])
