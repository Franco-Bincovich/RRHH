"""
Escrituras del catálogo de perfiles de puesto: alta, edición y baja lógica.

Separado de `perfiles_puesto.py` y montado en el MISMO prefijo, así que las rutas no cambian. El
porqué del corte está en el docstring de ese archivo.

⚠️ El `DELETE` responde 204 y hace una baja LÓGICA (`activo=False`), no un borrado físico. El
verbo es el correcto —para quien consume la API el perfil deja de estar— y el motivo por el que
la fila sobrevive está en `services/perfil_puesto_service.py`: `vacantes.perfil_puesto_id` es
una FK `ON DELETE SET NULL`, así que un DELETE real no fallaría pero le arrancaría en silencio
la trazabilidad a toda vacante creada desde ese perfil. Mismo contrato que
`clientes_escrituras.py`.

`_usuario_id` se IMPORTA de `routers.perfiles_puesto` en vez de duplicarse (ver su docstring).
Acá cumple DOS funciones distintas y las dos importan: es el `created_by` que se persiste en el
alta y es el `usuario_id` del evento de auditoría de las tres operaciones.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers.perfiles_puesto import _usuario_id
from schemas.perfil_puesto import (
    PerfilPuestoCreate, PerfilPuestoResponse, PerfilPuestoUpdate,
)
from services.perfil_puesto_service import PerfilPuestoService
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.PERFILES_PUESTO


def _service() -> PerfilPuestoService:
    return PerfilPuestoService()


@router.post("", response_model=PerfilPuestoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_perfil(
    request: Request,
    body: PerfilPuestoCreate,
    service: PerfilPuestoService = Depends(_service),
) -> PerfilPuestoResponse:
    # Sin empresa por ningún lado: el perfil es del GRUPO (migración 113). `created_by` sale del
    # usuario autenticado y NO del body — ver `PerfilPuestoCreate`.
    return service.create_perfil(body, _usuario_id(request))


@router.put("/{id}", response_model=PerfilPuestoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_perfil(
    id: UUID,
    body: PerfilPuestoUpdate,
    request: Request,
    service: PerfilPuestoService = Depends(_service),
) -> PerfilPuestoResponse:
    return service.update_perfil(id, body, _usuario_id(request))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_perfil(
    id: UUID,
    request: Request,
    service: PerfilPuestoService = Depends(_service),
) -> None:
    service.delete_perfil(id, _usuario_id(request))
