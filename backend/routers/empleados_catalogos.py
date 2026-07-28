"""Router de catálogos de empleados — pools de autocompletado (roles y campos del legajo).

Separado de empleados.py para no superar su límite de líneas (80). Comparte el prefijo
/api/empleados, pero se registra ANTES que el router de empleados en main.py para que las
rutas estáticas (/roles-conocidos, /valores-conocidos) matcheen antes que /{id}."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from schemas._provincias import PROVINCIAS
from schemas.empleado import EmpleadoSeleccionable
from services.empleado_catalogos_service import EmpleadoCatalogosService
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.EMPLEADOS


def _service() -> EmpleadoCatalogosService:
    return EmpleadoCatalogosService()


@router.get("/roles-conocidos", response_model=list[str], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def roles_conocidos(service: EmpleadoCatalogosService = Depends(_service)) -> list[str]:
    """Pool compartido de roles ya usados (todas las empresas), para autocompletar."""
    return service.get_roles_conocidos()


@router.get("/valores-conocidos", response_model=list[str], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def valores_conocidos(
    campo: str = Query(..., description="Campo del legajo a autocompletar (whitelist en el service)"),
    service: EmpleadoCatalogosService = Depends(_service),
) -> list[str]:
    """Pool compartido de valores ya usados de un campo autocompletable del legajo."""
    return service.get_valores_conocidos(campo)


@router.get("/seleccionables", response_model=list[EmpleadoSeleccionable], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def seleccionables(
    empresa_id: UUID = Query(..., description="Empresa de la que listar empleados activos"),
    service: EmpleadoCatalogosService = Depends(_service),
) -> list[EmpleadoSeleccionable]:
    """Lista liviana (id, nombre, apellido) de empleados activos de una empresa, para selects."""
    return service.get_seleccionables(empresa_id)


@router.get("/provincias", response_model=list[str], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def provincias() -> list[str]:
    """Las 24 jurisdicciones argentinas, para el select de domicilio del modal.

    Existe para que la lista tenga UNA fuente de verdad. El front podría tener su propia copia
    —son 24 strings que no cambian— pero dos listas escritas a mano se separan: es el problema
    ya documentado de permisos.ts como espejo manual de permisos.py. Sirviéndola desde acá, el
    backend valida y el front muestra exactamente lo mismo, por construcción.
    """
    return list(PROVINCIAS)
