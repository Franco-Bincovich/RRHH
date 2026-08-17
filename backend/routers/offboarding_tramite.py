"""
Router de offboarding — TRÁMITE: devolución de activos corporativos y registro de la entrevista
de salida.

🔑 CRITERIO DE CORTE — DÓNDE VA UN ENDPOINT NUEVO DEL MÓDULO, sin tener que preguntar:
  · TRÁMITE (este archivo): endpoints que registran PROGRESO DENTRO DE UNA INSTANCIA YA CREADA.
    No cambian el estado del proceso ni tocan nada fuera de la instancia.
  · CICLO (`offboarding_escrituras.py`): endpoints que cambian EN QUÉ ESTADO ESTÁ EL PROCESO.
  · LECTURAS (`offboarding.py`): listado y export.

Extraído de `offboarding_escrituras.py`, que había llegado a 79/80. El corte no se eligió por
tamaño —partir un archivo a la mitad por el número de líneas deja dos mitades que nadie sabe
distinguir después—: se eligió por la frontera que ya existía adentro del módulo. Es el mismo
criterio con el que `_offboarding_iniciar.py` se separó del service ("es el único que toca DOS
agregados"), aplicado ahora a la capa de router.

Se monta en el MISMO prefijo que los otros dos, así que las rutas NO cambian: mismos paths,
mismos métodos, mismos tags. Desde afuera la API queda igual. Molde: el corte
lecturas/escrituras que el módulo ya tenía, y `areas_escrituras.py` / `usuarios_escrituras.py`.

⚠️ Ninguno de estos dos endpoints lleva decorador de rate limit, así que moverlos es seguro: la
clave del limiter es `routers.<módulo>.<función>`, y mover un endpoint decorado le cambiaría la
clave y con ella su contador. La regla sigue vigente para el próximo que se mueva.

El orden de registro de este router respecto de los otros dos NO es load-bearing: sus dos rutas
tienen un segundo tramo LITERAL (`/activos/...`, `/entrevista`) que no puede colisionar con
ninguna otra ruta del módulo.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.offboarding import ActivoUpdate, EntrevistaUpdate
from services.offboarding_service import OffboardingService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.OFFBOARDING


def _service() -> OffboardingService:
    return OffboardingService()


@router.put(
    "/{instancia_id}/activos/{activo_id}",
    response_model=dict,
    dependencies=[Depends(require_permission(SECCION, Accion.WRITE))],
)
async def actualizar_activo(
    instancia_id: UUID,
    activo_id: UUID,
    body: ActivoUpdate,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> dict:
    service.marcar_activo_devuelto(
        instancia_id, activo_id, body.devuelto,
        request.state.user.get("id", "system"), get_empresa_id(request),
    )
    return {"ok": True}


@router.put(
    "/{instancia_id}/entrevista",
    response_model=dict,
    dependencies=[Depends(require_permission(SECCION, Accion.WRITE))],
)
async def registrar_entrevista(
    instancia_id: UUID,
    body: EntrevistaUpdate,
    request: Request,
    service: OffboardingService = Depends(_service),
) -> dict:
    service.registrar_entrevista(
        instancia_id, body.entrevista_salida, body.notas_entrevista,
        request.state.user.get("id", "system"), get_empresa_id(request),
    )
    return {"ok": True}
