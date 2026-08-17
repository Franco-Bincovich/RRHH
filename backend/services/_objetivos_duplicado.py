"""
La traducción del choque del índice único de `objetivos` a un `AppError` legible.

Vive aparte de `_objetivos_validaciones.py` porque es otra CLASE de cosa: aquéllas son
validaciones de campo que corren ANTES de escribir y miran un valor; ésta es la traducción del
error que devuelve la base DESPUÉS de intentar escribir, y no puede correr antes porque la
unicidad sólo la sabe el índice. Con este bloque adentro, aquel archivo quedaba en 168 contra un
tope de 150.

🔴 POR QUÉ EXISTE, y es lo que más importa de este archivo. Las migraciones **111 y 114 afirman
las dos, textualmente, que "el service traduce el 23505 a su propio error"** — y no era cierto:
nunca hubo una línea de código que lo hiciera (grep de `23505` y de "duplicate key" en
`backend/`, verificado el 17/8: cero fuera de las migraciones). Lo que pasaba de verdad:

  · **En el alta manual**, el `.insert()` de `objetivo_repo.save` no estaba envuelto, así que la
    `APIError` de PostgREST subía hasta `global_error_handler` y el endpoint devolvía **500
    INTERNAL_ERROR** — un error de servidor por un dato que el usuario puede corregir solo.
  · **En el import**, `objetivos_import_service.confirmar` la atrapa con su `except Exception` y
    ponía en el reporte de la fila el texto crudo de Postgres: "duplicate key value violates
    unique constraint ux_objetivo_responsable_titulo".

Ninguna de las dos es lo que la migración prometía, y las dos venían de semanas atrás.
"""
from contextlib import contextmanager

from utils.errors import AppError
from utils.logger import logger

# SQLSTATE de unique_violation. Es el código que PostgREST devuelve en el body cuando choca un
# índice único, y el que las migraciones 111, 114 y 119 nombran en sus verificaciones.
_UNIQUE_VIOLATION = "23505"

# 🔴 El mensaje NOMBRA LAS TRES SALIDAS, y por eso es largo. La clave del índice es
# (empresa, responsable, título, periodicidad, tipo): un mensaje que dijera sólo "ya existe" deja
# a alguien de RRHH cambiando el título —que es lo único obvio— cuando en general lo que quiere es
# cargarlo en la otra vista. Las tres salidas son las tres columnas que puede tocar.
MSG_DUPLICADO = (
    "Ya existe un objetivo con ese título para ese responsable, con la misma periodicidad y en "
    "la misma vista. Cambiá el título, poné otra periodicidad, o cargalo en la otra vista "
    "(anual / operativos)."
)


def es_choque_de_unicidad(exc: Exception) -> bool:
    """¿Esta excepción es el índice único rebotando, o es cualquier otra cosa?

    Mira el SQLSTATE que PostgREST manda en el body (`APIError.code`), que es el dato
    autoritativo. El fallback sobre el texto NO es defensa por las dudas: cuando la respuesta no
    trae JSON parseable, la librería arma el error con `generate_default_error_message`
    (`postgrest/exceptions.py:43-49`), que pone el **status HTTP** en `code` — y ahí el 23505
    sólo sobrevive dentro del mensaje.

    🔑 ALCANZA CON EL CÓDIGO, sin mirar el nombre de la constraint, y es a propósito:
    `objetivos` tiene exactamente DOS índices únicos, su pkey (un uuid generado, que no puede
    chocar) y `ux_objetivo_responsable_titulo`. Un 23505 en esta tabla significa una sola cosa.
    Atarlo al nombre haría que un índice único futuro subiera como 500 en vez de como el 409 que
    ya le corresponde.

    Args:
        exc: La excepción que levantó el repo.

    Returns:
        True si es una violación de unicidad.
    """
    codigo = getattr(exc, "code", None)
    return codigo == _UNIQUE_VIOLATION or _UNIQUE_VIOLATION in str(exc)


@contextmanager
def duplicado_a_409():
    """Convierte el choque del índice único en `OBJETIVO_DUPLICADO` (409). Lo demás pasa intacto.

    🔴 POR QUÉ ENVUELVE EN EL SERVICE Y NO EN EL REPO. El mismo choque llega por DOS caminos —el
    alta y la edición, porque cambiarle el título o el tipo a un objetivo puede colisionar con
    otro— y los dos tienen que contestar lo mismo. En el repo habría que envolver `save` y
    `update` por separado, o sea dos lugares donde el mensaje puede divergir. Y el import hereda
    la traducción gratis, porque va por `ObjetivoService.create`.

    ⚠️ NO ES UN `except Exception` A SECAS, al revés que `_carga_licencia.py:85-90`, que traduce
    CUALQUIER excepción del insert a "licencia duplicada". Esa forma es aceptable allá (una tabla
    con una sola constraint y un solo camino de escritura), pero acá convertiría un timeout o un
    42703 en un 409 que le dice al usuario que cambie el título de algo que no está duplicado.
    Lo que no es un 23505 **se re-lanza tal cual** y sigue su camino normal.

    Uso:
        with duplicado_a_409():
            row = self._repo.save(data)

    Raises:
        AppError: OBJETIVO_DUPLICADO (409) si chocó el índice único.
    """
    try:
        yield
    except AppError:
        # Los AppError ya son la respuesta que queremos: pasan sin tocar. Sin esta rama, un
        # OBJETIVO_NOT_FOUND del repo caería en el `except` de abajo y `es_choque_de_unicidad`
        # tendría que decidir sobre algo que ya estaba decidido.
        raise
    except Exception as exc:  # noqa: BLE001 — se re-lanza todo lo que no sea el 23505
        if not es_choque_de_unicidad(exc):
            raise
        logger.warning("Objetivo duplicado rechazado por el índice único",
                       extra={"error": str(exc)})
        raise AppError(MSG_DUPLICADO, "OBJETIVO_DUPLICADO", 409) from exc
