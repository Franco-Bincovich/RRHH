"""
Proyección de columnas legibles para el export de objetivos.

Extraído del service para no volcar model_dump() crudo (que incluía UUIDs). Los
headers del Excel son las keys de cada dict (el motor genérico las capitaliza).
No toca el motor de export.

🔴 LA JERARQUÍA SE APLANA CON UNA COLUMNA "Objetivo padre", NO CON INDENTACIÓN. `find_all`
devuelve raíces con sus hijos anidados; acá se recorre ese árbol y sale UNA FILA POR OBJETIVO,
padre o hijo, con el título del padre en su propia columna (vacía en las raíces).

Por qué esa forma y no filas indentadas con espacios: lo primero que hace alguien de RRHH con un
Excel es ordenar o filtrar por una columna, y ahí la indentación se desarma —quedan títulos con
espacios raros y el árbol deja de existir— mientras que la columna sobrevive intacta. Cada fila
se explica sola sin depender de la de arriba. Además `csv` y `pdf` no indentan igual que `xlsx`,
así que el mismo archivo se leería distinto según el formato elegido.

Por qué NO se exportan solo los padres: la fecha de entrega real vive en los subobjetivos. Un
archivo con solo las raíces mentiría por omisión justo en la columna por la que se abre.

⚠️ El aplanado emite el padre y DESPUÉS sus hijos, en el orden en que vienen del árbol. Eso hace
que el archivo recién bajado se lea como la pantalla; después de que el usuario lo ordene, la
columna "Objetivo padre" es lo único que sostiene la relación — que es exactamente para lo que
está.
"""
from typing import List

from schemas.objetivo import ObjetivoResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def _aplanar(raices: List[ObjetivoResponse]) -> List[ObjetivoResponse]:
    """Árbol → lista: cada raíz seguida de sus hijos. No recursiona (profundidad máxima 2)."""
    out: List[ObjetivoResponse] = []
    for r in raices:
        out.append(r)
        out.extend(r.hijos)
    return out


def _responsables(o: ObjetivoResponse) -> str:
    """Los responsables como texto, separados por coma. Cae al dueño si la lista está vacía.

    Una lista de objetos en una celda saldría como el `repr` de Python: el motor de export
    renderiza escalares. El dueño va igual en su propia columna, así que esta se lee como
    "quiénes más": si son la misma persona, las dos columnas coinciden y eso es correcto.
    """
    nombres = [r.nombre for r in o.responsables if r.nombre]
    return ", ".join(nombres) if nombres else (o.responsable_nombre or "")


def _areas(o: ObjetivoResponse) -> str:
    """Las áreas involucradas como texto, separadas por "; ". Vacío si no hay ninguna.

    🔴 SE UNE CON "; " Y NO CON ", " a propósito, aunque `_responsables` de arriba use la coma:
    desde la migración 119 un área es un ELEMENTO de un `text[]` y puede tener comas adentro
    ("Legales, Compliance"). Con coma, ese único área se leería en el Excel como dos, que es
    justamente la ambigüedad que la migración vino a sacar de la base — reintroducirla en el
    archivo dejaría el export mintiendo donde el filtro ya no miente. El `;` es además el
    separador que el import del módulo ya entiende, así que lo exportado se puede volver a subir.

    Un array vacío tiene que salir como celda vacía, no como "[]": el motor de export renderiza
    escalares, y un `str(lista)` volcaría la representación de Python.
    """
    return "; ".join(o.areas_involucradas)


def construir_filas_export(items: List[ObjetivoResponse]) -> List[dict]:
    """Proyecta el árbol de objetivos a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": o.empresa_nombre,
            "Objetivo padre": o.parent_titulo,
            "Responsable": o.responsable_nombre,
            "Responsables": _responsables(o),
            "Título": o.titulo,
            "Descripción": o.descripcion,
            # 🔑 "Tipo" va junto a prioridad y estado —las tres clasifican al objetivo— y no al
            # final: quien abre el archivo para separar los anuales de los operativos tiene que
            # encontrar la columna sin desplazarse hasta la última.
            "Tipo": o.tipo,
            "Prioridad": o.prioridad,
            "Estado": o.estado,
            # Periodicidad pegada a la fecha de entrega: las dos dicen CUÁNDO. En un anual sale
            # vacía y eso es correcto — un anual ya es del año.
            "Periodicidad": o.periodicidad,
            "Fecha entrega": _fecha(o.fecha_entrega),
            "Áreas involucradas": _areas(o),
            "Creada": _fecha(o.created_at),
            "Actualizada": _fecha(o.updated_at),
        }
        for o in _aplanar(items)
    ]
