"""
Traducción de los errores de Pydantic al mensaje que ve alguien de RRHH.

Salió de `middleware/error_handler.py`, que quedaba en 230/200 al sumarle el 422. El corte es
además el natural: acá vive QUÉ DICE el error, y allá QUÉ FORMA tiene la respuesta HTTP. El
handler llama a `mensaje_validacion` con los errores crudos y recibe `(mensaje, code)`.

Un segundo corte, por el mismo motivo (208/200 al sumarle las dos ramas de origen): la
traducción de UN error suelto —qué campo es, qué le pasa— vive en `_problema_campo.py`. Acá
queda la decisión de RAMA y el armado del mensaje sobre la lista entera.

🔴 QUÉ SALE AL CLIENTE Y QUÉ SE QUEDA EN EL LOG — el criterio, para no re-decidirlo:

  SALE: el nombre de la HOJA del campo, humanizado, y qué le pasa. El nombre del campo es parte
    del contrato público del endpoint —el cliente lo acaba de mandar, o tenía que mandarlo—, así
    que nombrarlo no revela nada que no haga falta para usar la API, y es lo único que vuelve el
    mensaje accionable. Sin el campo, "datos inválidos" manda a alguien de RRHH a adivinar cuál
    de doce inputs está mal.

  NO SALE:
    · El `loc` COMPLETO. `body.items.3.empleado.dni` describe cómo está compuesto el schema por
      dentro (anidamiento, listas, submodelos). La hoja alcanza para actuar; el camino solo
      sirve para mapear la estructura desde afuera.
    · El VALOR recibido (`input`). Es el que puede ser una contraseña, un DNI o un sueldo: el
      campo que falla puede ser justamente el sensible. Devolverlo lo pondría además en pantalla,
      y de ahí en un screenshot o un ticket.
    · El `msg`, el `type` y la `url` de Pydantic. Jerga de implementación, cambian entre
      versiones, y la `url` publicita el stack. "Input should be a valid UUID, invalid length:
      expected length 32 for simple format, found 0" no le sirve a nadie de RRHH.

  VA AL LOG (lo arma el handler): el `loc` completo, el `type` y la cantidad — lo que necesita un
    dev para diagnosticar. 🔴 El `input` NO va tampoco al log, por lo mismo de arriba: un
    `password` mal formado escribiría la contraseña en claro en los logs de la plataforma. Mismo
    criterio que el WARNING de `_oauth_state.consumir`, que loguea el rechazo y no el valor
    recibido. (Es lo contrario de `intentos_identificacion`, donde el DNI SÍ se guarda en claro —
    ahí es una decisión tomada y escrita, con el valor forense como motivo.)

🔴 DOS RAMAS, PORQUE SON DOS ERRORES DISTINTOS — y confundirlos le miente al usuario:

  · `loc[0] == "body"` → **lo llenó una persona.** Hay algo que corregir en la pantalla, así que
    se nombra el campo y se le pide que lo revise. Code `VALIDACION_INVALIDA`.

  · `loc[0]` en query/path/header/cookie → **lo armó la APLICACIÓN.** Un `page_size=200`, un
    filtro mal serializado o un id mal formado en la URL no son cosas que el usuario haya
    tipeado: son un bug nuestro. Nombrarle el campo ("page size es demasiado grande") le pide
    arreglar algo que no puede tocar y que ni siquiera sabe que existe — lo manda a buscar un
    input inexistente. Se le dice qué HACER (recargar, avisar) y el campo queda solo en el log,
    que es donde lo va a leer quien sí puede arreglarlo. Code `PEDIDO_INVALIDO`.

  Es exactamente el caso que ya quemó dos veces: `useDestinatarios` y `useCandidatosProyecto`
  pedían `page_size=200` contra un `le=100`. El usuario no tenía nada que corregir.

  · **`loc` MIXTO (body + query en el mismo request) → gana BODY**, y solo se nombran los campos
    del body. Es la rama accionable: si hay algo que la persona puede arreglar, esa información
    vale más que el aviso genérico, y el problema de query queda igual en el log.
"""

from middleware._problema_campo import ORIGENES_DE_LA_APP, campo_legible, problema

MENSAJE_CAMPOS = "Revisá los datos del formulario: {campos}."
MENSAJE_GENERICO = "El pedido tiene datos inválidos. Revisá el formulario e intentá de nuevo."
# No nombra el campo A PROPÓSITO (ver arriba), y pide lo único que el usuario puede hacer.
MENSAJE_PEDIDO = "No se pudo completar el pedido. Actualizá la pantalla y volvé a intentar."
CODE = "VALIDACION_INVALIDA"
CODE_PEDIDO = "PEDIDO_INVALIDO"
_MAX_CAMPOS_VISIBLES = 5

def _hay_origen(errores: list[dict], origenes: frozenset) -> bool:
    """Si algún error vino de alguno de esos orígenes.

    Args:
        errores: `RequestValidationError.errors()`.
        origenes: El conjunto contra el que comparar el primer tramo del `loc`.

    Returns:
        True si al menos un error arranca con uno de esos prefijos.
    """
    return any(
        (loc := e.get("loc", ())) and isinstance(loc[0], str) and loc[0] in origenes
        for e in errores
    )


def _campos_del_body(errores: list[dict]) -> str:
    """Los campos del BODY, formateados, o "" si no hay ninguno nombrable.

    Solo mira los errores de body: con un `loc` mixto los de query no se nombran, porque el
    usuario no puede hacer nada con ellos. Deduplica conservando el orden (un mismo campo puede
    fallar por dos reglas a la vez) y corta en `_MAX_CAMPOS_VISIBLES` para que un body masivo mal
    formado no devuelva un párrafo.

    Args:
        errores: `RequestValidationError.errors()`.

    Returns:
        "empresa (falta), nombre (es demasiado largo)", o "".
    """
    vistos: dict[str, str] = {}
    for err in errores:
        loc = err.get("loc", ())
        if not (loc and loc[0] == "body"):
            continue
        campo = campo_legible(loc)
        if campo and campo not in vistos:
            vistos[campo] = problema(err)
    if not vistos:
        return ""
    items = [f"{c} ({p})" for c, p in list(vistos.items())[:_MAX_CAMPOS_VISIBLES]]
    resto = len(vistos) - len(items)
    if resto > 0:
        items.append(f"y {resto} campo{'s' if resto > 1 else ''} más")
    return ", ".join(items)


def mensaje_validacion(errores: list[dict]) -> tuple[str, str]:
    """Arma el mensaje visible y el `code`, ramificando por el ORIGEN del dato inválido.

    Las dos ramas y por qué existen están en el encabezado del módulo. En orden de prioridad:
    body (hay algo que la persona puede corregir) → query/path/header (lo armó la app, no se
    nombra el campo) → genérico.

    Args:
        errores: `RequestValidationError.errors()`.

    Returns:
        `(mensaje, code)` para el usuario final.
    """
    campos = _campos_del_body(errores)
    if campos:
        return MENSAJE_CAMPOS.format(campos=campos), CODE
    # Sin campos de body nombrables: si el problema vino de la URL o de un header, el usuario no
    # tiene nada que corregir. Un body ilegible (`loc` = solo `("body",)`) sigue siendo suyo.
    if not _hay_origen(errores, frozenset({"body"})) and _hay_origen(errores, ORIGENES_DE_LA_APP):
        return MENSAJE_PEDIDO, CODE_PEDIDO
    return MENSAJE_GENERICO, CODE
