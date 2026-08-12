"""
Servicio de objetivos. Lógica de negocio del módulo Objetivos.
Flujo: router → service → repository → DB

Reglas:
  - empresa_id explícito en Create.
  - responsable_id → users (no empleados); validado como user activo.
  - Estado cambia por cambiar_estado() — no por update().

JERARQUÍA: profundidad máxima 2. Las dos guardas viven en services/_objetivos_jerarquia.py y se
aplican en las DOS puntas — al elegir padre (`ensure_padre_valido`) y al colgar un objetivo que
ya tiene hijos (`ensure_no_tiene_hijos`). 🔴 El ESTADO del padre es INDEPENDIENTE del de sus
hijos y `cambiar_estado` funciona igual en padres e hijos: es una decisión de producto, no un
pendiente. Un padre "terminado" con hijos "por hacer" es un estado que el tablero admite.

RESPONSABLES: `responsable_id` es el DUEÑO y no se toca; la lista adicional va a la puente. Los
dos caminos validan contra `users` con la MISMA función, así que un responsable inactivo se
rechaza igual venga como dueño o como acompañante.
"""
from typing import Optional
from uuid import UUID

from repositories.objetivo_repo import ObjetivoRepo
from repositories.usuario_repo import UsuarioRepo
from schemas.objetivo import (
    CambiarEstadoRequest, ESTADOS, ObjetivoCreate, ObjetivoListResponse,
    ObjetivoResponse, ObjetivoUpdate, PRIORIDADES,
)
from repositories._objetivos_arbol import contar_con_hijos
from services._limite_export import verificar_limite_export
from services._objetivos_export import construir_filas_export
from services._objetivos_jerarquia import ensure_no_tiene_hijos, ensure_padre_valido
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
        responsable y prioridad. None = consolidado. El motor genérico no se toca.

        🔴 EL ARCHIVO TRAE PADRES E HIJOS, así que el tope de filas se cuenta sobre el árbol
        APLANADO y no sobre las raíces: `find_all` devuelve raíces con hijos anidados, y
        `len(items)` diría bastante menos de lo que se va a escribir. Con el conteo equivocado,
        un export de 4.000 raíces con 4.000 hijos pasaría el tope de 5.000 y produciría 8.000
        filas — que es justo el archivo demasiado grande que el tope existe para evitar."""
        items = self._repo.find_all(empresa_id, estado, responsable_id, prioridad)
        verificar_limite_export(contar_con_hijos(items))
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
        for extra in (data.responsables or []):
            self._validate_responsable(str(extra))
        ensure_padre_valido(self._repo, data.parent_id, data.empresa_id)
        row = self._repo.save(data)
        logger.info("Objetivo creado", extra={"objetivo_id": row.id, "created_by": created_by})
        return row

    def update(self, id: UUID, data: ObjetivoUpdate, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """Actualización parcial. Revalida responsable si cambia."""
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        if data.responsable_id:
            self._validate_responsable(str(data.responsable_id))
        for extra in (data.responsables or []):
            self._validate_responsable(str(extra))
        if data.parent_id:
            # Las DOS puntas de la profundidad 2: que el padre elegido no sea ya un hijo, y que
            # el objetivo que se cuelga no tenga hijos propios (se volverían nietos).
            ensure_padre_valido(self._repo, data.parent_id, empresa_id, str(id))
            ensure_no_tiene_hijos(self._repo, id, empresa_id)
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
        """Verifica que el responsable sea un user activo en `users` (no empleados). Reusa
        `get_estado`: trae 2 columnas de más, pero recortarlas tocaría a su otro caller."""
        estado = UsuarioRepo().get_estado(responsable_id)
        if not estado:
            raise AppError("Responsable no encontrado en users", "RESPONSABLE_NO_VALIDO", 422)
        if not estado.get("activo"):
            raise AppError("El responsable no está activo", "RESPONSABLE_NO_ACTIVO", 422)
