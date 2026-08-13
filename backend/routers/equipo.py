"""Router del roster "mi equipo" (GET /api/equipo).

Gateado con la sección VACACIONES en modo READ (mismo patrón que routers/vacaciones.py):
mandos_medios la tiene, y así se expone el universo de ownership SIN abrir la sección
empleados. NO crea una sección de permisos nueva. Sin paginación: lista corta."""
from typing import List, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.equipo import EquipoMiembroResponse
from services.equipo_service import EquipoService
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()

SECCION = Seccion.VACACIONES


def _svc() -> EquipoService:
    return EquipoService()


@router.get("", response_model=List[EquipoMiembroResponse], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_equipo(request: Request, service: EquipoService = Depends(_svc)) -> List[EquipoMiembroResponse]:
    u = request.state.user
    return service.get_equipo(u.get("id"), u.get("rol"))


# Este router NO tiene ruta /{id}, así que el orden de /exportar no es load-bearing acá (en los
# demás módulos sí: "exportar" matchearía como un id). Queda igual pegado al listado por simetría.
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_equipo(request: Request, formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"), service: EquipoService = Depends(_svc)) -> Response:
    # 🔴 El universo sale del USUARIO del request, no de un Query: acá el filtro es el ownership.
    u = request.state.user
    d = service.exportar(u.get("id"), u.get("rol"), formato)
    return Response(content=d.content, media_type=d.media_type, headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})
