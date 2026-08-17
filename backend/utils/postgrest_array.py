r"""
Cómo se le pasa un valor a `.contains()` de PostgREST sin que una coma lo parta en dos.

(Este docstring es RAW —lleva el prefijo `r`— porque nombra la barra invertida como carácter:
sin ese prefijo, Python la lee como el arranque de un escape y avisa con un SyntaxWarning en cada
import. Y por eso mismo acá no se escribe el delimitador de comillas triples ni entre backticks:
adentro de un docstring, ESCRIBIRLO LO CIERRA — el archivo dejó de compilar la primera vez.)

🔴 EL PROBLEMA, VERIFICADO EN EL CÓDIGO DE LA LIBRERÍA INSTALADA
(`postgrest/base_request_builder.py:451-454`):

    if not isinstance(value, dict) and isinstance(value, Iterable):
        stringified_values = ",".join(value)
        return self.filter(column, Filters.CS, f"{{{stringified_values}}}")

O sea: `.contains("areas", ["Legales, Compliance"])` arma `cs.{Legales, Compliance}`, que
PostgREST parsea como **DOS elementos**. La consulta pasa a significar "que contenga Legales Y
Compliance", no encuentra nada, y **no hay error**: devuelve cero filas y el filtro miente. Lo
mismo con un valor que traiga `"`, `\`, `{` o `}`.

Un área llamada "Legales, Compliance" no es rebuscada: `areas_involucradas` es texto que RRHH
escribe, y hasta la migración 119 la columna ERA texto libre con comas adentro — el import y la
pantalla vienen justamente de ahí.

LA SALIDA: armar el literal de array a mano, SIEMPRE con comillas, y pasarlo como `str`. Esa
rama de la librería (`:447-450`) manda el string verbatim, así que lo que se escribe acá es
exactamente lo que viaja.

⚠️ SE COMILLA SIEMPRE, no sólo cuando hace falta. Un `if` que decidiera cuándo comillar sería una
segunda regla que mantener sincronizada con la de Postgres, y la primera vez que se equivoque va
a ser con un carácter que nadie probó. Postgres acepta un elemento comillado aunque no lo
necesite: `{"Sistemas"}` y `{Sistemas}` son el mismo array de un elemento.

🔴 VIVE EN `utils/` Y NO EN `repositories/`, y la razón es doble.
  · **De fondo:** no tiene nada de objetivos ni de ninguna tabla, y **no toca la base**. Es la
    traducción de un valor de Python a la sintaxis de un array de PostgREST — una función pura de
    strings, sin dependencias, que es exactamente lo que vive en `utils/`. Hoy la usa un solo
    filtro (`_objetivo_filtros`, el primer `text[]` filtrable del sistema); el segundo la va a
    usar sin volver a razonar el escapado.
  · **Y la que decidió el archivo:** en `repositories/` el límite son 100 líneas —un `_*.py` ahí
    adentro ES un repositorio, no hereda los 200 de "otros"— y esto son 104. La salida NO era
    recortar el encabezado: lo único valioso de este módulo es la explicación del bug que evita,
    porque la función en sí son ocho líneas que cualquiera escribiría mal de nuevo sin ella.

🚩 PARA EL PORTEO A ASYNCPG: **ESTE ARCHIVO DESAPARECE.** Todo lo que hace es esquivar una
limitación del cliente HTTP de PostgREST. Con asyncpg la lista se pasa como PARÁMETRO
(`WHERE areas_involucradas @> $1` con `["Legales, Compliance"]`) y el driver la serializa por el
protocolo binario: no hay literal que armar, no hay comas que comillar y no hay nada que escapar.
Borrarlo entonces es correcto; borrarlo antes reintroduce el bug.
"""
from typing import List

# El orden de los dos reemplazos NO es intercambiable: la barra invertida va PRIMERO. Al revés,
# el `\` que se agrega al escapar la comilla se volvería a escapar en la segunda pasada y saldría
# `\\"` — una barra literal seguida del cierre de comillas, o sea el elemento partido al medio.
_ESCAPES = (("\\", "\\\\"), ('"', '\\"'))


