"""
Router de la vista "Horas por cliente" — ESCRITURAS. Hoy: la baja de una carga.

Separado de `horas_cliente.py` y montado en el MISMO prefijo, así que las rutas no cambian. El
porqué del corte está en el encabezado de ese archivo.

`_usuario_id` vive ACÁ y no allá porque su único caller es este DELETE: es el autor del evento de
auditoría de la baja. (En `clientes` quedó del lado de las lecturas por razones históricas; el
criterio bueno es que el helper viva donde se usa.)
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from services.horas_cliente_service import HorasClienteService
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.PROYECTOS


def _svc() -> HorasClienteService:
    return HorasClienteService()


def _usuario_id(request: Request) -> Optional[str]:
    """Autor del evento de auditoría de la baja."""
    return (getattr(request.state, "user", None) or {}).get("id")


@router.delete("/{hora_id}", status_code=204, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def eliminar(
    hora_id: UUID,
    request: Request,
    service: HorasClienteService = Depends(_svc),
) -> None:
    service.eliminar(hora_id, _usuario_id(request))
