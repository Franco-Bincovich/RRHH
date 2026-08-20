"""
La traducción del choque de las unicidades de `empleados` a un `AppError` legible.

Molde: `services/_objetivos_duplicado.py`, que ya resolvió esto para `objetivos`. Se sigue su
forma —SQLSTATE autoritativo, fallback sobre el texto, context manager en el SERVICE— y se
diverge en UN punto, que está explicado abajo.

🔴 POR QUÉ EXISTE. `empleados` tiene TRES unicidades que un dato del formulario puede chocar:

  · `empleados_email_corporativo_key` — sobre `email_corporativo`, **GLOBAL, sin empresa**.
  · `empleados_empresa_dni_uq`        — sobre `(empresa_id, dni)`.
  · `empleados_legajo_empresa_key`    — sobre `(legajo, empresa_id)`.

De las tres, **sólo `legajo` tenía pre-chequeo** (`_empleados_utils.ensure_legajo_unico`, que da
un 409 limpio). Las otras dos no tenían nada: el `.insert()` de `_empleado_write_repo.guardar` no
estaba envuelto, así que la `APIError` de PostgREST subía hasta `global_error_handler`, caía en su
rama de "error inesperado" y el endpoint devolvía **500 INTERNAL_ERROR** — un error de servidor
por un dato que la persona que carga el legajo puede corregir sola. Es el mismo bug, con la misma
causa, que el de objetivos.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 POR QUÉ SE TRADUCE EL ERROR DE LA BASE EN VEZ DE PRE-CHEQUEAR CON UN SELECT
═══════════════════════════════════════════════════════════════════════════════════════════

Un pre-chequeo se lee como la solución obvia —es lo que hace `ensure_legajo_unico`— y **no
alcanza, porque entre el SELECT y el INSERT hay una ventana**. Dos altas simultáneas con el mismo
email preguntan las dos "¿existe?", las dos reciben que no, y las dos insertan. Sin transacción ni
lock —y por PostgREST no hay ninguna de las dos— esa carrera está siempre abierta.

**El constraint es la ÚNICA garantía de unicidad que hay, y por eso la traducción del 23505 es la
red de verdad y el pre-chequeo es sólo un atajo de mensaje.** Los dos conviven a propósito y no se
pisan: el pre-chequeo de legajo evita el round trip cuando el choque es obvio, y esta traducción
atrapa lo que se le escapa —incluida su propia carrera, que sale por el MISMO code
`LEGAJO_DUPLICADO`, así que el cliente no puede notar por cuál de los dos caminos vino—.

Agregarle un pre-chequeo a `email_corporativo` y a `dni` habría costado **dos SELECT por alta**
para tapar el caso fácil dejando el difícil igual de roto. Con esto, cero queries de más.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 LA DIVERGENCIA CON EL MOLDE: ACÁ SÍ SE MIRA EL NOMBRE DE LA CONSTRAINT
═══════════════════════════════════════════════════════════════════════════════════════════

`_objetivos_duplicado.es_choque_de_unicidad` NO mira el nombre, y su docstring explica por qué:
`objetivos` tiene una sola unicidad componible, así que "un 23505 en esta tabla significa una sola
cosa". **Acá significan tres cosas distintas**, y decirle "revisá el DNI" a alguien que repitió el
email sería peor que el 500 que esto viene a sacar: manda a corregir un campo que está bien.

Lo que SÍ se conserva del molde es su conclusión: **un índice único futuro no puede volver a
subir como 500**. Por eso un 23505 con una constraint que esta tabla no conoce sale igual como
409, con el mensaje genérico. Reconocer el nombre elige el MENSAJE; no decide si es un 409.

📄 **La tabla constraint → (mensaje, code) vive en `services/_empleado_constraints.py`**, junto
con las razones de cada mensaje. Salió de acá cuando este archivo llegó a 155/150, y el corte cae
en la costura que este encabezado ya describía: acá está CÓMO se detecta y DÓNDE se envuelve;
allá, QUÉ significa cada constraint para quien carga el alta — que es lo único que crece.

⚠️ NO ES UN `except Exception` A SECAS. Lo que no es un 23505 se re-lanza tal cual: convertir un
timeout o un 42703 en "ya existe un colaborador con ese email" mandaría a corregir un dato que no
tiene nada de malo.
"""
from contextlib import contextmanager

from services._empleado_constraints import traducir as _traducir
from utils.errors import AppError
from utils.logger import logger

# SQLSTATE de unique_violation, el mismo que ya nombra `_objetivos_duplicado`.
_UNIQUE_VIOLATION = "23505"


def _es_choque_de_unicidad(exc: Exception) -> bool:
    """¿Esta excepción es un índice único rebotando, o es cualquier otra cosa?

    Mira el SQLSTATE que PostgREST manda en el body (`APIError.code`), que es el dato
    autoritativo. El fallback sobre el texto NO es defensa por las dudas: cuando la respuesta no
    trae JSON parseable, la librería arma el error con `generate_default_error_message`
    (`postgrest/exceptions.py:43-49`), que pone el **status HTTP** en `code` — y ahí el 23505
    sólo sobrevive dentro del mensaje. Es el mismo criterio, y por el mismo motivo, que
    `_objetivos_duplicado.es_choque_de_unicidad`.
    """
    codigo = getattr(exc, "code", None)
    return codigo == _UNIQUE_VIOLATION or _UNIQUE_VIOLATION in str(exc)


@contextmanager
def duplicado_a_409():
    """Convierte el choque de una unicidad de `empleados` en un 409 con su code. Lo demás intacto.

    🔴 POR QUÉ ENVUELVE EN EL SERVICE Y NO EN EL REPO. El mismo choque llega por DOS caminos —el
    alta y la edición, porque cambiarle el email o el DNI a un empleado puede colisionar con
    otro— y los dos tienen que contestar lo mismo. En el repo habría que envolver `guardar` y
    `actualizar` por separado, o sea dos lugares donde el mensaje puede divergir. Y el import de
    nómina hereda la traducción gratis, porque va por `EmpleadoService.create_empleado`.

    Uso:
        with duplicado_a_409():
            empleado = repo.save(data, empresa_id)

    Raises:
        AppError: EMAIL_CORPORATIVO_DUPLICADO · DNI_DUPLICADO · LEGAJO_DUPLICADO ·
            EMPLEADO_DUPLICADO (409), según qué constraint rebotó.
    """
    try:
        yield
    except AppError:
        # Los AppError ya son la respuesta que queremos: pasan sin tocar. Sin esta rama, un
        # EMPLEADO_NOT_FOUND del repo caería en el `except` de abajo y `_es_choque_de_unicidad`
        # tendría que decidir sobre algo que ya estaba decidido.
        raise
    except Exception as exc:  # noqa: BLE001 — se re-lanza todo lo que no sea el 23505
        if not _es_choque_de_unicidad(exc):
            raise
        error = _traducir(exc)
        logger.warning("Alta/edición de empleado rechazada por una unicidad",
                       extra={"code": error.code, "error": str(exc)})
        raise error from exc
