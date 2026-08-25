"""
Router de plantillas de mail y envío (migración 087).

🔒 Gate: `Seccion.CONFIGURACION` — el MISMO criterio que las reglas de negocio, y por el mismo
motivo: una plantilla de mail es una regla de cómo opera la empresa, no un dato operativo.
Resultado: crear y editar solo `admin_rrhh`; `gerencia_lectura` lee (quien puede ver todos los
reportes debería poder ver con qué texto se comunica la empresa); `mandos_medios` no entra.
No se creó una `Seccion` nueva: habría que sumarla al espejo de permisos del front y al sidebar
para algo que se toca dos veces al año.

Router propio y no endpoints colgados de `/api/configuracion` (55/80): aquel resuelve escalares
y escalas, y esto es CRUD de contenido + render + envío. Comparten la sección de permisos, no el
service.

⚠️ El preview lee datos de un empleado real, así que lleva ADEMÁS el gate de lectura de
EMPLEADOS: quien puede editar plantillas pero no ver empleados no debe sacar datos por esta vía.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.plantillas import (
    EnvioRequest, EnvioResponse, PlantillaResponse, PlantillasListResponse, PlantillaUpsert,
    PreviewRequest, PreviewResponse,
)
from services.mail_envio_service import MailEnvioService
from services.plantillas_service import PlantillasService
from utils.empresa import get_empresa_id, require_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()
SECCION = Seccion.CONFIGURACION

_READ = Depends(require_permission(SECCION, Accion.READ))
_WRITE = Depends(require_permission(SECCION, Accion.WRITE))
_VER_EMPLEADOS = Depends(require_permission(Seccion.EMPLEADOS, Accion.READ))


@router.get("", response_model=PlantillasListResponse, dependencies=[_READ])
async def listar(request: Request) -> PlantillasListResponse:
    """Plantillas visibles + el catálogo de contextos y sus variables."""
    return PlantillasService().listar(get_empresa_id(request))


@router.put("", response_model=PlantillaResponse, dependencies=[_WRITE])
async def guardar(body: PlantillaUpsert, request: Request) -> PlantillaResponse:
    """Crea o edita. Rechaza una variable que el contexto no declara (422)."""
    return PlantillasService().guardar(body, require_empresa_id(request), request.state.user.get("id"))


@router.delete("/{id}", status_code=204, dependencies=[_WRITE])
async def borrar(id: UUID, request: Request) -> None:
    PlantillasService().borrar(id, require_empresa_id(request), request.state.user.get("id"))


@router.post("/preview", response_model=PreviewResponse, dependencies=[_READ, _VER_EMPLEADOS])
async def preview(body: PreviewRequest, request: Request) -> PreviewResponse:
    """Renderiza sin enviar, con el MISMO renderer que el envío."""
    return PlantillasService().preview(body, get_empresa_id(request))


@router.post("/enviar", response_model=EnvioResponse, dependencies=[_WRITE])
@limiter.shared_limit("20/hour", scope="mail")  # franja propia: manda correo a nombre de la empresa
async def enviar(body: EnvioRequest, request: Request) -> EnvioResponse:
    """Envía la plantilla a los empleados. Con presupuesto de tiempo y reporte parcial;
    reintentar el mismo lote no duplica (idempotencia por el log).

    🔴 `require_empresa_id`, NO `get_empresa_id` — igual que `guardar` y `borrar`. Con `None` el
    repo saltea la plantilla PROPIA y resuelve la GLOBAL: existiendo una global con esa clave, el
    mail sale con un TEXTO DISTINTO del que muestra la pantalla, con 200 y sin ninguna señal. Y
    el evento de auditoría queda con `empresa_id` NULL, fuera del filtro por empresa de
    `/auditoria`. Enviar es una ACCIÓN y las acciones se hacen sobre UNA empresa: `None` no es
    "todas" acá, es "no se sabe con qué texto". La UI ya lo evita; el endpoint también tiene que.
    """
    empresa_id = require_empresa_id(request)   # en su propia línea: se rechaza ANTES de construir
    return MailEnvioService().enviar(body, empresa_id, request.state.user.get("id"))
