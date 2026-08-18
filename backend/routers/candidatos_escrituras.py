"""
Escrituras de candidatos: baja, cambio de etapa y asignación de vacante.

Separado de `candidatos.py`, que estaba en 80/80 exacto y no admitía los dos `Query` de
paginación del listado. Se monta en el MISMO prefijo, así que las rutas no cambian.
Molde: `areas_escrituras.py`, `asignaciones_capacitacion_escrituras.py`.

POR QUÉ SALIERON LAS ESCRITURAS Y NO LAS LECTURAS: el listado y su export son los que CRECEN —
cada filtro nuevo les suma un `Query` en dos lugares. Las tres escrituras son estables.

⚠️ `GET /{id}/cv-url` se queda del lado de las LECTURAS aunque sea del mismo recurso: el criterio
del corte es el método, no la entidad. Devuelve una URL firmada y está gateado con READ.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.candidato import AsignarVacanteRequest, CandidatoResponse, ContratarRequest, EtapaUpdate
from schemas.empleado import EmpleadoResponse
from services.candidato_service import CandidatoService
from services.contratacion_service import ContratacionService
from services.vacante_service import VacanteService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.CANDIDATOS


def _svc() -> VacanteService:
    return VacanteService()


def _candidato_svc() -> CandidatoService:
    return CandidatoService()


def _contratacion_svc() -> ContratacionService:
    return ContratacionService()


@router.delete("/{id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def delete_candidato(
    id: UUID, request: Request, service: CandidatoService = Depends(_candidato_svc)
) -> None:
    service.delete_candidato(str(id), get_empresa_id(request), request.state.user.get("id", "system"))


@router.put("/{id}/etapa", response_model=CandidatoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def mover_candidato(
    id: UUID, body: EtapaUpdate, request: Request, service: VacanteService = Depends(_svc)
) -> CandidatoResponse:
    return service.mover_candidato(id, body.etapa, get_empresa_id(request), request.state.user.get("id", "system"))


@router.put("/{id}/vacante", response_model=CandidatoResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def asignar_vacante(
    id: UUID, body: AsignarVacanteRequest, request: Request,
    service: CandidatoService = Depends(_candidato_svc)
) -> CandidatoResponse:
    """Asigna una vacante a un candidato huérfano. La vacante tiene que ser de SU empresa."""
    return service.asignar_vacante(str(id), str(body.vacante_id), get_empresa_id(request),
                                   request.state.user.get("id"))


# Segundo tramo LITERAL (`/contratar`), igual que `/etapa` y `/vacante` de arriba: las tres son
# literales distintos, así que ninguna puede capturar a otra y el ORDEN DE REGISTRO NO ES
# LOAD-BEARING (verificado contra `app.routes`). Lo que sí lo volvería load-bearing es una ruta
# con PARÁMETRO en el segundo tramo (`/{id}/{algo}`): capturaría "contratar" como valor.
# Gate: CANDIDATOS + WRITE, como las otras tres escrituras del módulo. 🔴 NO lleva además un gate
# de EMPLEADOS aunque cree uno: el permiso es sobre la ACCIÓN que se pide —contratar a alguien de
# esta búsqueda— y exigir los dos dejaría el puente inalcanzable para quien administra selección.
@router.post("/{id}/contratar", response_model=EmpleadoResponse, status_code=201, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def contratar_candidato(
    id: UUID, body: ContratarRequest, request: Request,
    service: ContratacionService = Depends(_contratacion_svc)
) -> EmpleadoResponse:
    """Contrata a un candidato en oferta: crea su legajo en `preingreso`. Ver ContratacionService."""
    return service.contratar(str(id), body, get_empresa_id(request),
                             request.state.user.get("id", "system"))
