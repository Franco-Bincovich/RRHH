"""
Labels, textos de ayuda y vocabularios del formulario de perfiles de puesto.

🔴 POR QUÉ ES BACKEND Y NO UNA CONSTANTE DEL FRONT. Mismo criterio y mismo precedente que
`schemas/_provincias.py`: la lista se EXPONE por endpoint (`GET /api/perfiles-puesto/campos`) y
el front la consume, en vez de escribirla dos veces. Acá además sería peor que en provincias:
los tres vocabularios cerrados TAMBIÉN son los `Literal` con los que valida
`schemas/perfil_puesto.py`, así que una copia del front que derive ofrecería en un select un
valor que el backend rechaza con 422.

🔴 Y POR QUÉ HAY TEXTOS DE AYUDA Y NO SOLO LABELS — es el punto entero del archivo.
El bloque **"Requisitos"** del aviso real (`docs/AVISO-BUSQUEDA-REFERENCIA.md`) pone SIETE cosas
de CUATRO naturalezas distintas bajo un solo título: experiencia, formación, conocimientos
técnicos y habilidades blandas. La tabla tiene columna propia para las tres primeras, así que
`requisitos` es **el cajón de lo que no entra en ninguna**.

Si el formulario muestra los cuatro campos sin explicar la diferencia, Capital Humano va a pegar
el bloque entero en `requisitos` y dejar los otros tres vacíos — y ahí el perfil deja de servir
para filtrar y para armar un aviso por partes, que son las dos razones por las que las columnas
están separadas. **No falta una columna: faltan estos textos.**

NO HAY VALIDACIÓN QUE SUSTITUYA ESTO. Exigir los cuatro campos llenos sería peor: un perfil
legítimo puede no pedir formación, y el rechazo enseñaría a escribir cualquier cosa para pasar
el validador. La única defensa es que el formulario diga qué va en cada campo, en el orden
correcto, ANTES de que la persona escriba.
"""
from typing import List, TypedDict


class Campo(TypedDict):
    """Un campo del formulario: cómo se llama, qué se escribe adentro y con qué control."""

    campo: str
    label: str
    ayuda: str
    tipo: str  # texto | textarea | select


class Opcion(TypedDict):
    """Un valor de un vocabulario cerrado, con su etiqueta legible."""

    value: str
    label: str


# ── Vocabularios cerrados ─────────────────────────────────────────────────────
# Los `value` son EXACTAMENTE los de los CHECK de la 113 y los `Literal` de `perfil_puesto.py`.
# Los `label` son presentación: cambiarlos es gratis, cambiar un `value` rompe la validación y
# las filas ya guardadas.

MODALIDADES: List[Opcion] = [
    {"value": "presencial", "label": "Presencial"},
    {"value": "remoto", "label": "Remoto"},
    {"value": "hibrido", "label": "Híbrido"},
]

TIPOS_CONTRATO: List[Opcion] = [
    {"value": "efectivo", "label": "Efectivo"},
    {"value": "plazo_fijo", "label": "Plazo fijo"},
    {"value": "contratado", "label": "Contratado"},
    {"value": "pasantia", "label": "Pasantía"},
]

NIVELES: List[Opcion] = [
    {"value": "junior", "label": "Junior"},
    {"value": "semi_senior", "label": "Semi Senior"},
    {"value": "senior", "label": "Senior"},
    {"value": "lider", "label": "Líder"},
    {"value": "manager", "label": "Manager"},
    {"value": "director", "label": "Director"},
    {"value": "c_level", "label": "C-Level"},
]

# ── La nota que va ARRIBA del bloque de requisitos, no adentro de un tooltip ──
# Un tooltip se lee después de haber escrito. Esto tiene que estar visible antes.
NOTA_REQUISITOS = (
    "Los avisos suelen poner todo junto bajo “Requisitos”. Acá va separado en cuatro campos "
    "para que después se pueda filtrar y reusar por partes: primero la experiencia, después la "
    "formación, después las herramientas, y al final lo que no entra en ninguno de los tres."
)

# ── Los campos, EN EL ORDEN EN QUE SE LLENAN ──────────────────────────────────
# 🔴 `requisitos` va CUARTO del bloque y no primero. Puesto arriba se lleva todo el contenido
# y los otros tres quedan vacíos; puesto abajo, cuando se llega ya se escribieron los tres
# específicos y lo que queda es de verdad "lo demás".

