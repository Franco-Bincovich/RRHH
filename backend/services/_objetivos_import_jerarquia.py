"""
Por qué el import NO arma jerarquía, y cómo rechaza un archivo que la trae.

Salió de `_objetivos_import_transforms.py`, que con la tolerancia a acentos de `_get` quedaba en
171 contra un tope de 150. El corte es por PREGUNTA y no sólo por líneas: allá se contesta "cómo
se llaman las columnas y qué hay en cada una"; acá, "qué columna hace que el archivo entero se
rechace, y por qué". Es además el bloque más estable de los tres —no se toca desde que se
escribió— así que separarlo saca del camino 35 líneas que nadie vuelve a leer.

## 🔴 QUÉ DEL MODELO SOPORTA ESTE IMPORT, Y QUÉ NO — DECLARADO, NO IMPLÍCITO

El modelo de objetivos tiene `parent_id` (jerarquía de 2 niveles, migración 095) y la puente
`objetivo_responsables` (096). Este import:

  · **SÍ soporta múltiples responsables.** Columna "Responsables" opcional, separados por `;` o
    `,`. Se resuelven contra `users` con la MISMA validación que el dueño, así que un acompañante
    inactivo se rechaza igual que un dueño inactivo.

  · **SÍ soporta las tres columnas de la migración 119** (Tipo, Periodicidad, Areas
    involucradas), las tres opcionales. Ver `_objetivos_import_transforms`.

  · **NO soporta la jerarquía: todo lo que importa nace como RAÍZ.** Y no es una omisión — es que
    un Excel no tiene con qué señalar al padre de forma confiable:
      1. La única columna posible sería el TÍTULO del padre, y **`objetivos.titulo` no tiene
         UNIQUE** (verificado en el catálogo): dos objetivos pueden llamarse igual y la fila
         quedaría colgada de cualquiera de los dos.
      2. Si el padre viene en el MISMO archivo, resolverlo exige una segunda pasada, y sin un
         identificador único el resultado dependería del ORDEN DE LAS FILAS del Excel — que es
         exactamente el bug que `_nomina_superiores` existe para evitar (migración 086).
    **Qué lo destrabaría:** que el archivo traiga un código estable por objetivo (una columna
    "Código" con UNIQUE en la base), o que la jerarquía se arme desde la pantalla después de
    importar, que es lo que hoy se hace con dos clicks en el modal.

  🔴 **Y NO SE IGNORA EN SILENCIO.** Si el archivo trae una columna de padre, el import **rechaza
  el archivo entero** con un mensaje que explica dónde armar la jerarquía. Aceptarlo y descartar
  la columna sería lo peor de los dos mundos: el usuario cree que cargó una jerarquía y carga una
  lista plana, y no se entera nunca.
"""
from typing import List

from services._import_csv import normalizar_header

# Columnas que delatan que el usuario espera cargar jerarquía. Ver el encabezado del módulo.
COLUMNAS_JERARQUIA = ["Objetivo padre", "Padre", "Subobjetivo de"]

MENSAJE_JERARQUIA = (
    "El archivo trae una columna de objetivo padre y este import no arma jerarquía: todos los "
    "objetivos se cargan como principales. Sacá esa columna y, una vez importados, asigná el "
    "objetivo padre desde la pantalla (Editar → Objetivo padre)."
)


def trae_columna_de_jerarquia(headers: List[str]) -> bool:
    """True si el archivo trae alguna columna de padre — el import lo rechaza entero.

    ⚠️ Compara con `normalizar_header` a secas, sin el reintento sin acentos de `_get`, y acá da
    igual: ninguno de los tres nombres de `COLUMNAS_JERARQUIA` lleva acento. Si alguna vez se
    agrega uno que sí, hay que usar la misma comparación que `_get`.
    """
    presentes = {normalizar_header(h) for h in headers if h}
    return any(normalizar_header(c) in presentes for c in COLUMNAS_JERARQUIA)
