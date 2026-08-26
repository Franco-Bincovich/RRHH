"""
Del asunto de un mail al código de la vacante. Función pura: no toca la red ni la base.

## 🔴 CAMBIÓ EL 26/8/2026: EL CÓDIGO YA NO TIENE FORMA CONOCIDA

Hasta hoy el código lo emitía la base con el formato `VAC-0001`, así que el matcher podía
reconocerlo con UN regex (`VAC` + 4 dígitos) sin saber qué vacantes existen. Ahora lo escribe
Capital Humano y puede ser `ECO-2026`, `LOG-01` o lo que decidan (migración 122): **no hay
ninguna forma que adivinar**. Por eso este módulo pasó a recibir LOS CÓDIGOS QUE EXISTEN y
buscar esos, en vez de reconocer un patrón.

La consecuencia buena es que dejó de poder inventar: antes `VAC-9999` se "reconocía" aunque no
existiera ninguna vacante con ese número y el mail se reportaba como `vacante_desconocida`; ahora
un código que no existe simplemente no aparece, y el mail se reporta como `sin_codigo`. Las dos
formas mandan a revisión manual, que es lo correcto en los dos casos.

## 🔴 EL CANDIDATO LO VA A ESCRIBIR MAL, Y ESO NO ES UN CASO BORDE

Quien escribe el asunto es alguien de afuera copiando de un aviso de LinkedIn desde el teléfono.
Va a mandar `eco-2026`, `ECO 2026`, `Eco2026`, `[ECO-2026]`, o `Postulación ECO-2026 - Analista`.
Exigir el formato exacto significa mandar a revisión manual postulaciones que traen el código
perfectamente identificable — y eso no falla con un error: el CV cae en "pendiente" y alguien
tiene que mirarlo a mano, que es justo lo que el código venía a evitar.

Por eso el reconocimiento sigue siendo **permisivo en la escritura y estricto en la identidad**:
por cada código conocido se arma un patrón que tolera mayúsculas/minúsculas y CUALQUIER cosa que
no sea letra ni dígito ENTRE SUS PARTES, pero exige que el código completo esté ahí.

## 🔴 EL ASUNTO SE LEE SIN ACENTOS, CON LA MISMA FUNCIÓN QUE LOS SACA AL GUARDAR

El código guardado nunca tiene acentos —`Ecónomo 2026` se guarda `ECONOMO-2026`— pero **el asunto
del mail SÍ los puede traer**, y ése es el caso normal: el candidato copia el título del aviso tal
como está escrito. Si el matcher comparara el canónico contra un asunto con tilde, `[Ecónomo
2026]` NO matchearía y el CV iría a revisión manual — el módulo entero fallando justo en el caso
que se quería cubrir.

Se resuelve pasando el asunto por `_vacante_codigo.sin_acentos`, **la misma función** que usa la
conversión. Dos implementaciones de "sacar acentos" que se separaran darían dos lecturas
distintas del mismo texto en cada punta. Las posiciones que devuelve el regex son sobre el texto
YA normalizado y sólo se comparan entre sí (contención), así que no hace falta mapearlas de vuelta
al asunto original.

## 🔴 EL SEPARADOR TOLERADO ES EL MISMO QUE LA CONVERSIÓN COLAPSA — Y POR ESO MATCHEA EL AVISO

`canonico` transforma en `-` **todo lo que no es letra ni dígito**; acá se tolera exactamente eso
entre las partes. La consecuencia sale gratis y es la que importa: `LIDER-DE-EQUIPO` matchea un
asunto que dice **`Lider de equipo`**, que es lo que la gente realmente escribe —copian el título
del aviso, no el código entre corchetes—. Si el separador tolerado fuera más angosto que el que la
conversión colapsa, habría textos que el sistema acepta al guardar y no reconoce al leer.

⚠️ **EL PRECIO, DECLARADO:** con códigos de texto natural sube el riesgo de falso positivo. Si una
búsqueda se llama `ANALISTA` a secas, un asunto "Analista de sistemas - CV" la matchea. No es un
bug —el código está literalmente en el asunto— sino el costo de elegir un código genérico, y la
salida es de PRODUCTO: **conviene que el código tenga una parte que lo distinga**
(`ANALISTA-SISTEMAS-2026`). Si además existe la búsqueda larga, la contención ya hace que gane.

## 🔴 EL BORDE ALFANUMÉRICO ES LO QUE HACE QUE ESTO NO SE ROMPA

Un código conocido se busca como texto adentro del asunto, así que sin bordes `ECO` matchearía
adentro de `ECONOMIA` y cualquier mail sobre economía entraría a esa búsqueda. Los dos
`(?<![A-Za-z0-9])` / `(?![A-Za-z0-9])` lo impiden. Es el reemplazo del `\b` que tenía el regex
viejo, y del `EVAC-0001` que nunca tuvo que matchear.

## 🔴 DOS CÓDIGOS DONDE UNO CONTIENE AL OTRO — `ECO` y `ECO-2026`

Es el caso que la unicidad NO resuelve, y aparece solo ahora que los códigos los elige una
persona: nada impide crear `ECO` y después `ECO-2026`. En un asunto `[ECO-2026]` los DOS
patrones matchean —el borde de `ECO` es el guion, que no es alfanumérico— y sin nada más el mail
quedaría marcado como `codigo_ambiguo` PARA SIEMPRE: todo CV de `ECO-2026` iría a revisión
manual, que es exactamente lo que el código venía a evitar.

**Se resuelve por posición, no por preferencia: un match que quedó ADENTRO de otro se descarta.**
`ECO` ocupa [1,4) y `ECO-2026` ocupa [1,9); el primero es un pedazo del segundo, no una segunda
mención. No es "elegir el más largo por gusto": es que en el texto hay UNA sola mención, y la
mención es la larga. Si los dos códigos aparecen de verdad y por separado —`[ECO] y [ECO-2026]`—
los dos spans son disjuntos, los dos sobreviven, y el mail va a revisión, que es lo correcto.

⚠️ **LO QUE ESTO NO CUBRE, DECLARADO:** si existe `ECO` y el candidato escribe `[ECO-2027]` —un
código que NO existe— el mail resuelve a `ECO`, porque `ECO-2027` no matchea nada y `ECO` sí. Es
el mismo comportamiento que ya tenía `VAC-0001-analista`, y no se puede cerrar sin romperlo:
exigir que después del código no venga un guion mandaría a revisión todos los asuntos con el
código seguido del puesto. La salida es de PRODUCTO, no de código: no conviene usar un código
que sea el prefijo de otro que también se publica.

## 🔴 DOS CÓDIGOS DISTINTOS → SIN MATCH, y es una decisión, no una limitación

Un reenvío o una cadena de mails puede arrastrar dos códigos. **Elegir el primero es tomar una
decisión invisible sobre la carrera de alguien**: el CV entra a una búsqueda que quizás no es la
suya y nadie se entera nunca. Sin match va a revisión, donde un humano decide en dos segundos.
Repetido NO cuenta como dos: `[ECO-2026] re: eco 2026` es un código solo, y tratarlo como
ambiguo mandaría a revisión un mail perfectamente claro.
"""
import re
from functools import lru_cache
from typing import Iterable, List, Optional, Tuple

