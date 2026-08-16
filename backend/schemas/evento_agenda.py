"""
Schemas Pydantic de la agenda de eventos (migración 113).

QUÉ ES. Un recordatorio manual con fecha, que el dashboard levanta cuando se acerca. RRHH carga
nombre y fecha; el resto tiene default. **No es un registro histórico**: es un aviso, y por eso
—a diferencia de `recategorizaciones`— SE PUEDE EDITAR Y BORRAR. Uno cargado por error no tiene
por qué quedar; borrarlo no rompe ninguna cadena porque no cuelga nada de él.

🔴 `dias_aviso` NO TIENE DEFAULT EN EL SCHEMA DE ENTRADA, Y NO ES UN OLVIDO. Llega `None` y lo
completa el service leyendo `parametros_empresa.dias_aviso_evento` (migración 114). Un literal
acá sería una TERCERA definición del mismo número —ya están el default de la columna y el de la
configuración— y sería la que gana, dejando la pantalla de Configuración sin efecto sobre los
eventos nuevos: exactamente el bug de "el valor se guarda y no lo aplica nadie".

🔴 `resuelta` NO SE PUEDE TOCAR POR EL PUT, y tampoco `resuelta_at`/`resuelta_por`. Se resuelve
por su endpoint propio (`PUT /{id}/resuelta`), que es el único que sabe poner las tres columnas
de forma coherente con el CHECK `eventos_agenda_resuelta_coherente_check` (resuelta ⇒ hay
fecha). Aceptarlas en la edición genérica permitiría marcar `resuelta=true` sin `resuelta_at` y
el 23514 crudo de la base saldría como 500.

⚠️ `empresa_id` NO viaja en el body: sale del header (`require_empresa_id`). Es lo contrario de
`recategorizaciones`, que la deriva del empleado — y no es una inconsistencia, es la misma regla:
la empresa la decide la ENTIDAD PADRE cuando la hay. Un evento de agenda no tiene padre; su
empresa es la que está mirando quien lo carga, que es una elección explícita del formulario.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Topes de PRODUCTO: las dos columnas son `text` sin límite en la base. El nombre es lo que se
# lee en una tarjeta del dashboard —si no entra en un renglón, no sirve de aviso— y la
# descripción es una nota corta, no un documento.
MAX_NOMBRE = 120
MAX_DESCRIPCION = 1000

# Espejo del CHECK `eventos_agenda_dias_aviso_check`. Duplicado a propósito: Pydantic devuelve un
# 422 con el campo señalado y la base un 500 genérico. La base sigue siendo la garantía.
MIN_DIAS_AVISO, MAX_DIAS_AVISO = 0, 365


class EventoCreate(BaseModel):
    """Alta. Lo MÍNIMO es nombre y fecha; el resto tiene default o lo pone el sistema."""

    nombre: str = Field(..., min_length=1, max_length=MAX_NOMBRE)
    fecha: date
    descripcion: Optional[str] = Field(default=None, max_length=MAX_DESCRIPCION)
    # None = "usá el default de la empresa". Ver el encabezado del módulo.
    dias_aviso: Optional[int] = Field(default=None, ge=MIN_DIAS_AVISO, le=MAX_DIAS_AVISO)
    # `true` = lo ve el equipo; `false` = solo quien lo creó. El default es PÚBLICO porque la
    # agenda es del equipo: una privada por descuido no la ve nadie más y el evento no cumple
    # su función, mientras que una pública por descuido cuesta un ítem de más en el panel ajeno.
    es_publica: bool = True


class EventoUpdate(BaseModel):
    """Edición parcial. `None` = "no lo toques" (`exclude_none` en el write path).

    ⚠️ Una descripción SÍ se puede vaciar, mandando `""`: la cadena vacía no es `None`, así que
    viaja y pisa la columna. Es la diferencia con el resto de los `*Update` del repo, donde el
    campo vaciable es numérico o una fecha y ahí `None` es el único valor "vacío" disponible.
    Lo que no se puede es volver `descripcion` a NULL, y no hace falta: `''` y NULL se muestran
    igual, y distinguirlos obligaría a un centinela que ninguna pantalla necesita.
    """

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=MAX_NOMBRE)
    fecha: Optional[date] = None
    descripcion: Optional[str] = Field(default=None, max_length=MAX_DESCRIPCION)
    dias_aviso: Optional[int] = Field(default=None, ge=MIN_DIAS_AVISO, le=MAX_DIAS_AVISO)
    es_publica: Optional[bool] = None


class EventoResuelta(BaseModel):
    """El cuerpo del toggle de resuelta. UN endpoint para los dos sentidos, no dos.

    Resolver es REVERSIBLE (decisión de producto), así que "resolver" y "desresolver" son el
    mismo cambio de estado con distinto valor. Dos endpoints obligarían a que el front elija
    cuál llamar mirando el estado actual —que puede estar viejo— y a mantener dos caminos que
    escriben las mismas tres columnas.
    """

    resuelta: bool


class EventoResponse(BaseModel):
    """Lo que sale. Los ids van tipados `UUID`, nunca `str` (error #1 del porteo a asyncpg).

    Los tres nombres resueltos por join (`empresa_nombre`, `created_by_nombre`,
    `resuelta_por_nombre`) son DERIVADOS: no son datos de la fila sino resultado de cómo se la
    leyó. Por eso quedan fuera del diff de auditoría — ver `_audit_payloads_eventos`.
    """

    id: UUID
    empresa_id: UUID
    nombre: str
    fecha: date
    descripcion: Optional[str] = None
    dias_aviso: int
    es_publica: bool
    resuelta: bool
    resuelta_at: Optional[datetime] = None
    resuelta_por: Optional[UUID] = None
    resuelta_por_nombre: Optional[str] = None
    created_by: UUID
    created_by_nombre: Optional[str] = None
    empresa_nombre: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class EventoListResponse(BaseModel):
    """Página de la agenda. NACE PAGINADA, igual que la planilla de recategorizaciones.

    El listado de PENDIENTES (el que consume el dashboard) NO usa este schema: devuelve una
    lista plana y sin paginar, porque son los que caen dentro de su ventana de aviso — decenas,
    no miles, y un paginador de una página no le sirve a nadie.
    """

    items: List[EventoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
