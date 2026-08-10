"""
Traducción de UN error de Pydantic: qué campo es y qué le pasa, en castellano.

Salió de `_mensaje_validacion.py`, que quedaba en 208/200 al sumarle las dos ramas de origen. El
corte es el natural y no solo aritmético: acá vive **un error suelto → un par (campo, problema)**,
y allá **una lista de errores → el mensaje y el code**. Este módulo no sabe nada de ramas ni de
mensajes; aquél no sabe nada de los `type` de Pydantic.

🔴 EL CRITERIO DE QUÉ SE EXPONE ESTÁ EN `_mensaje_validacion.py` — leerlo antes de tocar esto.
Lo que importa acá: se devuelve la HOJA del campo, nunca el camino, y `_problema` MIRA el valor
recibido pero jamás lo devuelve.
"""

# Los `type` de Pydantic v2 son un vocabulario CERRADO y chico, así que traducirlos es una tabla
# que no envejece. Los NOMBRES de campo, en cambio, son 58 tablas de columnas: ahí no hay tabla
# posible —una lista curada mentiría por omisión en cuanto alguien agregue una columna— y por eso
# el nombre se humaniza con una REGLA (`campo_legible`), no con un diccionario.
_PROBLEMAS: dict[str, str] = {
    "missing": "falta",
    "string_too_short": "está vacío",
    "string_too_long": "es demasiado largo",
    "too_short": "tiene muy pocos elementos",
    "too_long": "tiene demasiados elementos",
    "greater_than": "es demasiado chico",
    "greater_than_equal": "es demasiado chico",
    "less_than": "es demasiado grande",
    "less_than_equal": "es demasiado grande",
    "enum": "tiene un valor no permitido",
    "literal_error": "tiene un valor no permitido",
    "value_error": "no es válido",
    "json_invalid": "no tiene un formato válido",
    "extra_forbidden": "no corresponde acá",
}
_PROBLEMA_POR_DEFECTO = "tiene un formato inválido"
_VACIO = "falta"

# Prefijos que Pydantic pone al principio del `loc` para decir DE DÓNDE salió el dato. No son
# campos, así que no se muestran.
ORIGENES = frozenset({"body", "query", "path", "header", "cookie"})
# Los que NO escribe una persona: los arma el front. `cookie` va acá por el mismo motivo que
# `header` — si algún día se valida una, tampoco la tipeó nadie.
ORIGENES_DE_LA_APP = frozenset({"query", "path", "header", "cookie"})


def campo_legible(loc: tuple) -> str:
    """Nombre mostrable del campo que falló, a partir del `loc` de Pydantic.

    Se queda con la HOJA (el último tramo de texto) y descarta el camino: los índices de lista y
    los submodelos intermedios describen la estructura del schema, no le dicen nada al usuario.
    `("body", "items", 3, "fecha_desde")` → `"fecha desde"`.

    La humanización es una REGLA y no una tabla, para que una columna nueva quede cubierta sola:
    se saca el sufijo `_id` (el usuario eligió "empresa" en un select, no un `empresa_id`) y los
    separadores pasan a espacios.

    Args:
        loc: La tupla `loc` de un error de Pydantic.

    Returns:
        El campo humanizado, o "" si el error no apunta a ningún campo (p. ej. un body que no es
        JSON válido, donde `loc` es solo `("body",)`).
    """
    tramos = [p for p in loc if isinstance(p, str)]
    if tramos and tramos[0] in ORIGENES:
        tramos = tramos[1:]
    if not tramos:
        return ""
    hoja = tramos[-1]
    if len(hoja) > 3 and hoja.endswith("_id"):
        hoja = hoja[:-3]
    return hoja.replace("_", " ").replace("-", " ").strip()


def problema(err: dict) -> str:
    """Qué le pasa al campo, en castellano.

    Un valor vacío o ausente se reporta como "falta" cualquiera sea el `type`: para quien llena
    un formulario, un `uuid_parsing` sobre `""` es un campo sin completar, no un formato raro.
    Esto MIRA el valor recibido pero no lo devuelve — el criterio prohíbe exponerlo, no
    inspeccionarlo.

    Args:
        err: Un elemento de `RequestValidationError.errors()`.

    Returns:
        Frase corta que completa "<campo> ...".
    """
    if err.get("input", None) in (None, "", [], {}):
        return _VACIO
    return _PROBLEMAS.get(err.get("type", ""), _PROBLEMA_POR_DEFECTO)