from services._vacante_codigo import sin_acentos

# Entre las partes de un código: cualquier cosa que no sea letra ni dígito, o nada. Es EL MISMO
# conjunto que `canonico` colapsa a `-` al guardar (ver el bloque de la simetría, arriba), así que
# `LIDER-DE-EQUIPO` reconoce `Lider de equipo`, `LIDER, DE EQUIPO` y `LIDERDEEQUIPO`.
_ENTRE_PARTES = r"[^A-Za-z0-9]*"
_PARTES = re.compile(r"[^A-Za-z0-9]+")


@lru_cache(maxsize=512)
def _patron(codigo: str) -> re.Pattern:
    """El patrón de UN código. Cacheado: la corrida arma uno por vacante y lo usa en N mails."""
    partes = [re.escape(p) for p in _PARTES.split(codigo) if p]
    return re.compile(rf"(?<![A-Za-z0-9]){_ENTRE_PARTES.join(partes)}(?![A-Za-z0-9])",
                      re.IGNORECASE)


def _adentro_de_otro(span: Tuple[int, int], spans: List[Tuple[int, int]]) -> bool:
    """¿Este match es un pedazo de otro más largo? Ver el bloque de `ECO` / `ECO-2026`."""
    return any(o[0] <= span[0] and span[1] <= o[1] and (o[1] - o[0]) > (span[1] - span[0])
               for o in spans)


def codigos_en(texto: Optional[str], codigos_conocidos: Iterable[str]) -> List[str]:
    """Los códigos CONOCIDOS que aparecen en el texto, en el orden en que aparecen.

    Devuelve la lista y no un código para que el caller pueda distinguir "ninguno" de "más de
    uno": son dos situaciones distintas y el caller las reporta distinto (`sin_codigo` vs
    `codigo_ambiguo`).

    Args:
        texto: el asunto del mail, tal como llegó. Se le sacan los acentos acá adentro. `None`
            (un mail sin asunto) devuelve `[]`, no revienta.
        codigos_conocidos: los códigos de las vacantes que existen, tal como están guardados.
            🔴 SE PASAN, NO SE CONSULTAN: son una query por CORRIDA, no por mail. Es un
            parámetro obligatorio justamente para que no se pueda esconder un N+1 acá adentro.
    """
    # Sin acentos ANTES de buscar: el asunto los puede traer y el código guardado nunca. Ver el
    # bloque 🔴 del encabezado — es el caso normal, no el borde.
    asunto = sin_acentos(texto or "")
    hallados: List[Tuple[int, int, str]] = []
    for codigo in codigos_conocidos:
        if not codigo:
            continue
        for m in _patron(codigo).finditer(asunto):
            hallados.append((m.start(), m.end(), codigo))
    spans = [(a, b) for a, b, _ in hallados]
    vistos: List[str] = []
    for inicio, fin, codigo in sorted(hallados):
        if _adentro_de_otro((inicio, fin), spans):
            continue
        if codigo not in vistos:          # repetido no es ambiguo: es el mismo código
            vistos.append(codigo)
    return vistos
