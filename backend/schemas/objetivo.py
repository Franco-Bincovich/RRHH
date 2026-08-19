"""
Schemas Pydantic para el módulo de objetivos.
ObjetivoCreate → Update → Response → ListResponse

responsable_id: FK a users (operadores RRHH), NO empleados.
empresa_id: explícito en Create; heredado por el objeto en lecturas.
estado: no se pide al crear (default 'por_hacer'); se cambia por CambiarEstadoRequest.

JERARQUÍA (migración 095): `parent_id` self-FK, profundidad máxima 2 — un objetivo con padre no
puede ser padre de otro. La guarda vive en services/_objetivos_jerarquia.py, no en un CHECK.

MÚLTIPLES RESPONSABLES (migración 096): `responsable_id` sigue siendo el DUEÑO PRINCIPAL y no se
toca; `responsables` es la lista COMPLETA (incluye al dueño) que arma la tabla puente.

LAS DOS VISTAS (migración 119): `tipo` dice a cuál pertenece el objetivo. Ver `TIPOS` abajo.

⚠️ LOS FILTROS DE LECTURA NO ESTÁN ACÁ: viven en `schemas/objetivo_filtros.py`, que salió de este
archivo cuando lo pasó de 200 líneas. Este módulo tiene los DTO del RECURSO (alta, edición,
respuesta) y los vocabularios; aquél, el objeto de filtros del listado y del export.
"""
from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

PRIORIDADES = {"baja", "media", "alta"}
ESTADOS = {"por_hacer", "haciendo", "terminado"}
ORDEN_ESTADOS = ["por_hacer", "haciendo", "terminado"]

# ── Las dos vistas del módulo (migración 119) ─────────────────────────────────
# Un objetivo pertenece a UNA y no se comparte. La vista ANUAL es la que Capital Humano le
# presenta al directorio; la OPERATIVA acepta cualquier expresión de tiempo (`periodicidad`).
TIPOS = {"anual", "operativo"}
TipoObjetivo = Literal["anual", "operativo"]

# 🔴 EL DEFAULT DE PRODUCTO ES 'operativo' Y EL DE LA COLUMNA ES 'anual'. NO ES UNA
# CONTRADICCIÓN: son dos preguntas distintas y las dos están contestadas donde corresponde.
#   · La BASE (`objetivos.tipo DEFAULT 'anual'`, migración 119) contesta "¿qué pasa con las
#     filas que YA existían cuando apareció la columna?". Había una y tenía que quedar ANUAL,
#     así que el backfill salió gratis con ese default y no hizo falta un UPDATE.
#   · PRODUCTO contesta "¿en qué vista NACE lo que se carga de ahora en adelante?", y ahí la
#     respuesta es OPERATIVO porque es la vista permisiva: mandar un objetivo cualquiera a la
#     vista que ve el directorio es peor error que al revés.
# Por eso este literal vive acá y no en la migración, y por eso el de la migración no se cambió
# a 'operativo' "para que sean iguales": eso habría roto el único backfill que tenía que hacer.
# 🔑 El IMPORT hereda este default GRATIS y sin una línea propia: `objetivos_import_service`
# arma un `ObjetivoCreate` sin `tipo`, así que toma el de abajo. Cuando el Excel traiga su
# columna `Tipo` (sesión 2), ese valor pisa el default; mientras tanto, todo lo importado nace
# operativo, que es lo decidido.
TIPO_POR_DEFECTO: TipoObjetivo = "operativo"