def literal_array(valores: List[str]) -> str:
    """Lista de Python → literal de array de Postgres, listo para `.contains(col, <esto>)`.

    Se pasa el RESULTADO como string, no la lista: la rama de lista de la librería concatena con
    comas sin comillar y parte cualquier valor que traiga una. Ver el encabezado del módulo.

    Args:
        valores: los elementos, tal como los escribió el usuario. Lista vacía → `{}`.

    Returns:
        El literal, con cada elemento entre comillas dobles y escapado.

        >>> literal_array(["Sistemas"])
        '{"Sistemas"}'
        >>> literal_array(["Legales, Compliance"])
        '{"Legales, Compliance"}'
    """
    elementos = []
    for v in valores:
        for viejo, nuevo in _ESCAPES:
            v = v.replace(viejo, nuevo)
        elementos.append(f'"{v}"')
    return "{" + ",".join(elementos) + "}"


def como_lo_manda_la_libreria(valores: List[str]) -> str:
    """Lo que `.contains(col, <lista>)` pone en el cable: `",".join` SIN comillar.

    🔴 NO ES UNA ALTERNATIVA A `literal_array` — ES EL BUG, REPRODUCIDO A PROPÓSITO. Copia
    exactamente `postgrest/base_request_builder.py:451-454`, y existe para que los fakes de test
    puedan modelar la diferencia entre pasar una lista y pasar el literal comillado. Sin esto, un
    doble que recibiera la lista y la usara tal cual sería MÁS INDULGENTE que PostgREST: el test
    del área con coma pasaría en verde con el repo mandando la lista cruda, que es justamente la
    forma rota.

    No la use código de producción. El repo manda `literal_array`.
    """
    return "{" + ",".join(valores) + "}"


def elementos_de(literal: str) -> List[str]:
    """El inverso de `literal_array`: `'{"a","b"}'` → `["a", "b"]`.

    🔴 EXISTE PARA LOS FAKES DE TEST, y por eso vive al lado del encoder en vez de en el fake.
    Un doble de Supabase que implemente `.contains()` tiene que entender lo que el repo le manda;
    si el parseo viviera del lado del test, sería una SEGUNDA interpretación del formato — y el
    día que el encoder cambie, el fake seguiría entendiendo el formato viejo y los tests del
    filtro pasarían en verde sin haber ejercitado nada. Encoder y decoder juntos, un solo
    formato, y un test de ida y vuelta que los ata (`test_objetivos_filtros_nuevos`).

    ⚠️ Recibe SIEMPRE un string, nunca una lista. Una rama que aceptara la lista y la devolviera
    tal cual haría al fake más tolerante que PostgREST justo en el caso que importa; el fake
    convierte la lista con `como_lo_manda_la_libreria` ANTES de llamar acá, para que el valor sin
    comillar se parta igual que se partiría de verdad.
    """
    cuerpo = literal.strip()[1:-1]        # saca las llaves
    salida: List[str] = []
    actual, dentro, escapando, comillado = "", False, False, False

    def cerrar():
        # 🔴 UN ELEMENTO SIN COMILLAS SE RECORTA Y UNO COMILLADO NO, porque es lo que hace
        # Postgres — verificado en el catálogo: `'{Legales, Compliance}'::text[]` da
        # ["Legales", "Compliance"] (sin el espacio), y `'{" a "}'::text[]` conserva los dos.
        # Sin esta diferencia el fake que usa este parser sería MÁS TOLERANTE que la base con el
        # valor sin comillar, que es justo el caso que hay que poder desmentir.
        salida.append(actual if comillado else actual.strip())

    for ch in cuerpo:
        if escapando:
            actual, escapando = actual + ch, False
        elif ch == "\\":
            escapando = True
        elif ch == '"':
            dentro, comillado = not dentro, True
        elif ch == "," and not dentro:
            cerrar()
            actual, comillado = "", False
        else:
            actual += ch
    if actual or salida or comillado:
        cerrar()
    return salida
