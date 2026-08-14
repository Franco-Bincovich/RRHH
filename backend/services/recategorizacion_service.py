"""
Servicio de recategorizaciones (migraciones 113/116/117).
Flujo: router → service → repository → DB

Registro PURO: no hay flujo de aprobación. Se puede editar, no borrar.

🔴 LAS DOS REGLAS QUE GOBIERNAN ESTE MÓDULO VIVEN EN `_recategorizacion_anteriores.py` Y HAY QUE
LEERLAS ANTES DE TOCAR NADA: los `*_anterior` salen de la última recategorización PREVIA a la
fecha efectiva (no del empleado actual), y el UPDATE del empleado corre SOLO si la fila es la
más reciente de esa persona. Las dos existen porque **la fecha efectiva es editable hacia
atrás**, y sin ellas el estado final del colaborador dependería del orden en que se cargaron las
filas en vez de las fechas. El write path que las aplica está en `_recategorizaciones_write.py`.

🔴 EL EFECTO LATERAL SOBRE `empleados` VA POR `EmpleadoService.update_empleado`, no por un write
path propio, así que **cada recategorización que pisa al colaborador emite DOS eventos de
auditoría**: el propio (registro de NEGOCIO: qué cambió, desde cuándo, por qué) y el
`update_empleado` (registro TÉCNICO: qué columnas se tocaron). Es a propósito, y por eso el
evento propio lleva `entidad="recategorizacion"` — si compartieran entidad se leerían como ruido
duplicado sobre el mismo empleado.

🔴 `impacto_salarial` SE OMITE SIN `COSTOS + READ`. No se gatea la sección entera —el rol y la
seniority no son sensibles, y el historial le sirve a cualquiera que vea el legajo—: se anula el
campo. `puede_ver_costos` lo resuelve el ROUTER y viaja como parámetro; el service no lee el
request. Mismo criterio por el que el sueldo no está entre las variables de mail.
⚠️ Se aplica en las CUATRO superficies de lectura (planilla, ficha, detalle y export). Una sola
que se olvide devuelve el monto a un rol que no debería verlo, y no hay test que lo note salvo
que se lo escriba.
"""
from datetime import date
from math import ceil
from typing import List, Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.recategorizacion_repo import RecategorizacionRepo
from schemas.recategorizacion import (
    RecategorizacionCreate, RecategorizacionListResponse, RecategorizacionResponse,
    RecategorizacionUpdate,
)
from services._empleado_scope import ensure_empleado_de_empresa
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._recategorizaciones_export import construir_filas_export
from services._recategorizaciones_write import NO_ENCONTRADO, crear, editar
from services.audit_service import AuditService
from services.empleado_service import EmpleadoService
from services.export import Descarga, build_export
from utils.errors import AppError


def _sin_impacto(r: RecategorizacionResponse) -> RecategorizacionResponse:
    """Copia con `impacto_salarial` en None. El campo NO se quita: cambiar la forma de la
    respuesta según el rol rompe el contrato, y un campo ausente confirmaría que hay monto."""
    return r.model_copy(update={"impacto_salarial": None})


class RecategorizacionService:
    def __init__(self, repo: Optional[RecategorizacionRepo] = None,
                 empleados: Optional[EmpleadoRepo] = None,
                 empleado_service: Optional[EmpleadoService] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or RecategorizacionRepo()
        self._empleados = empleados or EmpleadoRepo()
        self._empleado_service = empleado_service or EmpleadoService()
        self._audit = audit or AuditService()

    def listar(self, page: int = 1, page_size: int = 20, empresa_id: Optional[UUID] = None,
               empleado_id: Optional[UUID] = None, fecha_desde: Optional[date] = None,
               fecha_hasta: Optional[date] = None, *,
               puede_ver_costos: bool = False) -> RecategorizacionListResponse:
        """La planilla, paginada por fecha efectiva descendente."""
        items, total = self._repo.find_all(page, page_size, empresa_id, empleado_id,
                                           fecha_desde, fecha_hasta)
        return RecategorizacionListResponse(
            items=self._proyectar(items, puede_ver_costos), total=total, page=page,
            page_size=page_size, total_pages=max(1, ceil(total / page_size)) if page_size else 1)

    def historial_empleado(self, empleado_id: UUID, empresa_id: Optional[UUID] = None, *,
                           puede_ver_costos: bool = False) -> List[RecategorizacionResponse]:
        """Historial de una persona para su ficha. Lista plana, del más reciente al más viejo.

        La barrera de EMPRESA se aplica acá sobre el EMPLEADO objetivo: el `empresa_id` del repo
        sale del header y no valida a qué empleado apuntás. Mismo criterio, y mismo 404
        indistinguible de "no existe", que `costo_service.get_historial_salarial`.
        """
        ensure_empleado_de_empresa(self._empleados, empleado_id, empresa_id)
        return self._proyectar(self._repo.find_by_empleado(str(empleado_id), empresa_id),
                               puede_ver_costos)

    def obtener(self, id: UUID, empresa_id: Optional[UUID] = None, *,
                puede_ver_costos: bool = False) -> RecategorizacionResponse:
        """Detalle. 404 idéntico para "no existe" y "es de otra empresa"."""
        fila = self._repo.find_by_id(str(id), empresa_id)
        if not fila:
            raise AppError(*NO_ENCONTRADO)
        return self._proyectar([fila], puede_ver_costos)[0]

    def crear(self, data: RecategorizacionCreate, empresa_id: Optional[UUID],
              usuario_id: Optional[str], *,
              puede_ver_costos: bool = False) -> RecategorizacionResponse:
        """Registra una recategorización. Delegado a `_recategorizaciones_write.crear`."""
        fila = crear(self._repo, self._empleados, self._empleado_service, self._audit,
                     data, empresa_id, usuario_id)
        return self._proyectar([fila], puede_ver_costos)[0]

    def editar(self, id: UUID, data: RecategorizacionUpdate, empresa_id: Optional[UUID],
               usuario_id: Optional[str], *,
               puede_ver_costos: bool = False) -> RecategorizacionResponse:
        """Edición parcial. Delegado a `_recategorizaciones_write.editar`."""
        fila = editar(self._repo, self._empleados, self._empleado_service, self._audit,
                      id, data, empresa_id, usuario_id)
        return self._proyectar([fila], puede_ver_costos)[0]

    def exportar(self, empresa_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None,
                 fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
                 formato: str = "excel", *, puede_ver_costos: bool = False) -> Descarga:
        """Exporta con los MISMOS filtros que el listado, sin paginar.

        Pide una sola página del tamaño del tope, así el control actúa antes de cargar nada más
        grande: el total viene por `count="exact"` y respeta los filtros.
        """
        items, total = self._repo.find_all(1, LIMITE_FILAS_EXPORT, empresa_id, empleado_id,
                                           fecha_desde, fecha_hasta)
        verificar_limite_export(total)
        datos = {"Recategorizaciones": construir_filas_export(items, puede_ver_costos)}
        return build_export(nombre="Recategorizaciones", datos=datos,
                            filename_base="recategorizaciones", formato=formato)

    def _proyectar(self, filas, puede_ver_costos: bool) -> List[RecategorizacionResponse]:
        """Anula `impacto_salarial` si el rol no puede ver costos. Único punto donde se decide."""
        return list(filas) if puede_ver_costos else [_sin_impacto(f) for f in filas]
