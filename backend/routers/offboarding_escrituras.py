"""
Router de offboarding — CICLO DEL PROCESO: alta de la instancia.

🔑 CRITERIO DE CORTE — DÓNDE VA UN ENDPOINT NUEVO DEL MÓDULO, sin tener que preguntar:
  · CICLO (este archivo): endpoints que cambian EN QUÉ ESTADO ESTÁ EL PROCESO.
  · TRÁMITE (`offboarding_tramite.py`): endpoints que registran PROGRESO DENTRO DE UNA INSTANCIA
    YA CREADA. No cambian el estado del proceso ni tocan nada fuera de la instancia.
  · LECTURAS (`offboarding.py`): listado y export.

Este archivo nació separado de `offboarding.py`, que estaba en 78/80 y no admitía el endpoint de
export. Después se le fueron los dos PUT del trámite (devolución de activos y entrevista de
salida) al llegar a 79/80. Los tres se montan en el MISMO prefijo, así que en ninguno de los dos
cortes cambiaron las rutas. Molde: areas_escrituras.py, usuarios_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS DE `offboarding.py`: el export que motivó ese corte ES una
lectura, así que quedó del lado correcto para no volver a partir el archivo en la próxima tanda.

⚠️ Ningún endpoint de este archivo lleva decorador de rate limit, así que la regla de "no mover
nada decorado" (la clave del limiter es `routers.<módulo>.<función>`, y moverlo le cambiaría la
clave y con ella su contador) no ata a ninguno. Sigue vigente para el próximo que se agregue.

empresa_id para CREATE: heredada del EMPLEADO, no del header — el service la resuelve
internamente (principio Vista vs Acción). El orden de registro no es load-bearing.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.offboarding import EfectivizarBaja, OffboardingCreate, OffboardingResponse
from services.offboarding_service import OffboardingService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.OFFBOARDING


def _service() -> OffboardingService:
    return OffboardingService()


@router.post("", response_model=OffboardingResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def crear_offboarding(
    body: OffboardingCreate,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> OffboardingResponse:
    return service.iniciar_offboarding(body, get_empresa_id(request), request.state.user.get("id", "system"))


# Segundo tramo LITERAL (`/efectivizar`), así que no compite con ninguna otra ruta del módulo y su
# orden de registro no es load-bearing. Es CICLO: cambia en qué estado está el proceso.
@router.post(
    "/{instancia_id}/efectivizar",
    response_model=dict,
    dependencies=[Depends(require_permission(SECCION, Accion.WRITE))],
)
async def efectivizar_offboarding(
    instancia_id: UUID,
    body: EfectivizarBaja,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> dict:
    service.efectivizar(
        instancia_id, body.fecha_egreso,
        get_empresa_id(request), request.state.user.get("id", "system"),
    )
    return {"ok": True}
