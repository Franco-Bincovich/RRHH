"""
El bloque `<busqueda>` del prompt: qué campos de la vacante ve el clasificador.

## 🔴 QUÉ ARREGLA ESTE MÓDULO

Hasta ahora el prompt se armaba con `vacante.titulo` y `vacante.descripcion`, y nada más. Los
CINCO campos que RRHH escribe en "Información del puesto" —funciones, requisitos, formación,
experiencia, conocimientos técnicos— **no llegaban al modelo**. Y `descripcion`, el único campo
con contenido que sí se leía, **no se puede cargar desde la UI**: la ficha lo oculta cuando está
vacío, así que nunca hay dónde escribirlo.

El resultado en producción era el peor de los dos mundos: la única vacante tenía los cinco
campos cargados y `descripcion` vacío, así que el prompt real decía

    Puesto: Analista contable
    Descripción: (sin descripción)

y el modelo clasificaba CVs **contra un título y nada más**, mientras RRHH creía que estaba
usando los requisitos que había escrito. Un campo que el usuario completa y el sistema ignora es
peor que un campo que no existe.

## Los siete campos, y por qué cada uno con SU etiqueta

`CAMPOS` fija el orden y el rótulo. No se concatenan en un solo párrafo a propósito: "tiene que
saber Excel" pesa distinto si está bajo *Requisitos* que bajo *Conocimientos técnicos*, y
"contador público" es otra cosa como *Formación* que como *Funciones*. Un bloque de texto plano
le pide al modelo que reconstruya esa distinción; las etiquetas se la dan hecha.

🔑 **Los rótulos son los MISMOS que muestra la UI** (`InformacionPuestoSection.tsx`). El modelo
lee el campo con el mismo nombre con el que RRHH lo escribió: si acá dijera "Requisitos
excluyentes" y el formulario dijera "Requisitos", el modelo estaría interpretando una exigencia
que nadie declaró.

⚠️ `descripcion` va **ÚLTIMO y solo si tiene contenido**. Es legacy —hoy no hay UI para
escribirlo— y no es la fuente principal de la búsqueda; queda contemplado para el día que se
exponga, sin competir con los campos que sí se usan.

## Los vacíos se OMITEN

Nada de "(sin requisitos)". Seis secciones anunciadas y vacías son ruido que empuja al modelo a
llenar huecos, y encima gastan tokens en cada CV del lote. Si un campo no está, no aparece.

## 🔴 SI NO HAY NADA MÁS QUE EL TÍTULO, LA CORRIDA SE SALTEA ENTERA

`sin_contenido` habilita esa decisión, y la decisión es: **no se clasifica**. Clasificar contra
un título pelado es exactamente lo que estaba pasando, y el resultado no es "peor": es engañoso.
El modelo igual devuelve una de las tres categorías con un motivo redactado con seguridad, y ese
motivo es justo lo que RRHH lee para decidir si revisa. **Un veredicto convincente derivado de
nada no se distingue de uno fundado**, así que es peor que no tener veredicto.

El chequeo lo hace `cv_screening_service` UNA vez por corrida y no por candidato, porque es una
condición de la VACANTE: los N candidatos fallarían idénticamente. Así cuesta cero llamadas en
vez de N, deja UN mensaje sobre la búsqueda en lugar de N mensajes iguales sobre personas, y no
ensucia el `clasificacion_motivo` de nadie con algo que no habla del candidato.

## Topes: uno por campo Y uno del bloque

Antes había un solo tope de 2.000 sobre título y descripción. Con siete campos hacen falta dos:

  · **`MAX_CAMPO`** — para que un pegado accidental de medio manual en *Funciones* no se coma el
    presupuesto del bloque entero y deje a *Requisitos* afuera.
  · **`MAX_BLOQUE`** — techo del bloque armado. Es lo que acota el costo por CV: este texto viaja
    en CADA llamada del lote, así que un bloque el doble de largo duplica el costo de la corrida.

🔴 **Un truncado se AVISA, y se avisa DENTRO del prompt.** Un requisito cortado a la mitad hace
que el modelo evalúe contra media frase creyendo que es la frase entera. La nota le dice que el
texto está incompleto; sin ella, el truncado es exactamente la clase de error que no deja rastro.
`truncado` viaja además hasta la respuesta del botón, porque quien tiene que acortar la búsqueda
es RRHH y no se puede enterar leyendo un prompt que no ve.
"""
from dataclasses import dataclass
from typing import List, Tuple

