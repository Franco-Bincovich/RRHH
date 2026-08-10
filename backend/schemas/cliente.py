"""
Schemas Pydantic del catálogo de clientes (migración 102).

ARCHIVO PROPIO Y NO `schemas/proyectos.py`: ese está en 175/200 con 8 clases, y sumarle cuatro
más lo pasaba. Pero el motivo de fondo no es el límite — es que **`proyectos` no participa del
flujo de clientes**. Las 8 filas de `proyectos` en producción son una copia de
`empleados.gerencia` que crea el import de nómina; un cliente no cuelga de ninguna de ellas ni al
revés. Meter los dos modelos en el mismo archivo sugeriría un parentesco que no existe.

ClienteCreate → ClienteUpdate → ClienteResponse → ClienteListResponse. Molde: `schemas/area.py`,
que es el otro catálogo por empresa que RRHH edita.

`empresa_id` va explícito en el Create (empresa DUEÑA, del formulario) y NO sale del header
`X-Empresa-Id`: crear un cliente es una ACCIÓN, y en modo consolidado el header es None. Es el
principio Vista vs Acción, igual que `ProyectoCreate` y `AreaCreate`.

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
    empresa_id: UUID
    nombre: str = Field(..., max_length=120)


class ClienteUpdate(BaseModel):
    # `empresa_id` NO es modificable: mudar un cliente de empresa dejaría las horas ya cargadas
    # imputadas a una sociedad que no es la que facturó. Mismo criterio que ProyectoUpdate.
    nombre: Optional[str] = Field(default=None, max_length=120)
    activo: Optional[bool] = None


class ClienteResponse(BaseModel):
    id: UUID
    empresa_id: UUID
    nombre: str
    activo: bool
    created_at: datetime
    # Optional porque lo pone un trigger de base (mig 102) y no la app: si algún día se lee una
    # fila de una base sin el trigger, el campo viene ausente y no tiene que romper la respuesta.
    updated_at: Optional[datetime] = None


class ClienteListResponse(BaseModel):
    items: List[ClienteResponse]
    total: int
