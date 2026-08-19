"""
La traducción del choque de unicidad de `empleado_capacitacion` a un error legible por fila.

Molde: `_objetivos_duplicado.py`, del que se IMPORTA `es_choque_de_unicidad` en vez de
reescribirla — es la detección del 23505 con su fallback documentado sobre el texto, y dos
copias que se separen darían dos criterios sobre lo mismo (mismo argumento que `sin_derivados`).

🔴 POR QUÉ EXISTE. A4.1 dejó inventariadas las dos unicidades de esta tabla SIN protección
(`UNIQUE (capacitacion_id, empleado_id)` y la parcial `ux_ec_nombre_libre`), y el import del
Excel es exactamente quien las choca: reimportar el mismo archivo —el caso normal, alguien
reintenta porque no sabe si la primera corrida terminó— rebotaría fila por fila con el texto
crudo de Postgres, o peor, un 500. Con esto, el reimport reporta duplicados legibles y no
duplica nada.

🔑 UN SOLO MENSAJE PARA LOS DOS ÍNDICES, a propósito: los dos significan "esa persona ya tiene
esa formación cargada" (el parcial agrega año y mes a la clave para los nombres sueltos). El
SQLSTATE alcanza sin mirar el nombre de la constraint — mismo argumento que objetivos: atarlo
al nombre haría que un índice futuro suba como 500 en vez de como el 409 que le corresponde.
"""
from contextlib import contextmanager

from services._objetivos_duplicado import es_choque_de_unicidad
from utils.errors import AppError
from utils.logger import logger

MSG_DUPLICADO = (
    "Esa persona ya tiene esta formación cargada (misma formación; para un nombre suelto, "
    "también mismo año y mes). Si esto es un reimport del mismo archivo, la fila ya estaba y "
    "no se duplica."
)


@contextmanager
def duplicado_legible():
    """Convierte el choque del índice único en `FORMACION_DUPLICADA` (409). Lo demás pasa intacto.

    ⚠️ NO es un `except Exception` que traduce todo (la forma de `_carga_licencia` que
    `_objetivos_duplicado` descarta con razón): lo que no es un 23505 se re-lanza tal cual —
    un 42703 disfrazado de "duplicado" le diría a RRHH que la fila ya estaba cuando en realidad
    el import está roto.
    """
    try:
        yield
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 — se re-lanza todo lo que no sea el 23505
        if not es_choque_de_unicidad(exc):
            raise
        logger.warning("Asignación de formación duplicada rechazada por índice único",
                       extra={"error": str(exc)})
        raise AppError(MSG_DUPLICADO, "FORMACION_DUPLICADA", 409) from exc
