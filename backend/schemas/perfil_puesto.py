"""
Schemas Pydantic del catálogo de perfiles de puesto (migraciones 113 y 116).

Un perfil es una PLANTILLA para armar búsquedas: Capital Humano la carga a mano y la reusa. Al
crear una vacante se elige un perfil y los campos se COPIAN — editar el perfil después NO cambia
las vacantes ya creadas. Ese puente es una sesión aparte; acá vive solo el CRUD del catálogo.

🔴 UN PERFIL ES DEL GRUPO: NO TIENE `empresa_id` NI `area_id`, y las dos ausencias son la
decisión de fondo, no un olvido. `areas.empresa_id` es NOT NULL, así que un perfil con área
quedaría atado a una empresa por transitividad y chocaría con `trg_emp_vacantes` al copiarse a
la vacante. El área se ELIGE al crear la vacante, y el trigger sigue siendo la red que impide el
cruce. Molde: `schemas/cliente.py`, el otro —y hasta ahora único— catálogo global del sistema.

🔴 LO QUE UN PERFIL **NO** TIENE, escrito para que no se vuelva a proponer: **competencias**,
**ubicación** y **contador de ocupantes o de vacantes**. Las tres las inventó un prototipo y no
están en el modelo. El aviso real (`docs/AVISO-BUSQUEDA-REFERENCIA.md`) no las usa: la ubicación
es de la búsqueda concreta (`vacantes.ubicacion`) y los contadores se derivan de `vacantes`
cuando hagan falta, no se persisten.

⚠️ LOS TRES VOCABULARIOS CERRADOS (`modalidad`, `tipo_contrato`, `nivel`) SON COPIA LITERAL DE
LOS CHECK DE `vacantes`, igual que en la migración 113. Se declaran como `Literal` y no como
`str` a propósito: un valor fuera de la lista tiene que salir como **422 de validación**, con el
nombre del campo, y no como el 23514 crudo de la base convertido en 500. Si algún día se
reescribieran "parecido", un perfil podría guardar un valor que la vacante rechaza al copiarlo,
y el error aparecería recién al crear la búsqueda.

Los LABELS y los textos de ayuda de cada campo NO están acá: viven en `_perfil_puesto_campos.py`
y se sirven por endpoint, para que el front no los duplique. Leer ese archivo antes de tocar el
formulario — la separación entre `experiencia`, `formacion`, `conocimientos_tecnicos` y
`requisitos` se pierde sola si nadie la explica.
"""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Copia literal de los CHECK de la migración 113 (que a su vez los copió de `vacantes`).
Modalidad = Literal["presencial", "remoto", "hibrido"]
TipoContrato = Literal["efectivo", "plazo_fijo", "contratado", "pasantia"]
Nivel = Literal["junior", "semi_senior", "senior", "lider", "manager", "director", "c_level"]

# `perfiles_puesto.nombre` es `text` sin límite en la base: este tope es de PRODUCTO, no de
# schema. El nombre se muestra entero en un selector y en el título de la vacante que lo copia;
# más de esto no se lee, se trunca visualmente y deja de servir para elegir.
MAX_NOMBRE = 120


class PerfilPuestoBase(BaseModel):
    """Los 12 campos editables de un perfil, en el orden en que se llenan.

    🔴 EL ORDEN NO ES DECORATIVO. `requisitos` va ÚLTIMO y después de los tres campos que le
    sacan contenido (`experiencia`, `formacion`, `conocimientos_tecnicos`), porque el bloque
    "Requisitos" del aviso real mezcla las cuatro naturalezas bajo un solo título. Puesto
    primero, se convierte en el cajón donde entra todo y los otros tres quedan vacíos — ver
    `_perfil_puesto_campos.NOTA_REQUISITOS`.
    """

    nombre: str = Field(..., min_length=1, max_length=MAX_NOMBRE)
    descripcion: Optional[str] = None
    funciones: Optional[str] = None
    experiencia: Optional[str] = None
    formacion: Optional[str] = None
    conocimientos_tecnicos: Optional[str] = None
    requisitos: Optional[str] = None
    ofrecemos: Optional[str] = None
    modalidad: Optional[Modalidad] = None
    tipo_contrato: Optional[TipoContrato] = None
    nivel: Optional[Nivel] = None
    jornada: Optional[str] = None


class PerfilPuestoCreate(PerfilPuestoBase):
    """Alta. `created_by` NO viaja en el body: sale del usuario autenticado del request.

    Aceptarlo del cliente permitiría atribuirle el alta a cualquier otro usuario, que es
    exactamente lo que la columna existe para impedir.
    """


class PerfilPuestoUpdate(BaseModel):
    """Edición parcial. Todo opcional; `None` significa "no lo toques".

    ⚠️ CONSECUENCIA ASUMIDA, ESCRITA PARA QUE NO SORPRENDA: el service arma el patch con
    `exclude_none`, así que **`null` no vacía un campo**. Para borrar el contenido de un campo
    de texto se manda la cadena vacía (`""`), que sí viaja y sí se escribe. Es el mismo
    contrato que `ClienteUpdate` y el que el resto del repo ya usa; lo que cambia acá es que un
    perfil tiene 8 campos de texto largo y vaciarlos es una operación real, no teórica.
    """

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=MAX_NOMBRE)
    descripcion: Optional[str] = None
    funciones: Optional[str] = None
    experiencia: Optional[str] = None
    formacion: Optional[str] = None
    conocimientos_tecnicos: Optional[str] = None
    requisitos: Optional[str] = None
    ofrecemos: Optional[str] = None
    modalidad: Optional[Modalidad] = None
    tipo_contrato: Optional[TipoContrato] = None
    nivel: Optional[Nivel] = None
    jornada: Optional[str] = None
    activo: Optional[bool] = None


class PerfilPuestoResponse(PerfilPuestoBase):
    """Lo que sale. Los ids van tipados `UUID`, nunca `str`.

    🔴 No es cosmética: es el error #1 del porteo a asyncpg, que devuelve UUID nativos donde
    Supabase devuelve strings. Un campo declarado `str` valida hoy y revienta el día del
    cutover — ya pasó con `AreaCreate` y salió como un 500 en producción.
    """

    id: UUID
    activo: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    # Optional porque lo pone un trigger de base (`trg_perfiles_puesto_updated_at`) y no la app:
    # si alguna vez se lee una fila de una base sin el trigger, el campo viene ausente y no tiene
    # que romper la respuesta. Mismo criterio que `ClienteResponse.updated_at`.
    updated_at: Optional[datetime] = None


class PerfilPuestoListResponse(BaseModel):
    """Página del listado. NACE PAGINADO — ver el docstring del repo.

    `total` es el total REAL del filtro (`count="exact"`), no el largo de `items`: sin eso el
    front no puede dibujar el paginador ni el export puede saber si se pasó del tope.
    """

    items: List[PerfilPuestoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