CAMPOS: List[Campo] = [
    {
        "campo": "nombre",
        "label": "Nombre del perfil",
        "ayuda": ("Cómo se llama el puesto. Es lo que vas a elegir en el selector al crear una "
                  "vacante y lo que se copia al título del aviso. Ej: “Analista SQL”."),
        "tipo": "texto",
    },
    {
        "campo": "descripcion",
        "label": "Descripción del puesto",
        "ayuda": ("El párrafo de presentación del aviso: qué es el puesto y a quién se busca. "
                  "Si la búsqueda abarca una franja de niveles (“Junior avanzado / Semi "
                  "Senior”), escribila acá: el campo Nivel guarda un valor solo."),
        "tipo": "textarea",
    },
    {
        "campo": "funciones",
        "label": "Responsabilidades",
        "ayuda": ("Qué va a hacer la persona, una por línea. Son las tareas del puesto, no lo "
                  "que se le pide saber. Ej: “Análisis de datos de diversas fuentes para "
                  "identificar patrones y generar informes”."),
        "tipo": "textarea",
    },
    {
        "campo": "experiencia",
        "label": "Experiencia requerida",
        "ayuda": ("Cuántos años y haciendo qué. SOLO experiencia laboral previa. Ej: “Mínimo "
                  "de 1 a 3 años en análisis funcional o roles relacionados”. Los títulos van "
                  "en Formación y las herramientas en Conocimientos técnicos."),
        "tipo": "textarea",
    },
    {
        "campo": "formacion",
        "label": "Formación académica",
        "ayuda": ("Títulos, carreras y certificaciones. Ej: “Título de Analista de Sistemas, o "
                  "afines”. Un curso de una herramienta NO va acá: es conocimiento técnico."),
        "tipo": "textarea",
    },
    {
        "campo": "conocimientos_tecnicos",
        "label": "Conocimientos técnicos",
        "ayuda": ("Herramientas, lenguajes y metodologías, aclarando cuáles son excluyentes. "
                  "Ej: “SQL y bases de datos (excluyente), metodologías ágiles, herramientas "
                  "de modelado”."),
        "tipo": "textarea",
    },
    {
        "campo": "requisitos",
        "label": "Otros requisitos y habilidades blandas",
        "ayuda": (
            "Lo que no entra en los tres campos de arriba: comunicación, autonomía, "
            "resolución de problemas, disponibilidad para viajar. "
            "Si pegás acá el bloque “Requisitos” entero del aviso, los otros tres quedan "
            "vacíos y el perfil deja de servir para filtrar ni para reusar por partes."
        ),
        "tipo": "textarea",
    },
    {
        "campo": "ofrecemos",
        "label": "Ofrecemos",
        "ayuda": ("Beneficios y propuesta de valor: desarrollo profesional, ambiente de "
                  "trabajo, beneficios corporativos. Es el bloque que MENOS cambia entre "
                  "búsquedas, y por eso vive en la plantilla y no en cada vacante."),
        "tipo": "textarea",
    },
    {
        "campo": "modalidad",
        "label": "Modalidad",
        "ayuda": (
            "Presencial, remoto o híbrido. El detalle de cuántos días se va a la oficina NO va "
            "acá: eso cambia entre búsquedas del mismo perfil y se escribe en la vacante."
        ),
        "tipo": "select",
    },
    {
        "campo": "tipo_contrato",
        "label": "Tipo de contrato",
        "ayuda": "Cómo se contrata a la persona. Se copia tal cual a la vacante.",
        "tipo": "select",
    },
    {
        "campo": "nivel",
        "label": "Nivel",
        "ayuda": (
            "Un solo valor. Si la búsqueda abarca una franja, elegí el más bajo de los dos y "
            "aclarala en la Descripción."
        ),
        "tipo": "select",
    },
    {
        "campo": "jornada",
        "label": "Jornada",
        "ayuda": "Texto libre. Ej: “Lunes a viernes de 9 a 18”.",
        "tipo": "texto",
    },
]

# ── Mensajes de validación ────────────────────────────────────────────────────
# Viven acá y no sueltos en el service, por el mismo motivo que los labels: son texto que ve
# alguien de Capital Humano. El service los IMPORTA, no los reescribe.

MSG_NOMBRE_REQUERIDO = "El nombre del perfil es obligatorio."
MSG_NOMBRE_DUPLICADO = (
    "Ya existe un perfil de puesto con ese nombre. Los perfiles son de todo el grupo, así que "
    "el nombre tiene que ser único en el sistema entero, no por empresa."
)
MSG_NO_ENCONTRADO = "Perfil de puesto no encontrado"
