"""
Schemas Pydantic del catálogo de clientes (migración 102).

ARCHIVO PROPIO Y NO `schemas/proyectos.py`: ese está en 175/200 con 8 clases, y sumarle cuatro
más lo pasaba. Pero el motivo de fondo no es el límite — es que **`proyectos` no participa del
flujo de clientes**. Las 8 filas de `proyectos` en producción son una copia de
`empleados.gerencia` que crea el import de nómina; un cliente no cuelga de ninguna de ellas ni al
revés. Meter los dos modelos en el mismo archivo sugeriría un parentesco que no existe.

ClienteCreate → ClienteUpdate → ClienteResponse → ClienteListResponse. Molde: `schemas/area.py`,
que es el otro catálogo por empresa que RRHH edita.

🔴 UN CLIENTE NO PERTENECE A NINGUNA EMPRESA (migración 108). `empresa_id` no está en ninguno de
los tres schemas — ni entra en el alta ni sale en la respuesta. Revierte la decisión de la 102
("no hay clientes globales"): el catálogo pasa a comportarse como `tipos_ausencia`, se ve y se
edita con el sidebar en cualquier modo, y cualquier empleado imputa horas contra cualquier
cliente. Por eso acá tampoco aplica el Vista vs Acción: no hay empresa que elegir en ningún lado.

⚠️ `ClienteResponse` se valida contra filas que TODAVÍA traen la columna (la 108 solo saca el
NOT NULL; la columna se dropea en la 109). Pydantic ignora las claves de más, así que la
respuesta simplemente deja de exponerla — y el día que la columna desaparezca, nada cambia acá.

NO hay `ClienteDelete` ni el repo tiene `delete`, y no es un olvido: `horas_proyecto.cliente_id`
es una FK sin ON DELETE, así que borrar un cliente con horas fallaría — y si no fallara, se
llevaría puesto el historial de imputación. La baja es `activo=False`. Mismo razonamiento, escrito
en el repo, que `tipos_ausencia_repo.update`.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClienteCreate(BaseModel):
    nombre: str = Field(..., max_length=120)


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=120)
    activo: Optional[bool] = None


class ClienteResponse(BaseModel):
    id: UUID
    nombre: str
    activo: bool
    created_at: datetime
    # Optional porque lo pone un trigger de base (mig 102) y no la app: si algún día se lee una
    # fila de una base sin el trigger, el campo viene ausente y no tiene que romper la respuesta.
    updated_at: Optional[datetime] = None


class ClienteListResponse(BaseModel):
    items: List[ClienteResponse]
    total: int