# ── El vocabulario con sus etiquetas, para servirlo por endpoint ──────────────
# 🔴 EL FRONT NO HARDCODEA ESTOS DOS VALORES: los pide a `GET /api/objetivos/campos`. Mismo
# criterio y mismo precedente que `_perfil_puesto_campos` y `_provincias` — el `value` ES el
# literal del CHECK de la base Y el del `Literal` de arriba, así que una copia en el front que
# derive ofrecería en un selector un valor que el backend rechaza con 422.
#
# ⚠️ ESTO VIVE ACÁ Y NO EN UN `_objetivo_campos.py` APARTE, al revés que el molde. La razón por
# la que aquel archivo existe es su tamaño (195 líneas de labels y textos de ayuda); acá son dos
# opciones, y ponerlas PEGADAS al `Literal` y al set que describen es lo que hace imposible que
# se agregue un tercer tipo al vocabulario y quede sin etiqueta —o al revés—. La divergencia que
# el molde evita separando, acá se evita juntando.
# El `label` es presentación y cambiarlo es gratis; cambiar un `value` rompe la validación, el
# CHECK de la base y las filas ya guardadas.
TIPOS_OPCIONES: List[dict] = [
    {"value": "anual", "label": "Anual"},
    {"value": "operativo", "label": "Operativo"},
]


class ObjetivoCreate(BaseModel):
    empresa_id:     UUID
    responsable_id: UUID
    titulo:         str
    descripcion:    Optional[str] = None
    prioridad:      str = "media"
    fecha_entrega:  Optional[date] = None
    parent_id:      Optional[UUID] = None       # None = objetivo raíz
    # Responsables ADICIONALES al dueño. El dueño entra siempre a la puente, venga o no acá.
    responsables:   Optional[List[UUID]] = None
    # 🔴 EL TIPO NO SE HEREDA DEL PADRE, y es una decisión de producto, no un pendiente: un
    # OPERATIVO colgando de un ANUAL es el caso útil —el objetivo del año se descompone en
    # tareas del trimestre— así que no hay guarda que vigilar en `_objetivos_jerarquia`.
    tipo:           TipoObjetivo = TIPO_POR_DEFECTO
    # Texto libre a propósito (migración 114): "primer trimestre", "tercera semana de
    # septiembre", una fecha suelta. Sólo tiene sentido en un operativo — un anual ya es del año.
    periodicidad:   str = ""
    # Las áreas de OTRAS empresas con las que se comparte el objetivo. NO es `area_id`: los
    # objetivos son del equipo de RRHH y su área principal es siempre la misma.
    areas_involucradas: List[str] = Field(default_factory=list)


class ObjetivoUpdate(BaseModel):
    responsable_id: Optional[UUID] = None
    titulo:         Optional[str] = None
    descripcion:    Optional[str] = None
    prioridad:      Optional[str] = None
    fecha_entrega:  Optional[date] = None
    parent_id:      Optional[UUID] = None
    # `None` = no se toca la lista. `[]` = se deja solo al dueño. Ver services/objetivo_service.
    responsables:   Optional[List[UUID]] = None
    # Se puede cambiar de vista desde la pantalla: es una columna editable, no una clasificación
    # de nacimiento. `None` = no se toca.
    tipo:           Optional[TipoObjetivo] = None
    # ⚠️ En estos dos, `None` y el vacío NO son lo mismo, y de eso depende que se puedan BORRAR.
    # `objetivo_repo.update` arma el patch con `model_dump(exclude_none=True)`: `None` se cae del
    # patch (no se toca la columna) y `""` / `[]` sobreviven y llegan a la base como el valor
    # vacío. Sin esa distinción no habría forma de sacarle la periodicidad o las áreas a un
    # objetivo que ya las tiene.
    periodicidad:   Optional[str] = None
    areas_involucradas: Optional[List[str]] = None


class ResponsableItem(BaseModel):
    """Un responsable del objetivo, con el nombre ya resuelto desde `users`."""
    id:     str
    nombre: Optional[str] = None


class CambiarEstadoRequest(BaseModel):
    estado: str


