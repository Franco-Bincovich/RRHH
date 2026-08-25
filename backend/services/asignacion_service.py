"""
Servicio de asignaciones de capacitaciones (empleado × curso).
Flujo: router → service → repository → DB
empresa_id heredado del empleado; empleado y curso deben ser de la misma empresa.
Al pasar a 'completado', fecha_completado se auto-setea. Certs en bucket 'documentos' privado.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from repositories.asignacion_repo import AsignacionRepo
from repositories.capacitacion_repo import CapacitacionRepo
from schemas.capacitacion import AsignacionCreate, AsignacionListResponse, AsignacionResponse, AsignacionUpdate
from services._asignacion_certificado import subir as _subir_certificado
from services._asignacion_certificado import url_firmada as _url_certificado
from services._audit_payloads_capacitaciones import (
    payload_alta_asignacion_capacitacion, payload_baja_asignacion_capacitacion,
    payload_update_asignacion_capacitacion,
)
from services._capacitaciones_export import construir_filas_export
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._paginacion import cantidad_paginas
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger

_VALID_ESTADOS = ("pendiente", "en_curso", "completado")


class AsignacionService:
    def __init__(self, repo: Optional[AsignacionRepo] = None,
                 cap_repo: Optional[CapacitacionRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._audit = audit or AuditService()
        self._repo = repo or AsignacionRepo()
        self._cap_repo = cap_repo or CapacitacionRepo()

    def get_all(self, empresa_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None,
                capacitacion_id: Optional[UUID] = None, estado: Optional[str] = None,
                area_id: Optional[UUID] = None, page: int = 1, page_size: int = 20) -> AsignacionListResponse:
        """Página de asignaciones filtradas (empresa None = todas). `total` = count del filtro."""
        items, total = self._repo.find_all(empresa_id, empleado_id, capacitacion_id, estado,
                                           area_id, page, page_size)
        return AsignacionListResponse(items=items, total=total, page=page, page_size=page_size,
                                      total_pages=cantidad_paginas(total, page_size))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", empleado_id: Optional[UUID] = None, capacitacion_id: Optional[UUID] = None, estado: Optional[str] = None, area_id: Optional[UUID] = None) -> Descarga:
        """Exporta las asignaciones de capacitación (columnas legibles, sin UUIDs) respetando los filtros (empleado/capacitación/estado/área)."""
        pagina = self.get_all(empresa_id, empleado_id, capacitacion_id, estado, area_id,
                              1, LIMITE_FILAS_EXPORT)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        filas = construir_filas_export(pagina.items)
        return build_export(nombre="Formación", datos={"Asignaciones": filas}, filename_base="formacion", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> AsignacionResponse:
        """Retorna asignación por ID. Raises ASIGNACION_NOT_FOUND (404)."""
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        return row

    def create(self, data: AsignacionCreate, created_by: str) -> AsignacionResponse:
        """
        Asigna un curso a un empleado. Hereda empresa_id del empleado.

        🔴 LA CAPACITACIÓN SE BUSCA ACOTADA A LA EMPRESA DEL EMPLEADO, y por eso ya no existe un
        EMPRESA_MISMATCH (422). Antes el lookup no acotaba y el desajuste salía con status propio:
        el id de un curso de otra empresa devolvía 422 y uno inventado 404, y esa diferencia
        confirmaba que el curso existe. Mismo cierre que services/_onboarding_iniciar.py.

        Raises: EMPLEADO_NOT_FOUND (404), CAPACITACION_NOT_FOUND (404), YA_ASIGNADO (409).
        """
        empresa_id = self._repo.find_empresa_for_empleado(str(data.empleado_id))
        if not empresa_id:
            raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)
        if not self._cap_repo.find_empresa_for(str(data.capacitacion_id), empresa_id):
            raise AppError("Formación no encontrada", "CAPACITACION_NOT_FOUND", 404)
        try:
            row = self._repo.save(str(data.capacitacion_id), str(data.empleado_id), empresa_id, data.fecha_asignacion, data.fecha_limite,
                                  proyecto=data.proyecto, anio=data.anio, mes=data.mes, nombre_libre=data.nombre_libre)
        except AppError:
            raise
        except Exception:
            raise AppError("El colaborador ya tiene esta formación asignada", "YA_ASIGNADO", 409)
        self._audit.registrar(**payload_alta_asignacion_capacitacion(row, created_by))
        logger.info("Capacitación asignada", extra={"asignacion_id": row.id, "created_by": created_by})
        return row

    def update_estado(self, id: UUID, data: AsignacionUpdate, empresa_id: Optional[UUID] = None,
                      usuario_id: Optional[str] = None) -> AsignacionResponse:
        """
        Actualiza estado y/o fechas. Al pasar a 'completado', auto-setea fecha_completado=hoy si no viene.
        Raises: ASIGNACION_NOT_FOUND (404), ESTADO_INVALIDO (422).
        """
        prior = self._repo.find_by_id(str(id), empresa_id)   # el "antes" del diff
        if not prior:
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        payload: dict = {}
        if data.estado is not None:
            if data.estado not in _VALID_ESTADOS:
                raise AppError(f"Estado inválido. Valores: {', '.join(_VALID_ESTADOS)}", "ESTADO_INVALIDO", 422)
            payload["estado"] = data.estado
            if data.estado == "completado" and not data.fecha_completado:
                payload["fecha_completado"] = str(date.today())
        if data.fecha_limite is not None:
            payload["fecha_limite"] = str(data.fecha_limite)
        if data.fecha_completado is not None:
            payload["fecha_completado"] = str(data.fecha_completado)
        # Los cuatro de la mig 116, con la misma semántica `is not None` que las fechas: un campo
        # omitido no se toca; vaciar uno es mandar "" (str vacío), no None.
        for campo in ("proyecto", "anio", "mes", "nombre_libre"):
            if getattr(data, campo) is not None:
                payload[campo] = getattr(data, campo)
        updated = self._repo.update(str(id), empresa_id, payload)
        self._audit.registrar(**payload_update_asignacion_capacitacion(prior, updated, usuario_id))
        logger.info("Asignación actualizada", extra={"asignacion_id": str(id)})
        return updated  # type: ignore[return-value]

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> None:
        """Elimina la asignación (hard delete, sin guardas).

        🔴 Lo que se pierde es el HISTORIAL DE FORMACIÓN de esa persona: estado, fechas y la ruta
        del certificado —cuyo objeto queda huérfano en el bucket, porque el path vivía sólo acá—.
        El evento se arma con la fila viva y se registra después del borrado.

        Raises: ASIGNACION_NOT_FOUND (404).
        """
        prior = self._repo.find_by_id(str(id), empresa_id)
        if not prior:
            raise AppError("Asignación no encontrada", "ASIGNACION_NOT_FOUND", 404)
        self._repo.delete(str(id), empresa_id)
        self._audit.registrar(**payload_baja_asignacion_capacitacion(prior, usuario_id))
        logger.info("Asignación eliminada", extra={"asignacion_id": str(id)})

    def upload_certificado(self, id: str, empresa_id: Optional[UUID], content: bytes, filename: str,
                           content_type: str, usuario_id: Optional[str] = None) -> AsignacionResponse:
        """Adjunta el comprobante. Ver `_asignacion_certificado.subir`."""
        return _subir_certificado(self._repo, self._audit, id, empresa_id, content, filename,
                                  content_type, usuario_id)

    def get_certificado_signed_url(self, id: str, empresa_id: Optional[UUID] = None) -> str:
        """URL firmada de descarga. Ver `_asignacion_certificado.url_firmada`."""
        return _url_certificado(self._repo, id, empresa_id)
