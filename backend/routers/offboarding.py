"""
Router de offboarding — LECTURAS (listado de activos y export).
Rutas protegidas por AuthMiddleware.
empresa_id para lecturas: header X-Empresa-Id (filtro de vista, None = todas).

🔑 CRITERIO DE CORTE — DÓNDE VA UN ENDPOINT NUEVO DEL MÓDULO, sin tener que preguntar:
  · LECTURAS (este archivo): listado y export.
  · CICLO (`offboarding_escrituras.py`): endpoints que cambian EN QUÉ ESTADO ESTÁ EL PROCESO.
  · TRÁMITE (`offboarding_tramite.py`): endpoints que registran PROGRESO DENTRO DE UNA INSTANCIA
    YA CREADA. No cambian el estado del proceso ni tocan nada fuera de la instancia.

Los tres se montan en el MISMO prefijo, así que las rutas no cambiaron en ninguno de los dos
cortes. El porqué de cada uno está en el docstring del archivo correspondiente.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.offboarding import OffboardingResponse
from services.offboarding_service import OffboardingService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

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
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_offboardings(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: OffboardingService = Depends(_service)) -> Response:
    d = service.exportar(get_empresa_id(request), formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
