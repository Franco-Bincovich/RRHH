"""
Servicio de períodos cerrados (bloqueo por período). Flujo: router → service → repository.

Cierra/reabre períodos (rango de fechas) por empresa y módulo (módulo None = todos).
Reversible vía estado: reabrir conserva la fila y su traza. Audita cierre y reapertura.
El check de bloqueo en sí vive en _periodo_utils.verificar_periodo_abierto (lo usa B3.2).
"""
from datetime import date
from typing import Optional
from uuid import UUID

from repositories.periodo_repo import PeriodoRepo
from schemas.periodo import PeriodoListResponse, PeriodoResponse
from services._audit_payloads_rrhh import payload_cierre_periodo, payload_reapertura_periodo
from services._limite_export import verificar_limite_export
from services._periodos_export import construir_filas_export
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class PeriodoService:
    def __init__(self, repo: Optional[PeriodoRepo] = None, audit: Optional[AuditService] = None) -> None:
        self._repo = repo or PeriodoRepo()
        self._audit = audit or AuditService()

    def listar(self, empresa_id: Optional[UUID] = None) -> PeriodoListResponse:
        """Retorna los períodos de una empresa (todos los estados). None = todas las empresas."""
        items = self._repo.listar(empresa_id)
        return PeriodoListResponse(items=items, total=len(items))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel") -> Descarga:
        """Exporta los períodos cerrados por el MISMO `listar` del repo que usa la pantalla, así
        el archivo no puede traer filas que el listado no muestre. El motor genérico no se toca."""
        items = self._repo.listar(empresa_id)
        verificar_limite_export(len(items))
        datos = {"Períodos": construir_filas_export(items)}
        return build_export(nombre="Períodos cerrados", datos=datos, filename_base="periodos", formato=formato)

    def cerrar(
        self, empresa_id: UUID, modulo: Optional[str], desde: date, hasta: date, usuario_id: Optional[str]
    ) -> PeriodoResponse:
        """Cierra un período [desde, hasta] para una empresa (y módulo opcional). Audita el cierre.
        Raises: FECHA_INVALIDA (422) si hasta < desde."""
        if hasta < desde:
            raise AppError("La fecha de fin debe ser posterior o igual a la de inicio", "FECHA_INVALIDA", 422)
        periodo = self._repo.crear({
            "empresa_id": str(empresa_id), "modulo": modulo,
            "desde": str(desde), "hasta": str(hasta), "cerrado_por": usuario_id,
        })
        self._audit.registrar(**payload_cierre_periodo(periodo, usuario_id))
        logger.info("Período cerrado", extra={"periodo_id": periodo.id, "empresa_id": str(empresa_id), "modulo": modulo})
        return periodo

    def reabrir(self, id: str, empresa_id: Optional[UUID], usuario_id: Optional[str]) -> PeriodoResponse:
        """Reabre un período (estado='abierto'), validando pertenencia a la empresa. Audita la reapertura.
        Raises: PERIODO_NOT_FOUND (404), PERIODO_YA_ABIERTO (409)."""
        periodo = self._repo.find_by_id(id)
        if not periodo or (empresa_id and str(periodo.empresa_id) != str(empresa_id)):
            raise AppError("Período no encontrado", "PERIODO_NOT_FOUND", 404)
        if periodo.estado == "abierto":
            raise AppError("El período ya está abierto", "PERIODO_YA_ABIERTO", 409)
        self._repo.reabrir(id, usuario_id)
        actualizado = self._repo.find_by_id(id)
        self._audit.registrar(**payload_reapertura_periodo(actualizado, usuario_id))
        logger.info("Período reabierto", extra={"periodo_id": id})
        return actualizado  # type: ignore[return-value]
