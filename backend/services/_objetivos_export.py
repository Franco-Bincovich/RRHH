"""
EL EXPORT DE OBJETIVOS, entero: el acto (`exportar`) y la proyección de columnas legibles.

Extraído del service para no volcar model_dump() crudo (que incluía UUIDs). Los
headers del Excel son las keys de cada dict (el motor genérico las capitaliza).
No toca el motor de export.

🔴 `exportar` SE MUDÓ ACÁ EL 24/8/2026, al cablearle auditoría al módulo (bloque 1). El service
estaba en 142/150 y los cuatro eventos no entraban; la regla del repo es que un archivo que se
pasa **se divide, no se comprime**. De todo lo que había para sacar, el export es lo que menos
información pierde al moverse: el tope de filas —que se cuenta sobre el árbol APLANADO y no
sobre las raíces— queda ahora pegado a `_aplanar`, que es la función que produce esas filas. En
el service ese `contar_con_hijos` estaba a sesenta líneas de lo único que lo explica.
Lo que NO se movió es `create`/`update`: el docstring del service declara que ese archivo se
queda con la ORQUESTACIÓN —qué se valida y en qué ORDEN— y ahí el orden es load-bearing.

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
from typing import List, Optional
from uuid import UUID

from repositories._objetivos_arbol import contar_con_hijos
from schemas.objetivo import ObjetivoResponse
from schemas.objetivo_filtros import SIN_FILTROS, ObjetivosFiltros
from services._limite_export import verificar_limite_export
from services.export import Descarga, build_export


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


def exportar(repo, empresa_id: Optional[UUID] = None, formato: str = "excel",
             filtros: ObjetivosFiltros = SIN_FILTROS) -> Descarga:
    """Exporta los objetivos (columnas legibles, sin UUIDs) respetando los MISMOS filtros que el
    listado. `empresa_id=None` = consolidado. El motor genérico no se toca.

    🔑 Que el listado y el export reciban el MISMO objeto `ObjetivosFiltros` es lo que hace
    estructuralmente imposible que un filtro quede en uno solo de los dos — la invariante que
    `tests/test_paridad_list_export.py` verifica del lado del router.

    🔴 EL ARCHIVO TRAE PADRES E HIJOS, así que el tope de filas se cuenta sobre el árbol APLANADO
    y no sobre las raíces: `find_all` devuelve raíces con hijos anidados, y `len(items)` diría
    bastante menos de lo que se va a escribir. Con el conteo equivocado, un export de 15.000
    raíces con 15.000 hijos pasaría el tope de 20.000 y produciría 30.000 filas — que es justo el
    archivo demasiado grande que el tope existe para evitar.

    Args:
        repo: ObjetivoRepo (o doble).
        empresa_id: Empresa del request. None = consolidado.
        formato: pdf | excel | csv | word.
        filtros: los MISMOS seis que acepta el listado.

    Returns:
        La descarga lista para que el router la devuelva.

    Raises:
        AppError: EXPORT_DEMASIADAS_FILAS (422) si el árbol aplanado supera el tope.
    """
    items = repo.find_all(empresa_id, filtros)
    verificar_limite_export(contar_con_hijos(items))
    return build_export(nombre="Objetivos", datos={"Objetivos": construir_filas_export(items)},
                        filename_base="objetivos", formato=formato)
