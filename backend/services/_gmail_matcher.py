"""
Del asunto de un mail al código de vacante. Función pura: no toca la red ni la base.

## 🔴 EL CANDIDATO LO VA A ESCRIBIR MAL, Y ESO NO ES UN CASO BORDE

Quien escribe el asunto es alguien de afuera copiando de un aviso de LinkedIn desde el teléfono.
Va a mandar `vac-0001`, `VAC 0001`, `Vac0001`, `[VAC-0001]`, o `Postulación VAC-0001 - Analista`.
Exigir el formato exacto significa mandar a revisión manual postulaciones que traen el código
perfectamente identificable — y eso no falla con un error: el CV cae en "pendiente" y alguien
tiene que mirarlo a mano, que es justo lo que el código venía a evitar.

Por eso el reconocimiento es **permisivo en la escritura y estricto en la identidad**:
  · `VAC` sin distinguir mayúsculas;
  · separador opcional (`-`, espacio, o nada), y espacios de más;
  · los dígitos se **normalizan** a la forma canónica, así que `[VAC-00001]` y `VAC 0001` son el
    mismo código: el padding es cosmético.

🔴 **PERO SE EXIGEN 4 DÍGITOS COMO MÍNIMO, y esa parte NO es negociable.** `VAC-1` NO matchea.
Aceptar menos dígitos sería permitir que un código tipeado a medias resuelva **a otra vacante
real**: `VAC-12` se volvería `VAC-0012`, que puede existir y no ser la búsqueda del candidato.
Un CV en la búsqueda equivocada no da error y no se detecta; uno en revisión manual se resuelve
en dos segundos. La permisividad llega hasta donde no puede inventar una respuesta distinta.

## 🔴 DOS CÓDIGOS DISTINTOS → SIN MATCH, y es una decisión, no una limitación

Un reenvío o una cadena de mails puede arrastrar dos códigos. **Elegir el primero es tomar una
decisión invisible sobre la carrera de alguien**: el CV entra a una búsqueda que quizás no es la
suya y nadie se entera nunca. Sin match va a revisión, donde un humano decide en dos segundos.
Repetido NO cuenta como dos: `[VAC-0001] re: VAC 0001` es un código solo, y tratarlo como
ambiguo mandaría a revisión un mail perfectamente claro.
"""
import re
from typing import List, Optional

# `VAC`, separador opcional, y 4+ dígitos. `{4,}` y no `{4}` porque el contador puede pasar de
# 9999 (ver el CHECK de la migración 097). El `\b` inicial evita enganchar el sufijo de otra
# palabra; no se exige `\b` al final para que `VAC-0001-analista` matchee igual.
_CODIGO = re.compile(r"\bVAC[\s\-_.]*(\d{4,})", re.IGNORECASE)


def codigos_en(texto: Optional[str]) -> List[str]:
    """Todos los códigos DISTINTOS que aparecen en un texto, en forma canónica `VAC-0001`.

    Devuelve la lista para que el caller pueda distinguir "ninguno" de "más de uno": son dos
    situaciones distintas y el caller las reporta distinto (`sin_codigo` vs `codigo_ambiguo`).

    Los dígitos se normalizan quitando ceros a la izquierda y re-paddeando a 4, así que
    `VAC 0001` y `[vac-00001]` colapsan al mismo código. Un número de 5 dígitos reales
    (`VAC-10000`) sobrevive intacto. Menos de 4 dígitos NO es un código — ver el encabezado.
    """
    vistos: List[str] = []
    for digitos in _CODIGO.findall(texto or ""):
        canonico = f"VAC-{int(digitos):04d}"
        if canonico not in vistos:            # repetido no es ambiguo: es el mismo código
            vistos.append(canonico)
    return vistos
