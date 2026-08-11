"""
Servicio del catálogo de clientes (migración 102).
Flujo: router → service → repository → DB

🔴 LA BAJA ES LÓGICA (`activo=False`), NO HAY DELETE FÍSICO. Tres razones, y la tercera es la
que lo decide:
  1. Es lo que hace el molde: `areas` borra con `activo=False` y `tipos_ausencia` directamente
     no tiene delete.
  2. `horas_proyecto.cliente_id` es una FK **sin ON DELETE** (migración 103). Un DELETE físico
     sobre un cliente con horas cargadas no da un 409: revienta contra la constraint y sale como
     500. Ese bug existe HOY en `proyectos_service.delete`, que chequea `has_horas` pero NO las
     asignaciones, así que borrar un proyecto con equipo y sin horas pasa las dos validaciones y
     muere en la base. No se replica.
  3. Las horas ya cargadas tienen que seguir pudiendo decir a qué cliente se imputaron. Un
     borrado físico o rompe, o deja el historial apuntando a la nada.
La baja saca al cliente de los selects y no toca una sola hora. Es reversible desde la pantalla.

🔴 AUDITA LAS TRES ESCRITURAS, Y ES TODO O NADA. `tests/test_auditoria_coherente.py` barre por
AST y exige que un módulo que audita ALGUNA operación las audite TODAS: auditar el alta y
olvidar la edición es la clase de bug que ya se cerró a mano tres veces en este repo. Los tres
eventos van con `empresa_id` NULL: un cliente es global y no tiene empresa que declarar — ver
`_audit_payloads_clientes`.
"""
from typing import Optional
from uuid import UUID

from repositories.cliente_repo import ClienteRepo
from schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, ClienteUpdate
from services._audit_payloads_clientes import (
    payload_alta_cliente, payload_baja_cliente, payload_update_cliente,
)
from services._clientes_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger

_NO_ENCONTRADO = ("Cliente no encontrado", "CLIENTE_NOT_FOUND", 404)


class ClienteService:
    def __init__(self, repo: Optional[ClienteRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or ClienteRepo()
        self._audit = audit or AuditService()

    def get_clientes(self, incluir_inactivos: bool = False) -> ClienteListResponse:
        """El catálogo entero, por nombre. Es GLOBAL: el sidebar de empresa no lo acota."""
        items = self._repo.find_all(incluir_inactivos)
        return ClienteListResponse(items=items, total=len(items))

    def exportar(self, formato: str = "excel",
                 incluir_inactivos: bool = False) -> Descarga:
        """Exporta el catálogo con los MISMOS filtros que el listado. Va por el mismo
        `find_all`, así que el archivo no puede traer filas que la pantalla no muestre."""
        items = self._repo.find_all(incluir_inactivos)
        verificar_limite_export(len(items))
        datos = {"Clientes": construir_filas_export(items)}
        return build_export(nombre="Clientes", datos=datos, filename_base="clientes",
                            formato=formato)

    def get_cliente(self, id: UUID) -> ClienteResponse:
        """Detalle. El catálogo es global: no hay clientes ajenos que ocultar."""
        cliente = self._repo.find_by_id(str(id))
        if not cliente:
            raise AppError(*_NO_ENCONTRADO)
        return cliente

    def create_cliente(self, data: ClienteCreate, usuario_id: Optional[str]) -> ClienteResponse:
        """Alta. Sin empresa: el cliente es global (migración 108).

        Raises:
            AppError: NOMBRE_REQUERIDO (422), CLIENTE_DUPLICADO (409).
        """
        if not data.nombre.strip():
            raise AppError("El nombre es requerido", "NOMBRE_REQUERIDO", 422)
        if self._repo.existe_nombre(data.nombre):
            raise AppError("Ya existe un cliente con ese nombre",
                           "CLIENTE_DUPLICADO", 409)
        cliente = self._repo.save(data)
        self._audit.registrar(**payload_alta_cliente(cliente, usuario_id))
        logger.info("Cliente creado", extra={"cliente_id": str(cliente.id)})
        return cliente

    def update_cliente(self, id: UUID, data: ClienteUpdate,
                       usuario_id: Optional[str] = None) -> ClienteResponse:
        """Edición parcial. Lee el PRIOR antes de escribir: sin él no hay diff que auditar."""
        prior = self._repo.find_by_id(str(id))
        if not prior:
            raise AppError(*_NO_ENCONTRADO)
        if data.nombre is not None:
            if not data.nombre.strip():
                raise AppError("El nombre es requerido", "NOMBRE_REQUERIDO", 422)
            if self._repo.existe_nombre(data.nombre, excepto_id=str(id)):
                raise AppError("Ya existe un cliente con ese nombre",
                               "CLIENTE_DUPLICADO", 409)
        patch = {k: (v.strip() if k == "nombre" else v)
                 for k, v in data.model_dump(exclude_none=True).items()}
        nuevo = self._repo.update(str(id), patch)
        if not nuevo:
            raise AppError(*_NO_ENCONTRADO)
        self._audit.registrar(**payload_update_cliente(prior, nuevo, usuario_id))
        logger.info("Cliente actualizado", extra={"cliente_id": str(id)})
        return nuevo

    def delete_cliente(self, id: UUID, usuario_id: Optional[str] = None) -> None:
        """Baja LÓGICA. Ver el encabezado del módulo: no hay borrado físico."""
        prior = self._repo.find_by_id(str(id))
        if not prior:
            raise AppError(*_NO_ENCONTRADO)
        if not self._repo.update(str(id), {"activo": False}):
            raise AppError(*_NO_ENCONTRADO)
        self._audit.registrar(**payload_baja_cliente(prior, usuario_id))
        logger.info("Cliente dado de baja", extra={"cliente_id": str(id)})
