"""
Escrituras del módulo de áreas: alta, edición y baja lógica.

Separado de areas.py, que estaba en 72/80 y no admitía el endpoint de export (mide +10 líneas,
medido sobre el mismo bloque en proyectos.py). Se monta en el MISMO prefijo, así que las rutas
no cambian. Molde: costos_escrituras.py y onboarding_templates_escrituras.py.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS: el export que motiva el corte ES una lectura,
así que tiene que quedar del lado de las lecturas para no volver a partir el archivo en la
próxima tanda. Las tres escrituras son además un bloque coherente —las tres resuelven la empresa
igual, por `_empresa_str`— y ningún test las ancla por módulo.

`_empresa_str` se IMPORTA de routers.areas en vez de duplicarse: es una sola línea de criterio
("el repo de áreas filtra por str, no por UUID") y dos copias que se separen darían dos formas
distintas de resolver la misma empresa. Mismo patrón que `sujeto` en
onboarding_templates_escrituras.py.

El orden de registro respecto de areas.py no es load-bearing: no hay colisión de rutas posible
entre un POST/PUT/DELETE y los GET del otro módulo.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from routers.areas import _empresa_str
from schemas.area import AreaCreate, AreaResponse, AreaUpdate
from services.area_service import AreaService
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.AREAS


def _service() -> AreaService:
    return AreaService()


@router.post("", response_model=AreaResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def create_area(
    request: Request,
    body: AreaCreate,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    created_by = request.state.user.get("id", "system")
    return service.create_area(body, created_by)


@router.put("/{id}", response_model=AreaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def update_area(
    id: UUID,
    body: AreaUpdate,
    request: Request,
    service: AreaService = Depends(_service),
) -> AreaResponse:
    return service.update_area(id, body, _empresa_str(request))


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_area(
    id: UUID,
    request: Request,
    service: AreaService = Depends(_service),
) -> None:
    service.delete_area(id, _empresa_str(request))
