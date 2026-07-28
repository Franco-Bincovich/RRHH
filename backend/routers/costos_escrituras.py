"""
Escrituras del módulo de costos: carga de nómina y presupuesto de área.

Separado de costos.py, que estaba en 80/80 y no admitía el endpoint nuevo del historial
salarial. Molde: vacaciones_empleado.py y evaluaciones_resultados_export.py. Se monta en el
mismo prefijo, así que las rutas no cambian.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS, que era el corte más obvio: el export
(`exportar_nomina`) es una lectura, y el barrido de rate limiting lo referencia POR MÓDULO
(tests/test_rate_limit.py). Moverlo obligaba a editar ese test en la misma tanda en que se
agrega una feature. Las escrituras son un bloque igual de coherente —las dos heredan su
empresa de la entidad, ninguna la toma del header— y ningún test las ancla.

El orden de registro respecto de costos.py no es load-bearing: estos son POST y aquellos GET,
así que no hay colisión de rutas posible.
"""
from fastapi import APIRouter, Depends, Request

from schemas.costo import NominaCreate, NominaResponse, PresupuestoCreate, PresupuestoResponse
from services.costo_service import CostoService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.COSTOS


def _service() -> CostoService:
    return CostoService()


@router.post("/nomina", response_model=NominaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def post_nomina(
    request: Request,
    body: NominaCreate,
    service: CostoService = Depends(_service),
) -> NominaResponse:
    u = request.state.user
    return service.cargar_nomina(body, get_empresa_id(request), u.get("id", "system"), u.get("rol"))


@router.post("/presupuesto", response_model=PresupuestoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def post_presupuesto(
    request: Request,
    body: PresupuestoCreate,
    service: CostoService = Depends(_service),
) -> PresupuestoResponse:
    return service.set_presupuesto_area(body, get_empresa_id(request), request.state.user.get("id", "system"))
