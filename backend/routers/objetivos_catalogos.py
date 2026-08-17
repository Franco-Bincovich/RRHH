"""
Router de catálogos de objetivos — el vocabulario cerrado del formulario y de los filtros.

Separado de `objetivos.py` por el mismo corte que ya existe entre `empleados.py` y
`empleados_catalogos.py`, y entre `perfiles_puesto.py` y `perfiles_puesto_catalogos.py`. Comparte
el prefijo `/api/objetivos` y **se registra ANTES** que el router de lecturas.

⚠️ HOY EL ORDEN NO ES LOAD-BEARING ACÁ, Y SE RESPETA IGUAL. En `perfiles-puesto` el orden es
obligatorio porque el CRUD tiene un `GET /{id}` que se comería `/campos` con `id="campos"` → 422.
En objetivos ese GET **no existe**: el router de lecturas sólo monta `""` y `/exportar`, y los
`/{id}` del módulo son PUT y DELETE, que no colisionan con un GET.
🔴 Pero `ObjetivoService.get_by_id` ya está escrito y esperando un endpoint, así que el día que
alguien monte `GET /api/objetivos/{id}` la colisión aparece — y aparece EN SILENCIO, con un 422
`PEDIDO_INVALIDO` sobre una ruta que funcionaba. Es exactamente lo que le pasó a
`asignaciones_capacitacion`, que estuvo apagado hasta el 13/8/2026 sin que nadie lo notara porque
la tabla estaba vacía. Registrarlo en el orden correcto ahora cuesta cero.
"""
from typing import List

from fastapi import APIRouter, Depends, Request

from schemas.objetivo import TIPOS_OPCIONES
from services.objetivo_catalogos_service import ObjetivoCatalogosService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.OBJETIVOS


def _svc() -> ObjetivoCatalogosService:
    return ObjetivoCatalogosService()


@router.get("/campos", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def campos_objetivo() -> dict:
    """El vocabulario cerrado de `tipo`, con su etiqueta legible.

    🔴 EXISTE PARA QUE EL FRONT NO ESCRIBA `anual | operativo` POR SU CUENTA. Esos dos literales
    son a la vez el CHECK de la migración 119, el `Literal` de `ObjetivoCreate`/`ObjetivoUpdate` y
    el del filtro `ObjetivosFiltros`. Una copia en el front que derive ofrecería en un selector un
    valor que el backend rechaza con 422 — y con dos opciones la copia se ve inofensiva, que es
    justamente por qué se hace.

    Va gateado por `Seccion.OBJETIVOS + READ` y no abierto: quien no puede ver el módulo tampoco
    necesita saber cómo se llaman sus vistas.

    Returns:
        `tipos`: la lista de opciones, cada una con `value` (el literal de la base) y `label`.
    """
    return {"tipos": TIPOS_OPCIONES}


@router.get("/areas-conocidas", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def areas_conocidas(
    request: Request,
    service: ObjetivoCatalogosService = Depends(_svc),
) -> List[str]:
    """Las áreas ya usadas en objetivos, para el desplegable del filtro por área.

    🔴 ENDPOINT APARTE DE `/campos` Y NO UN CAMPO MÁS DE SU RESPUESTA, aunque los dos alimenten
    selectores del mismo formulario. `/campos` devuelve un vocabulario CERRADO que no depende de
    los datos —los dos literales del CHECK— y se puede cachear para siempre; esto son DATOS, que
    cambian con cada objetivo que se carga y que además dependen de la empresa activa. Juntarlos
    haría que el vocabulario fijo se recargue con cada alta, o —peor— que el pool de áreas quede
    cacheado y deje de mostrar lo recién cargado.

    Devuelve una lista plana de strings, no objetos `{value,label}`: acá el valor **es** la
    etiqueta. Es texto que escribió RRHH; inventarle un `label` distinto sería traducirlo.

    Respeta el selector de empresa del sidebar (`X-Empresa-Id`): es una VISTA, y el desplegable
    tiene que ofrecer lo que esta vista puede encontrar. El porqué, en `ObjetivoAreasRepo`.
    """
    return service.get_areas_conocidas(get_empresa_id(request))
