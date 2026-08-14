"""
Escrituras de recategorizaciones: registrar y editar.

Separado de `recategorizaciones.py` y montado en el MISMO prefijo, así que las rutas no cambian.

🔴 NO HAY DELETE, Y NO ES UN OLVIDO. Se puede EDITAR, no borrar. Se cargan a mano y alguien se
va a equivocar de fecha o de motivo, pero borrar rompe el histórico —y la cadena de
`*_anterior` que cuelga de él, porque cada fila calcula sus valores anteriores leyendo la
previa— y la auditoría ya registra quién editó qué. Un DELETE que "solo saca una fila" dejaría a
la siguiente afirmando un valor anterior que ya no existe en ningún lado.

⚠️ El PUT recalcula los `*_anterior` y reevalúa si corresponde pisar al colaborador. No es un
update plano: mover `fecha_efectiva` cambia cuál es la recategorización previa. Ver
`services/_recategorizaciones_write.editar`.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers._recategorizaciones_costos import puede_ver_costos, usuario_id
from schemas.recategorizacion import (
    RecategorizacionCreate, RecategorizacionResponse, RecategorizacionUpdate,
)
from services.recategorizacion_service import RecategorizacionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.RECATEGORIZACIONES


def _service() -> RecategorizacionService:
    return RecategorizacionService()


@router.post("", response_model=RecategorizacionResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_recategorizacion(
    request: Request,
    body: RecategorizacionCreate,
    service: RecategorizacionService = Depends(_service),
) -> RecategorizacionResponse:
    # `empresa_id` del header va SOLO como barrera de lectura sobre el empleado: la que se
    # PERSISTE sale del empleado (Vista vs Acción). Ver `_recategorizacion_anteriores.empresa_de`.
    return service.crear(body, get_empresa_id(request), usuario_id(request),
                         puede_ver_costos=puede_ver_costos(request))


@router.put("/{id}", response_model=RecategorizacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_recategorizacion(
    id: UUID,
    body: RecategorizacionUpdate,
    request: Request,
    service: RecategorizacionService = Depends(_service),
) -> RecategorizacionResponse:
    return service.editar(id, body, get_empresa_id(request), usuario_id(request),
                          puede_ver_costos=puede_ver_costos(request))
