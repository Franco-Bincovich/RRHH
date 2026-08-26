"""
LA FORMA del código de la búsqueda: de lo que escribe Capital Humano al código canónico.

La otra mitad de la regla —que el código no se repita— vive en `_vacante_codigo_choque.py`. El
corte es por el límite de 150 líneas y cae en la costura natural: **el matcher de CVs importa de
acá y no necesita saber nada de unicidad**, y esta mitad no consulta la base ni una vez.

## 🔴 CAPITAL HUMANO ESCRIBE TEXTO NATURAL — EL SISTEMA LO CONVIERTE

Hasta la migración 122 el código era `VAC-0001` y lo emitía una secuencia. Después pasó a ser un
campo del formulario **con la forma canónica exigida al tipear**, y eso rebotaba lo único que una
persona iba a escribir de verdad: `Lider de equipo`. Un rechazo así no enseña la regla — enseña
que el campo es hostil, y el que lo usa termina poniendo `L1` para que lo deje pasar.

Ahora escriben lo que quieren y `canonico` lo convierte:

    "Lider de equipo"   → LIDER-DE-EQUIPO
    "Analista Sr."      → ANALISTA-SR
    "Ecónomo 2026"      → ECONOMO-2026
    "Diseño UX/UI"      → DISENO-UX-UI

🔴 **Y LA PANTALLA MUESTRA EL RESULTADO ANTES DE GUARDAR** (`VacanteCampoCodigo`, "Se va a usar:
…"). Convertir en silencio sería peor que rechazar: escriben una cosa, el sistema guarda otra, y
se enteran cuando el candidato pregunta por qué su CV no llegó.

## Las reglas, y contra qué está cada una

  1. **Sin acentos ni ñ** (`Ecónomo` → `ECONOMO`, `Diseño` → `DISENO`). El código termina en el
     asunto de un mail que tipea alguien desde el teléfono: una tilde se escribe mal la mitad de
     las veces y el CV cae en revisión manual sin ningún error visible. ⚠️ El asunto SÍ puede
     traer el acento, y por eso `_gmail_matcher` le saca los acentos AL ASUNTO con `sin_acentos`,
     esta misma función — ver su docstring.
  2. **Todo lo que no es letra ni dígito es separador**, y un run de separadores es UN guion
     (`Analista  //  Sr.` → `ANALISTA-SR`). Sin colapsar el run quedarían guiones dobles, que el
     CHECK rechaza; sin limpiar los bordes, un `-` al principio o al final.
  3. **Al menos una letra.** `2026` matchearía cualquier "2026" suelto en un asunto —"CV 2026"—
     y mandaría el CV a esa búsqueda sin que nada falle.
  4. **Entre 3 y 60 caracteres, y pasarse RECHAZA — no recorta.** Ver `MAX_LARGO` y `normalizar`.
"""
import re
import unicodedata
from typing import Optional

from utils.errors import AppError

CODIGO_INVALIDO = "CODIGO_VACANTE_INVALIDO"

# Espejo del CHECK `vacantes_codigo_formato` (migración 122, ensanchado por la 123). Si divergen,
# la base rechaza lo que la app aceptó y el alta muere con un 500 en vez de con el mensaje de acá.
_FORMA = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)*$")
_NO_ALFANUMERICO = re.compile(r"[^A-Z0-9]+")
MIN_LARGO = 3

# 🔴 60 Y NO 30. El techo de 30 lo escribió la 122 pensando en códigos tipo `ECO-2026`; con texto
# natural rebota lo que la gente escribe de verdad — **una de las 5 vacantes reales de producción
# se llama "Analista de Sistemas Semi Senior", que canoniza a 32 caracteres** y con 30 no se
# podría cargar por su nombre. 60 sigue entrando cómodo en el asunto de un mail y en la columna
# del listado, que es lo único que el límite protegía.
MAX_LARGO = 60


def sin_acentos(texto: str) -> str:
    """`Ecónomo` → `Economo`, `Diseño` → `Diseno`. Descompone y tira las marcas diacríticas.

    🔴 ES PÚBLICA PORQUE LA USA `_gmail_matcher` SOBRE EL ASUNTO DEL MAIL, y ése es el motivo de
    que exista separada de `canonico`: el código guardado no tiene acentos, pero el asunto que
    escribe el candidato sí puede tenerlos. Si sólo se los sacáramos al código, `[Ecónomo 2026]`
    no matchearía `ECONOMO-2026` — el caso normal, no el borde. Dos implementaciones de "sacar
    acentos" que se separaran darían dos resultados distintos para el mismo texto en cada punta.
    """
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def canonico(texto: Optional[str]) -> str:
    """El texto convertido a código, SIN validar. `""` si no queda nada utilizable.

    Separada de `normalizar` porque la pantalla necesita mostrar el resultado mientras se escribe
    —"Se va a usar: LIDER-DE-EQUIPO"— y ahí un texto a medio tipear todavía no es un error.
    """
    limpio = sin_acentos((texto or "").strip()).upper()
    return _NO_ALFANUMERICO.sub("-", limpio).strip("-")


def _invalido(mensaje: str) -> AppError:
    return AppError(mensaje, CODIGO_INVALIDO, 422)


def normalizar(texto: Optional[str]) -> str:
    """El código canónico, validado. Es lo que se guarda y sobre lo que se mide la unicidad.

    Raises: CODIGO_VACANTE_INVALIDO (422) — vacío, muy corto, sin ninguna letra, o muy largo.
    """
    codigo = canonico(texto)
    if not codigo:
        raise _invalido("La búsqueda necesita un código: escribí un nombre con letras o números, "
                        "por ejemplo «Líder de equipo».")
    if len(codigo) < MIN_LARGO:
        raise _invalido(f"«{codigo}» es muy corto para un código: necesita al menos {MIN_LARGO} "
                        "caracteres, o va a matchear cualquier palabra de un asunto.")
    if not re.search(r"[A-Z]", codigo):
        raise _invalido(f"«{codigo}» no tiene ninguna letra. Un código de puros números matchea "
                        "cualquier año suelto en el asunto de un mail: agregale una palabra.")
    if len(codigo) > MAX_LARGO:
        # 🔴 SE RECHAZA, NO SE RECORTA, y no es rigidez. Dos títulos distintos que empiecen igual
        # —"Analista de Sistemas Senior" y "Analista de Sistemas Semi Senior"— recortados al
        # mismo largo dan EL MISMO código: la segunda búsqueda se rechazaría como duplicada de
        # una que su autor nunca escribió, o peor, el aviso saldría con un código que esa persona
        # no vio nunca. Un recorte en silencio es exactamente lo que esta pantalla vino a evitar.
        raise _invalido(
            f"El código queda en {len(codigo)} caracteres y el máximo es {MAX_LARGO}. "
            f"Acortá el texto {len(codigo) - MAX_LARGO} caracteres: no se recorta solo, porque "
            "dos títulos distintos podrían quedar con el mismo código.")
    if not _FORMA.match(codigo):  # pragma: no cover — la conversión no puede producir otra forma
        raise _invalido(f"El código «{codigo}» no se puede usar. Usá letras, números y espacios.")
    return codigo
