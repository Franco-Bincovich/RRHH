"""
Escrituras del catálogo de clientes: alta, edición y baja lógica.

Separado de `clientes.py` y montado en el MISMO prefijo, así que las rutas no cambian. El porqué
del corte está en el docstring de ese archivo.

⚠️ El `DELETE` responde 204 y hace una baja LÓGICA (`activo=False`), no un borrado físico. El
verbo es el correcto —para quien consume la API el cliente deja de estar— y el motivo por el que
la fila sobrevive está en `services/cliente_service.py`: `horas_proyecto.cliente_id` es una FK
sin ON DELETE, así que un DELETE real sobre un cliente con horas cargadas saldría como 500.
Mismo contrato que `areas_escrituras.py`.

`_usuario_id` se IMPORTA de `routers.clientes` en vez de duplicarse (ver su docstring).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers.clientes import _usuario_id
from schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate
from services.cliente_service import ClienteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.CLIENTES


def _service() -> ClienteService:
    return ClienteService()


@router.post("", response_model=ClienteResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_cliente(
    request: Request,
    body: ClienteCreate,
    service: ClienteService = Depends(_service),
) -> ClienteResponse:
    # La empresa sale del BODY, no del header: crear es una ACCIÓN (Vista vs Acción).
    return service.create_cliente(body, _usuario_id(request))


@router.put("/{id}", response_model=ClienteResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_cliente(
    id: UUID,
    body: ClienteUpdate,
    request: Request,
    service: ClienteService = Depends(_service),
) -> ClienteResponse:
    return service.update_cliente(id, body, get_empresa_id(request), _usuario_id(request))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_cliente(
    id: UUID,
    request: Request,
    service: ClienteService = Depends(_service),
) -> None:
    service.delete_cliente(id, get_empresa_id(request), _usuario_id(request))
