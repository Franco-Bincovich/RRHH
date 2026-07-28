"""
Servicio de objetivos. Lógica de negocio del módulo Objetivos.
Flujo: router → service → repository → DB

Reglas:
  - empresa_id explícito en Create.
  - responsable_id → users (no empleados); validado como user activo.
  - Estado cambia por cambiar_estado() — no por update().
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories.objetivo_repo import ObjetivoRepo
from schemas.objetivo import (
    CambiarEstadoRequest, ESTADOS, ObjetivoCreate, ObjetivoListResponse,
    ObjetivoResponse, ObjetivoUpdate, PRIORIDADES,
)
from services._objetivos_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class ObjetivoService:
    def __init__(self, repo: Optional[ObjetivoRepo] = None) -> None:
        self._repo = repo or ObjetivoRepo()

    def get_all(
        self,
        empresa_id:     Optional[UUID] = None,
        estado:         Optional[str]  = None,
        responsable_id: Optional[str]  = None,
        prioridad:      Optional[str]  = None,
    ) -> ObjetivoListResponse:
        """Retorna todos los objetivos con filtros opcionales. None = todas las empresas."""
        items = self._repo.find_all(empresa_id, estado, responsable_id, prioridad)
        return ObjetivoListResponse(items=items, total=len(items))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel", estado: Optional[str] = None, responsable_id: Optional[str] = None, prioridad: Optional[str] = None) -> Descarga:
        """Exporta los objetivos (columnas legibles, sin UUIDs) respetando los filtros de estado,
        responsable y prioridad. None = consolidado. El motor genérico no se toca."""
        items = self._repo.find_all(empresa_id, estado, responsable_id, prioridad)
        verificar_limite_export(len(items))
        datos = {"Objetivos": construir_filas_export(items)}
        return build_export(nombre="Objetivos", datos=datos, filename_base="objetivos", formato=formato)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """Raises OBJETIVO_NOT_FOUND (404)."""
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        return row

    def create(self, data: ObjetivoCreate, created_by: str) -> ObjetivoResponse:
        """
        Crea un objetivo. Valida título, prioridad y que el responsable sea un user activo.

        Raises:
            AppError: TITULO_REQUERIDO (422), PRIORIDAD_INVALIDA (422),
                      RESPONSABLE_NO_VALIDO (422), RESPONSABLE_NO_ACTIVO (422).
        """
        if not data.titulo.strip():
            raise AppError("El título es requerido", "TITULO_REQUERIDO", 422)
        if data.prioridad not in PRIORIDADES:
            raise AppError(f"Prioridad inválida. Valores: {sorted(PRIORIDADES)}", "PRIORIDAD_INVALIDA", 422)
        self._validate_responsable(str(data.responsable_id))
        row = self._repo.save(data)
        logger.info("Objetivo creado", extra={"objetivo_id": row.id, "created_by": created_by})
        return row

    def update(self, id: UUID, data: ObjetivoUpdate, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """Actualización parcial. Revalida responsable si cambia."""
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        if data.responsable_id:
            self._validate_responsable(str(data.responsable_id))
        if data.prioridad and data.prioridad not in PRIORIDADES:
            raise AppError(f"Prioridad inválida. Valores: {sorted(PRIORIDADES)}", "PRIORIDAD_INVALIDA", 422)
        updated = self._repo.update(str(id), data, empresa_id)
        logger.info("Objetivo actualizado", extra={"objetivo_id": str(id)})
        return updated  # type: ignore[return-value]

    def cambiar_estado(self, id: UUID, data: CambiarEstadoRequest, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """
        Mueve el objetivo a otro estado del kanban.
        Alimenta los botones ← y → del tablero.

        Raises:
            AppError: ESTADO_INVALIDO (422), OBJETIVO_NOT_FOUND (404).
        """
        if data.estado not in ESTADOS:
            raise AppError(f"Estado inválido. Valores: {sorted(ESTADOS)}", "ESTADO_INVALIDO", 422)
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        updated = self._repo.set_estado(str(id), data.estado, empresa_id)
        logger.info("Estado de objetivo cambiado", extra={"objetivo_id": str(id), "estado": data.estado})
        return updated  # type: ignore[return-value]

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """Elimina el objetivo permanentemente (no hay historial que preservar)."""
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        self._repo.delete(str(id), empresa_id)
        logger.info("Objetivo eliminado", extra={"objetivo_id": str(id)})

    def _validate_responsable(self, responsable_id: str) -> None:
        """Verifica que el responsable sea un user activo en la tabla users (no empleados)."""
        res = supabase_admin.table("users").select("activo").eq("id", responsable_id).maybe_single().execute()
        if not res.data:
            raise AppError("Responsable no encontrado en users", "RESPONSABLE_NO_VALIDO", 422)
        if not res.data.get("activo"):
            raise AppError("El responsable no está activo", "RESPONSABLE_NO_ACTIVO", 422)