# (atributo de VacanteResponse, rótulo). El orden es el del prompt.
# `descripcion` NO está acá: va aparte y al final. Ver el encabezado.
CAMPOS: Tuple[Tuple[str, str], ...] = (
    ("titulo", "Puesto"),
    ("area_nombre", "Área"),
    ("funciones", "Funciones"),
    ("requisitos", "Requisitos"),
    ("formacion", "Formación"),
    ("experiencia", "Experiencia"),
    ("conocimientos_tecnicos", "Conocimientos técnicos"),
)

# Los campos que constituyen el CONTENIDO de la búsqueda: lo que dice qué se pide. `titulo` y
# `area_nombre` quedan afuera porque no son requisitos — son la etiqueta del puesto y su
# ubicación en el organigrama. Una búsqueda con solo esos dos no describe nada evaluable.
CAMPOS_DE_CONTENIDO = ("funciones", "requisitos", "formacion", "experiencia",
                       "conocimientos_tecnicos", "descripcion")

MAX_CAMPO = 2_000
MAX_BLOQUE = 6_000

_NOTA_TRUNCADO = ("[La descripción de la búsqueda está incompleta: el texto se cortó por "
                  "longitud. Evaluá solo con lo que ves y ante la duda usá dudoso.]")


@dataclass(frozen=True)
class BloqueBusqueda:
    """El bloque listo, más lo que el caller necesita saber sobre él."""

    texto: str
    truncado: bool
    #: No hay ni un campo de contenido cargado: solo título y/o área. Ver `cv_screening_service`.
    sin_contenido: bool


def bloque_busqueda(vacante, limpiar) -> BloqueBusqueda:
    """Arma el bloque `<busqueda>` con los siete campos que tengan contenido.

    Args:
        vacante: `VacanteResponse`. Se pasa el objeto ENTERO y no campos sueltos: la firma vieja
            tomaba dos strings, y ese fue justamente el punto donde los otros cinco se perdieron.
        limpiar: el sanitizador del prompt (`_clasificador_prompt._limpio`). Se inyecta en vez de
            importarse para no cerrar un ciclo entre los dos módulos. 🔴 TODOS los campos pasan
            por él, no solo los dos de antes: los siete son texto que escribe una persona.
    """
    partes: List[str] = []
    for atributo, rotulo in CAMPOS:
        valor = limpiar(getattr(vacante, atributo, None), MAX_CAMPO)
        if valor:
            partes.append(f"{rotulo}: {valor}")

    # Último y solo si tiene contenido. Ver el encabezado.
    extra = limpiar(getattr(vacante, "descripcion", None), MAX_CAMPO)
    if extra:
        partes.append(f"Notas adicionales: {extra}")

    cuerpo = "\n".join(partes)
    truncado = len(cuerpo) > MAX_BLOQUE
    if truncado:
        cuerpo = f"{cuerpo[:MAX_BLOQUE]}\n{_NOTA_TRUNCADO}"

    return BloqueBusqueda(
        texto=f"<busqueda>\n{cuerpo}\n</busqueda>",
        truncado=truncado,
        sin_contenido=not _tiene_contenido(vacante),
    )


def _tiene_contenido(vacante) -> bool:
    """¿Hay algo evaluable, más allá del título y el área?"""
    return any((getattr(vacante, c, None) or "").strip() for c in CAMPOS_DE_CONTENIDO)
