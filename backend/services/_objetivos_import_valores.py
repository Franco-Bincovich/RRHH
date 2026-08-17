"""
Cómo se lee el CONTENIDO de una celda del Excel de objetivos: la fecha y las áreas.

🔑 EL CORTE CONTRA `_objetivos_import_transforms.py` ES POR PREGUNTA, no sólo por líneas (aquél
quedaba en 159 contra un tope de 150). Allá vive el **vocabulario de columnas**: cómo se llama
cada una, cuáles son obligatorias, cuál delata una jerarquía que no se soporta. Acá vive cómo se
interpreta lo que hay ADENTRO de una celda, que es lo único que puede convertir un dato bueno en
uno roto sin que nadie se entere.

Las dos funciones comparten esa forma y la misma política de fondo: **una celda mal escrita no
tumba la fila**. Una fecha ilegible deja el objetivo sin fecha y lo reporta; una celda de áreas
vacía deja el array vacío. Perder un objetivo entero por una celda con "prox. mes" sería peor.

La regla de las áreas además NO es la misma que la de `_separar`, la de los responsables, y las
dos juntas en un archivo se leen como una inconsistencia en vez de como dos decisiones.

## 🔴 EL `;` GANA CUANDO ESTÁ, Y RECIÉN SI NO ESTÁ SE PARTE POR `,`

`_separar` (responsables) acepta los DOS separadores a la vez y está bien: un email o un username
**no puede tener una coma adentro**, así que partir por las dos nunca destruye un valor.
Con las áreas eso deja de valer: **"Legales, Compliance" es un nombre de área perfectamente
posible**, y con la regla de los responsables se convertiría en dos áreas que no existen. Sin
error, sin aviso, y con el filtro por área devolviendo cero para las dos.

La regla de prioridad resuelve el caso sin perder la comodidad del copiar y pegar:

    "Sistemas; Legales"                 -> ["Sistemas", "Legales"]          (hay `;`)
    "Legales, Compliance; Sistemas"     -> ["Legales, Compliance", "Sistemas"]  (hay `;`: la coma es CONTENIDO)
    "Sistemas, Legales"                 -> ["Sistemas", "Legales"]          (no hay `;`: la coma separa)
    "Legales, Compliance"               -> ["Legales", "Compliance"]        ⚠️ ver abajo

🔑 Y LO QUE LO VUELVE COHERENTE CON EL RESTO DEL SISTEMA: **el export ya junta las áreas con
`"; "`** (`_objetivos_export._areas`, sesión 1) exactamente por este motivo. O sea que **todo lo
que sale del sistema vuelve a entrar idéntico**: la planilla exportada, editada y resubida
conserva sus áreas con coma. El `;` no es una convención inventada acá, es la que el módulo ya
escribe.

⚠️ **EL CASO AMBIGUO, DICHO Y NO ESCONDIDO.** Una celda con UNA sola área que tiene coma y sin
ningún `;` —`"Legales, Compliance"` sola— entra como DOS. No hay información en esa celda para
decidir otra cosa, y entre las dos lecturas la más probable es que sean dos áreas ("Legales" y
"Compliance" son las dos nombres plausibles). La salida para quien de verdad quiera una sola es
escribir `"Legales, Compliance;"` — con el `;`, la coma pasa a ser contenido.
🔴 Esto es una limitación declarada, NO el caso que la migración 119 vino a arreglar. Aquél es el
del FILTRO: un área con coma ya guardada como un elemento tiene que poder buscarse entera, y eso
funciona (ver `utils/postgrest_array` y `_objetivo_area`). Acá lo único que se decide es cómo
leer una celda que el usuario escribió sin declarar su separador.

⚠️ NO se normaliza el contenido: no se pasa a Título, no se saca acento, no se deduplica contra
un catálogo. `areas_involucradas` es texto libre por decisión de producto — es una anotación de
contexto, no una FK a `areas`. Lo único que se hace es recortar espacios y descartar vacíos, para
que "Sistemas; ; Legales" no meta un elemento vacío en el array.
"""
from typing import List, Optional

_PRINCIPAL = ";"
_ALTERNATIVO = ","


def parse_fecha(valor: str) -> Optional[str]:
    """`d/m/Y` → `YYYY-MM-DD` para la base. None si está vacía o no se puede leer.

    Una fecha ilegible NO tumba la fila: `fecha_entrega` es opcional en el modelo, y perder un
    objetivo entero por una celda con "prox. mes" sería peor que cargarlo sin fecha. El reporte
    de la fila lo dice igual (`faltantes`), así que no es silencioso.
    """
    if not valor:
        return None
    partes = valor.replace("-", "/").split("/")
    if len(partes) != 3:
        return None
    try:
        d, m, a = (int(p) for p in partes)
    except ValueError:
        return None
    if a < 100:
        a += 2000
    return f"{a:04d}-{m:02d}-{d:02d}"


def separar_areas(valor: str) -> List[str]:
    """Celda del Excel → lista de áreas. Ver el encabezado para la regla de separadores.

    Args:
        valor: el contenido de la celda, ya recortado por `_get`. Vacío → lista vacía.

    Returns:
        Las áreas, sin espacios de borde y sin elementos vacíos. Conserva el ORDEN y los
        DUPLICADOS tal como los escribió el usuario: deduplicar acá escondería que la planilla
        repite un área, que es algo que quien la escribió quiere ver.

        >>> separar_areas("Legales, Compliance; Sistemas")
        ['Legales, Compliance', 'Sistemas']
        >>> separar_areas("Sistemas, Legales")
        ['Sistemas', 'Legales']
    """
    if not valor.strip():
        return []
    sep = _PRINCIPAL if _PRINCIPAL in valor else _ALTERNATIVO
    return [p.strip() for p in valor.split(sep) if p.strip()]
