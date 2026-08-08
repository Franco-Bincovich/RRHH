"""
ABM de usuarios del sistema: alta con rol asignable y baja blanda. Solo admin_rrhh.

Separado de usuarios.py, que estaba en 77/80 y no admitía el endpoint de export (mide +10
líneas, medido sobre el mismo bloque en proyectos.py). Se monta en el MISMO prefijo, así que
las rutas no cambian. Molde: areas_escrituras.py, costos_escrituras.py y
onboarding_templates_escrituras.py.

QUÉ SE MOVIÓ Y QUÉ NO. Salieron las dos escrituras del ABM, que no llevan decorador de rate
limit. Se quedaron en usuarios.py el listado, el export y **cambiar-password**: los dos
últimos están decorados, y la clave del limiter es `routers.<módulo>.<función>` — mudarlos
cambiaría la clave y sus tests pasarían a mirar una clave inexistente, en verde. Por eso
"escrituras" acá no es literal: el criterio real es no mover nada decorado.

El orden de registro respecto de usuarios.py no es load-bearing: el POST "" no colisiona con
el GET "" del otro módulo (distinto método) y no hay ningún GET /{user_id} que pueda comerse
/exportar.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.usuario import CrearUsuarioRequest, CrearUsuarioResponse
from services.usuario_service import UsuarioService
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.USUARIOS


def _svc() -> UsuarioService:
    return UsuarioService()


@router.post("", response_model=CrearUsuarioResponse, status_code=201,
             dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def crear_usuario(
    request: Request,
    body: CrearUsuarioRequest,
    service: UsuarioService = Depends(_svc),
) -> CrearUsuarioResponse:
    """Crea un usuario con el rol indicado (validado en el schema) y contraseña temporal. Solo admin_rrhh."""
    creado_por = request.state.user.get("id", "system")
    return service.crear_usuario(body, creado_por)


@router.delete("/{user_id}", status_code=204,
               dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def eliminar_usuario(
    user_id: UUID,
    request: Request,
    service: UsuarioService = Depends(_svc),
) -> None:
    """Elimina un usuario del sistema. Solo admin_rrhh. No permite auto-eliminación.
    El id sale del path; el ejecutor, del token."""
    service.eliminar_usuario(str(user_id), request.state.user.get("id"))
