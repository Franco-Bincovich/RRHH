"""
Router de offboarding — LECTURAS (listado de activos y export).
Rutas protegidas por AuthMiddleware.
empresa_id para lecturas: header X-Empresa-Id (filtro de vista, None = todas).

Las escrituras (alta del proceso, devolución de activos y entrevista de salida) viven en
routers/offboarding_escrituras.py, montado en el MISMO prefijo: las rutas no cambiaron. El
porqué del corte está en el docstring de ese archivo.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.offboarding import OffboardingResponse
from services.offboarding_service import OffboardingService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.OFFBOARDING


def _service() -> OffboardingService:
    return OffboardingService()


@router.get("", response_model=list[OffboardingResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_offboardings(
    request: Request,
    service: OffboardingService = Depends(_service),
) -> list[OffboardingResponse]:
    empresa_id = get_empresa_id(request)
    return service.get_offboardings_activos(empresa_id)


# ⚠️ ANTES de cualquier ruta con parámetro: si un GET /{instancia_id} se agregara arriba,
# "exportar" matchearía como un id y este endpoint devolvería 422 en vez de un archivo.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limiter.shared_limit("30/hour", scope="export")  # franja "export" — utils/rate_limit.py
async def exportar_offboardings(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: OffboardingService = Depends(_service)) -> Response:
    d = service.exportar(get_empresa_id(request), formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
