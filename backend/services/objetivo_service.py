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

VALIDACIONES: los campos en _objetivos_validaciones.py y la jerarquía en _objetivos_jerarquia.py,
los dos salidos de acá por límite de líneas. Este archivo se queda con la ORQUESTACIÓN —qué se
valida y en qué ORDEN—, que es load-bearing: el gate del responsable va ANTES del insert.

🔴 LAS CUATRO ESCRITURAS AUDITAN, Y ES TODO O NADA (24/8/2026). Hasta esa fecha este módulo era
el ÚNICO del sistema con borrado desde la UI y CERO eventos de auditoría, y no fue gratis: un
objetivo real de Karstec desapareció entre el 17/8 y el 24/8 sin dejar rastro de quién ni cuándo.
`tests/test_auditoria_coherente.py` no podía cazarlo —su alcance son los módulos que YA emiten
algún evento, así que uno que no emite ninguno queda afuera POR CONSTRUCCIÓN— y por eso la misma
tanda suma el barrido que sí lo caza (`tests/test_auditoria_destructivas.py`). Los
payloads, con el porqué de cada campo excluido, en `services/_audit_payloads_objetivos.py`.

⚠️ EL EXPORT NO ESTÁ ACÁ: vive en `services/_objetivos_export.py`, junto a las filas que arma.
Se mudó en esta misma tanda para hacerle lugar a la auditoría — el porqué del corte está allá.
"""
from typing import Optional
from uuid import UUID

from repositories.objetivo_repo import ObjetivoRepo
from schemas.objetivo import (
    CambiarEstadoRequest, ObjetivoCreate, ObjetivoListResponse,
    ObjetivoResponse, ObjetivoUpdate,
)
from schemas.objetivo_filtros import SIN_FILTROS, ObjetivosFiltros
from services._audit_payloads_objetivos import payload_alta_objetivo, payload_update_objetivo
from services._paginacion import sin_paginar
from services._objetivos_duplicado import duplicado_a_409
from services._objetivos_export import exportar as _exportar
from services._objetivos_jerarquia import ensure_no_tiene_hijos, ensure_padre_valido
from services._objetivos_validaciones import ensure_prioridad_valida, ensure_responsable_valido, ensure_responsables_validos
from services._objetivos_write import cambiar_estado, eliminar
from services.audit_service import AuditService
from services.export import Descarga
from utils.errors import AppError
from utils.logger import logger


class ObjetivoService:
    def __init__(self, repo: Optional[ObjetivoRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or ObjetivoRepo()
        self._audit = audit or AuditService()

    def get_all(self, empresa_id: Optional[UUID] = None,
                filtros: ObjetivosFiltros = SIN_FILTROS) -> ObjetivoListResponse:
        """Retorna todos los objetivos con filtros opcionales. None = todas las empresas.

        ⚠️ EL TOTAL CUENTA RAÍCES, y con el filtro por `tipo` esa diferencia se vuelve visible:
        el mismo objetivo puede contar como hijo en una vista y como raíz en la otra. Por qué es
        correcto: `_objetivos_arbol.armar_arbol`.
        """
        items = self._repo.find_all(empresa_id, filtros)
        return ObjetivoListResponse(items=items, **sin_paginar(items))

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel",
                 filtros: ObjetivosFiltros = SIN_FILTROS) -> Descarga:
        """Exporta los objetivos con los MISMOS filtros que el listado. Ver `_objetivos_export`."""
        return _exportar(self._repo, empresa_id, formato, filtros)

    def get_by_id(self, id: UUID, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """Raises OBJETIVO_NOT_FOUND (404)."""
        row = self._repo.find_by_id(str(id), empresa_id)
        if not row:
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        return row

    def create(self, data: ObjetivoCreate, created_by: str) -> ObjetivoResponse:
        """
        Crea un objetivo. Valida título, prioridad y que el responsable sea un user activo.

        `tipo` NO se valida acá: es un `Literal` en el schema y Pydantic lo rechaza antes. La
        asimetría con `prioridad` (que sí es `str`) está explicada en `_objetivos_validaciones`.

        Raises:
            AppError: TITULO_REQUERIDO (422), PRIORIDAD_INVALIDA (422),
                      RESPONSABLE_NO_VALIDO (422), RESPONSABLE_NO_ACTIVO (422),
                      OBJETIVO_DUPLICADO (409).
        """
        if not data.titulo.strip():
            raise AppError("El título es requerido", "TITULO_REQUERIDO", 422)
        ensure_prioridad_valida(data.prioridad)
        ensure_responsable_valido(str(data.responsable_id))
        ensure_responsables_validos(data.responsables)
        ensure_padre_valido(self._repo, data.parent_id, data.empresa_id)
        with duplicado_a_409():
            row = self._repo.save(data)
        # La empresa del evento sale del OBJETIVO (`data.empresa_id`, explícito en el body) y no
        # del header: auditar es una ACCIÓN y la empresa la decide el form, no el sidebar.
        self._audit.registrar(**payload_alta_objetivo(row, created_by))
        logger.info("Objetivo creado", extra={"objetivo_id": row.id, "created_by": created_by})
        return row

    def update(self, id: UUID, data: ObjetivoUpdate, empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> ObjetivoResponse:
        """Actualización parcial. Revalida responsable si cambia.

        🔴 La edición TAMBIÉN puede chocar el índice único —cambiar título, periodicidad o TIPO
        puede dejar el objetivo idéntico a otro— y por eso lleva el mismo `duplicado_a_409` que
        el alta. Ver ese módulo.

        🔑 EL `prior` SE GUARDA: el `find_by_id` que verifica existencia ES el "antes" del diff.
        Sin él habría que releer, y releer DESPUÉS del update daría un diff vacío."""
        prior = self._repo.find_by_id(str(id), empresa_id)
        if not prior:
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        if data.responsable_id:
            ensure_responsable_valido(str(data.responsable_id))
        ensure_responsables_validos(data.responsables)
        if data.parent_id:
            # Las DOS puntas de la profundidad 2: que el padre elegido no sea ya un hijo, y que
            # el objetivo que se cuelga no tenga hijos propios (se volverían nietos).
            ensure_padre_valido(self._repo, data.parent_id, empresa_id, str(id))
            ensure_no_tiene_hijos(self._repo, id, empresa_id)
        ensure_prioridad_valida(data.prioridad, opcional=True)
        with duplicado_a_409():
            updated = self._repo.update(str(id), data, empresa_id)
        self._audit.registrar(**payload_update_objetivo(prior, updated, usuario_id))
        logger.info("Objetivo actualizado", extra={"objetivo_id": str(id)})
        return updated  # type: ignore[return-value]

    # Las dos de abajo delegan en `_objetivos_write`: no orquestan validaciones, sólo verifican
    # existencia y escriben. El porqué del corte está en el encabezado de ese módulo.
    def cambiar_estado(self, id: UUID, data: CambiarEstadoRequest, empresa_id: Optional[UUID] = None,
                       usuario_id: Optional[str] = None) -> ObjetivoResponse:
        """Mueve el objetivo a otro estado del kanban. Ver `_objetivos_write.cambiar_estado`."""
        return cambiar_estado(self._repo, self._audit, id, data, empresa_id, usuario_id)

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> None:
        """Elimina el objetivo y sus subobjetivos. Ver `_objetivos_write.eliminar`."""
        eliminar(self._repo, self._audit, id, empresa_id, usuario_id)