class ObjetivoResponse(BaseModel):
    id:                  str
    empresa_id:          str
    empresa_nombre:      Optional[str] = None
    responsable_id:      str
    responsable_nombre:  Optional[str] = None
    titulo:              str
    descripcion:         Optional[str] = None
    prioridad:           str
    estado:              str
    fecha_entrega:       Optional[date] = None
    created_at:          datetime
    updated_at:          datetime
    parent_id:           Optional[str] = None
    parent_titulo:       Optional[str] = None   # derivado: alimenta la columna del export
    # 🔴 `tipo` VA SIN DEFAULT, al revés que los dos de abajo, y no es un descuido.
    # `periodicidad` y `areas_involucradas` tienen un vacío que SIGNIFICA algo ("sin
    # periodicidad", "sin áreas compartidas") y la columna lo garantiza con su propio DEFAULT,
    # así que un default acá no puede inventar nada. `tipo` no tiene valor neutro: todo objetivo
    # ES anual o ES operativo, y ponerle un default sería INVENTAR a qué vista pertenece una
    # fila que llegó sin decirlo. Requerido, un row sin `tipo` revienta acá y no en la pantalla.
    tipo:                TipoObjetivo
    periodicidad:        str = ""
    areas_involucradas:  List[str] = Field(default_factory=list)
    # Lista COMPLETA de responsables (el dueño incluido). Vacía solo si la puente no tiene filas.
    responsables:        List[ResponsableItem] = []
    # Subobjetivos anidados. Siempre vacía en un hijo: la profundidad máxima es 2.
    hijos:               List["ObjetivoResponse"] = []


ObjetivoResponse.model_rebuild()   # `hijos` se referencia a sí misma


class ObjetivoListResponse(BaseModel):
    items: List[ObjetivoResponse]
    # 🔴 HOY `total == len(items)` PORQUE EL TABLERO NO PAGINA: `objetivo_repo.find_all` devuelve
    # todo el árbol del filtro.
    # 🔴 EL DÍA QUE PAGINE, `total` SALE DE `count="exact"` DE LA MISMA QUERY — y acá hay una
    # trampa propia: `items` son las RAÍCES, con los hijos anidados adentro. O sea `len(items)` ya
    # no es la cantidad de objetivos ni cuando NO se pagina. `total` cuenta raíces (es lo que
    # pagina); el conteo aplanado que usa el export es otra cosa y sale de
    # `_objetivos_arbol.contar_con_hijos`. Confundirlos hace que el tope de export deje pasar el
    # doble de filas. Los tres pasos de la migración, en `services/_paginacion.py`.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0

    # ── 🔴 CONTRATO CON EL FRONTEND — LEER ANTES DE ESCRIBIR EL TABLERO ───────────────────────
    # EL TABLERO DE OBJETIVOS SE CONSTRUYE CONTRA ESTE WRAPPER, **AUNQUE HOY EL BACKEND DEVUELVA
    # TODO**. La respuesta YA tiene la forma final `{items, total, page, page_size, total_pages}`;
    # lo único provisorio es que `total == len(items)`.
    #
    # Concretamente, y sin excepción: el front lee **`total`** para los contadores del encabezado,
    # monta **`Pagination`**, y **NUNCA asume que le llegó el conjunto completo** — nada de
    # `items.length` como total, nada de `.reduce()` sobre `items` para sacar un agregado, nada de
    # filtrar o contar en el cliente lo que el backend ya sabe contar.
    #
    # POR QUÉ IMPORTA AHORA Y NO CUANDO SE PAGINE: si el tablero se escribe contra "me llega
    # todo", el día que el backend pagine hay que volver a tocarlo entero —contadores, filtros y
    # agregados—, y ese día ya es septiembre. Escrito contra el wrapper, **el front no cambia una
    # sola línea**: le empiezan a llegar 20 de 68 y todo lo que muestra sigue siendo correcto.
    # Es exactamente el bug que `HorasTab` ya pagó una vez (decía "9 h" con 400 h cargadas,
    # porque sumaba con `.reduce()` sobre la página en vez de leer el total del backend).
