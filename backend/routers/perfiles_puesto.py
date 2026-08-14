"""
Router del catálogo de perfiles de puesto — LECTURAS.

Las escrituras viven en `perfiles_puesto_escrituras.py` y los labels del formulario en
`perfiles_puesto_catalogos.py`, los dos montados en el MISMO prefijo: las rutas no cambian. Se
parte DESDE EL PRINCIPIO, igual que en `clientes.py`. Sale la ESCRITURA y no la lectura porque
el export —lo que empuja el archivo— es una lectura y tiene que quedar de este lado.

🔴 EL LISTADO NACE PAGINADO, con `page_size` topeado en 100 (regla (d) de
`docs/DIAGNOSTICO-ESCALA.md`). El `le=100` es del ROUTER a propósito: un `page_size` sin techo
convierte el listado en un export encubierto que esquiva `verificar_limite_export`.

⚠️ SIN `X-Empresa-Id` EN NINGUNA RUTA: el catálogo es del GRUPO y el selector del sidebar no lo
acota (migración 113). No hay `empresa_id` que pasar ni barrera de empresa que aplicar.
"""
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from schemas.perfil_puesto import PerfilPuestoListResponse, PerfilPuestoResponse
from services.perfil_puesto_service import PerfilPuestoService
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limite_export

router = APIRouter()
SECCION = Seccion.PERFILES_PUESTO


def _service() -> PerfilPuestoService:
    return PerfilPuestoService()


@router.get("", response_model=PerfilPuestoListResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def list_perfiles(
    search: Optional[str] = Query(None, description="Búsqueda parcial por nombre"),
    incluir_inactivos: bool = Query(False, description="Incluir los dados de baja"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: PerfilPuestoService = Depends(_service),
) -> PerfilPuestoListResponse:
    return service.get_perfiles(page, page_size, search, incluir_inactivos)


# 🔴 `/exportar` va ANTES de `/{id}`: si fuera después, FastAPI resuelve por ORDEN DE DECLARACIÓN
# y "exportar" matchearía como el path param `id: UUID` → 422 en vez del archivo. Mismo bug
# evitado que en `clientes.py`. (`/campos` corre el mismo riesgo — ver `..._catalogos.py`.)
@router.get("/exportar", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
@limite_export  # 100/hora por usuario — utils/rate_limit.py
async def exportar_perfiles(
    request: Request,
    formato: Literal["pdf", "excel", "csv", "word"] = Query("excel"),
    search: Optional[str] = Query(None, description="Búsqueda parcial por nombre"),
    incluir_inactivos: bool = Query(False, description="Incluir los dados de baja"),
    service: PerfilPuestoService = Depends(_service),
) -> Response:
    """Export del listado — MISMOS Query que el listado, sin `page`. `request` lo exige slowapi."""
    d = service.exportar(formato, search, incluir_inactivos)
    return Response(content=d.content, media_type=d.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{d.filename}"'})


@router.get("/{id}", response_model=PerfilPuestoResponse, dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def get_perfil(
    id: UUID,
    service: PerfilPuestoService = Depends(_service),
) -> PerfilPuestoResponse:
    return service.get_perfil(id)


def _usuario_id(request: Request) -> Optional[str]:
    """Id del usuario del request, para `created_by` y para la trazabilidad de la auditoría.

    Vive acá y lo IMPORTA `perfiles_puesto_escrituras.py` en vez de duplicarse: es una línea de
    criterio y dos copias que se separen darían dos formas distintas de resolver el mismo
    usuario. Mismo patrón que entre `clientes.py` y `clientes_escrituras.py`.
    """
    user = getattr(request.state, "user", None)
    return user.get("id") if isinstance(user, dict) else None
