"""
Vocabulario de columnas del Excel de objetivos y armado de una fila.

Molde: `_nomina_empleados_transforms.py` — qué columnas espera, cuáles son obligatorias, y cómo
se arma el dict de una fila. Los VALORES ya llegan como string desde `_import_excel` (que
resolvió `None`, floats y fechas), así que acá no hay nada de formato: solo vocabulario.

## 🔴 QUÉ DEL MODELO NUEVO SOPORTA ESTE IMPORT, Y QUÉ NO — DECLARADO, NO IMPLÍCITO

El modelo de objetivos cambió hace días: tiene `parent_id` (jerarquía de 2 niveles, migración
095) y la puente `objetivo_responsables` (096). Este import:

  · **SÍ soporta múltiples responsables.** Columna "Responsables" opcional, separados por `;` o
    `,`. Se resuelven contra `users` con la MISMA validación que el dueño, así que un
    acompañante inactivo se rechaza igual que un dueño inactivo.

  · **NO soporta la jerarquía: todo lo que importa nace como RAÍZ.** Y no es una omisión — es
    que un Excel no tiene con qué señalar al padre de forma confiable:
      1. La única columna posible sería el TÍTULO del padre, y **`objetivos.titulo` no tiene
         UNIQUE** (verificado en el catálogo): dos objetivos pueden llamarse igual y la fila
         quedaría colgada de cualquiera de los dos.
      2. Si el padre viene en el MISMO archivo, resolverlo exige una segunda pasada, y sin un
         identificador único el resultado dependería del ORDEN DE LAS FILAS del Excel — que es
         exactamente el bug que `_nomina_superiores` existe para evitar (migración 086).
    **Qué lo destrabaría:** que el archivo traiga un código estable por objetivo (una columna
    "Código" con UNIQUE en la base), o que la jerarquía se arme desde la pantalla después de
    importar, que es lo que hoy se hace con dos clicks en el modal.

  🔴 **Y NO SE IGNORA EN SILENCIO.** Si el archivo trae una columna de padre, el import
  **rechaza el archivo entero** con un mensaje que explica dónde armar la jerarquía. Aceptarlo
  y descartar la columna sería lo peor de los dos mundos: el usuario cree que cargó una
  jerarquía y carga una lista plana, y no se entera nunca.
"""
from typing import List, Optional

from services._import_csv import normalizar_header

# Nombres tal como se le muestran a quien tiene la planilla abierta.
COL_TITULO = "Titulo"
COL_RESPONSABLE = "Responsable"
COL_PRIORIDAD = "Prioridad"
COL_FECHA = "Fecha entrega"
COL_DESCRIPCION = "Descripcion"
COL_RESPONSABLES = "Responsables"

REQUERIDAS: List[str] = [COL_TITULO, COL_RESPONSABLE]
OPCIONALES: List[str] = [COL_PRIORIDAD, COL_FECHA, COL_DESCRIPCION, COL_RESPONSABLES]

# Columnas que delatan que el usuario espera cargar jerarquía. Ver el encabezado del módulo.
COLUMNAS_JERARQUIA = ["Objetivo padre", "Padre", "Subobjetivo de"]

MENSAJE_JERARQUIA = (
    "El archivo trae una columna de objetivo padre y este import no arma jerarquía: todos los "
    "objetivos se cargan como principales. Sacá esa columna y, una vez importados, asigná el "
    "objetivo padre desde la pantalla (Editar → Objetivo padre)."
)

_SEPARADORES = (";", ",")


def _get(fila: dict, columna: str) -> str:
    """Valor de una columna por su nombre normalizado. '' si no está."""
    return (fila.get(normalizar_header(columna)) or "").strip()


def trae_columna_de_jerarquia(headers: List[str]) -> bool:
    """True si el archivo trae alguna columna de padre — el import lo rechaza entero."""
    presentes = {normalizar_header(h) for h in headers if h}
    return any(normalizar_header(c) in presentes for c in COLUMNAS_JERARQUIA)


def parsear_fila(fila: dict) -> dict:
    """Fila cruda → campos del objetivo. No valida: eso lo hace el service contra `users`.

    `prioridad` cae a "media" cuando viene vacía o con un valor que no es del enum: es el mismo
    default que la columna en la base, y rechazar una fila entera por una prioridad mal escrita
    sería desproporcionado — el dato importante es el título y el responsable.
    """
    prioridad = _get(fila, COL_PRIORIDAD).lower()
    return {
        "titulo": _get(fila, COL_TITULO),
        "responsable": _get(fila, COL_RESPONSABLE),
        "prioridad": prioridad if prioridad in ("baja", "media", "alta") else "media",
        "fecha_entrega": _get(fila, COL_FECHA),
        "descripcion": _get(fila, COL_DESCRIPCION) or None,
        "responsables": _separar(_get(fila, COL_RESPONSABLES)),
    }


def _separar(valor: str) -> List[str]:
    """"ana@x.com; beto@x.com" → ["ana@x.com", "beto@x.com"]. Acepta `;` y `,`.

    Los dos separadores porque el archivo lo escribe una persona: en un Excel en español el `;`
    es el natural, pero el `,` es el que sale de copiar y pegar de cualquier otro lado.
    """
    if not valor:
        return []
    for sep in _SEPARADORES:
        valor = valor.replace(sep, "\n")
    return [p.strip() for p in valor.split("\n") if p.strip()]


def identificador(fila: dict) -> str:
    """Cómo se nombra una fila en el reporte de errores: por su título, que es lo que el
    usuario reconoce al mirar la planilla. Vacío → un marcador, nunca una cadena vacía."""
    return _get(fila, COL_TITULO) or "(sin título)"


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
