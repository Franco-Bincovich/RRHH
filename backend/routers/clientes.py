"""
Router del catálogo de clientes — LECTURAS.

Las escrituras (POST/PUT/DELETE) viven en `routers/clientes_escrituras.py`, montado en el MISMO
prefijo: las rutas no cambian. Se parte DESDE EL PRINCIPIO y no cuando el archivo reviente,
porque el molde ya está: `areas.py` llegó a 72/80 y hubo que partirlo para que entrara el export.

POR QUÉ SALEN LAS ESCRITURAS Y NO LAS LECTURAS: el export que motiva el corte ES una lectura, así
que tiene que quedar de este lado para no volver a partir el archivo en la próxima tanda. Mismo
criterio, textual, que `areas_escrituras.py`.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.cliente import ClienteListResponse, ClienteResponse
from services.cliente_service import ClienteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.CLIENTES


def _service() -> ClienteService:
    return ClienteService()


@router.get("", response_model=ClienteListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_clientes(
    request: Request,
    incluir_inactivos: bool = Query(False, description="Incluir los dados de baja"),
    service: ClienteService = Depends(_service),
) -> ClienteListResponse:
    return service.get_clientes(get_empresa_id(request), incluir_inactivos)


# 🔴 ANTES de /{id}. Si fuera después, FastAPI resuelve por ORDEN DE DECLARACIÓN y "exportar"
# matchearía como el path param `id: UUID` → 422 de validación en vez del archivo. Es el mismo
# comentario, y el mismo bug evitado, que en areas.py.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_clientes(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    incluir_inactivos: bool = Query(False, description="Incluir los dados de baja"),
    service: ClienteService = Depends(_service),
) -> Response:
    d = service.exportar(get_empresa_id(request), formato, incluir_inactivos)
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=ClienteResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_cliente(
    id: UUID,
    request: Request,
    service: ClienteService = Depends(_service),
) -> ClienteResponse:
    return service.get_cliente(id, get_empresa_id(request))


def _usuario_id(request: Request) -> Optional[str]:
    """Id del usuario del request, para la trazabilidad de los eventos de auditoría.

    Vive acá y lo IMPORTA `clientes_escrituras.py` en vez de duplicarse: es una línea de
    criterio y dos copias que se separen darían dos formas distintas de resolver el mismo
    usuario. Mismo patrón que `_empresa_str` entre `areas.py` y `areas_escrituras.py`.
    """
    user = getattr(request.state, "user", None)
    return user.get("id") if isinstance(user, dict) else None
