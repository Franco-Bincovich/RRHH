"""Router del catálogo de tipos de ausencia. Se registra en /api/ausencias ANTES del router
de ausencias (rutas estáticas /tipos vs /{id}).

🔒 DOS SECCIONES DISTINTAS, A PROPÓSITO:
  · GET y POST → AUSENCIAS. Crear un tipo al vuelo es parte de cargar una ausencia (el modal
    lo ofrece inline), y mandos_medios tiene que poder hacerlo.
  · PATCH → CONFIGURACION. Renombrar, dar de baja o cambiar si computa como ausentismo
    afecta a TODAS las ausencias ya cargadas y a la tasa de ausentismo de los reportes. Eso
    es cambiar una regla, no cargar un dato, y mandos_medios no lo toca.

NO hay DELETE, y no es un olvido: ver el encabezado de tipos_ausencia_service.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from schemas.ausencias import (
    TipoAusenciaCreate, TipoAusenciaListResponse, TipoAusenciaResponse,
)
from schemas.configuracion import TipoAusenciaUpdate
from services.tipos_ausencia_service import TiposAusenciaService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.AUSENCIAS


def _tipos_svc() -> TiposAusenciaService: return TiposAusenciaService()


@router.get("/tipos", response_model=TipoAusenciaListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_tipos(
    request: Request,
    incluir_inactivos: bool = Query(False, description="Los da de baja también; lo usa /configuracion para poder reactivarlos"),
    service: TiposAusenciaService = Depends(_tipos_svc),
) -> TipoAusenciaListResponse:
    return service.get_tipos(get_empresa_id(request), incluir_inactivos)


@router.post("/tipos", response_model=TipoAusenciaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_tipo(body: TipoAusenciaCreate, request: Request, service: TiposAusenciaService = Depends(_tipos_svc)) -> TipoAusenciaResponse:
    return service.create_tipo(body, get_empresa_id(request))


@router.patch("/tipos/{tipo_id}", response_model=TipoAusenciaResponse, dependencies=[Depends(require_permission(Seccion.CONFIGURACION, Accion.WRITE))])
async def update_tipo(tipo_id: UUID, body: TipoAusenciaUpdate, request: Request, service: TiposAusenciaService = Depends(_tipos_svc)) -> TipoAusenciaResponse:
    return service.update_tipo(tipo_id, body, get_empresa_id(request))
