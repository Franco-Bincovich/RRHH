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
"""
from typing import Optional
from uuid import UUID

from repositories.objetivo_repo import ObjetivoRepo
from schemas.objetivo import (
    CambiarEstadoRequest, ObjetivoCreate, ObjetivoListResponse,
    ObjetivoResponse, ObjetivoUpdate,
)
from schemas.objetivo_filtros import SIN_FILTROS, ObjetivosFiltros
from repositories._objetivos_arbol import contar_con_hijos
from services._limite_export import verificar_limite_export
from services._paginacion import sin_paginar
from services._objetivos_duplicado import duplicado_a_409
from services._objetivos_export import construir_filas_export
from services._objetivos_jerarquia import ensure_no_tiene_hijos, ensure_padre_valido
from services._objetivos_validaciones import ensure_prioridad_valida, ensure_responsable_valido
from services._objetivos_write import cambiar_estado, eliminar
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class ObjetivoService:
    def __init__(self, repo: Optional[ObjetivoRepo] = None) -> None:
        self._repo = repo or ObjetivoRepo()

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
        """Exporta los objetivos (columnas legibles, sin UUIDs) respetando los MISMOS filtros que
        el listado. None = consolidado. El motor genérico no se toca.

        🔑 Que el listado y el export reciban el MISMO objeto `ObjetivosFiltros` es lo que hace
        estructuralmente imposible que un filtro quede en uno solo de los dos — la invariante que
        `tests/test_paridad_list_export.py` verifica del lado del router.

        🔴 EL ARCHIVO TRAE PADRES E HIJOS, así que el tope de filas se cuenta sobre el árbol
        APLANADO y no sobre las raíces: `find_all` devuelve raíces con hijos anidados, y
        `len(items)` diría bastante menos de lo que se va a escribir. Con el conteo equivocado,
        un export de 15.000 raíces con 15.000 hijos pasaría el tope de 20.000 y produciría 30.000
        filas — que es justo el archivo demasiado grande que el tope existe para evitar."""
        items = self._repo.find_all(empresa_id, filtros)
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
        for extra in (data.responsables or []):
            ensure_responsable_valido(str(extra))
        ensure_padre_valido(self._repo, data.parent_id, data.empresa_id)
        with duplicado_a_409():
            row = self._repo.save(data)
        logger.info("Objetivo creado", extra={"objetivo_id": row.id, "created_by": created_by})
        return row

    def update(self, id: UUID, data: ObjetivoUpdate, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """Actualización parcial. Revalida responsable si cambia.

        🔴 La edición TAMBIÉN puede chocar el índice único —cambiar título, periodicidad o TIPO
        puede dejar el objetivo idéntico a otro— y por eso lleva el mismo `duplicado_a_409` que
        el alta. Ver ese módulo."""
        if not self._repo.find_by_id(str(id), empresa_id):
            raise AppError("Objetivo no encontrado", "OBJETIVO_NOT_FOUND", 404)
        if data.responsable_id:
            ensure_responsable_valido(str(data.responsable_id))
        for extra in (data.responsables or []):
            ensure_responsable_valido(str(extra))
        if data.parent_id:
            # Las DOS puntas de la profundidad 2: que el padre elegido no sea ya un hijo, y que
            # el objetivo que se cuelga no tenga hijos propios (se volverían nietos).
            ensure_padre_valido(self._repo, data.parent_id, empresa_id, str(id))
            ensure_no_tiene_hijos(self._repo, id, empresa_id)
        ensure_prioridad_valida(data.prioridad, opcional=True)
        with duplicado_a_409():
            updated = self._repo.update(str(id), data, empresa_id)
        logger.info("Objetivo actualizado", extra={"objetivo_id": str(id)})
        return updated  # type: ignore[return-value]

    # Las dos de abajo delegan en `_objetivos_write`: no orquestan validaciones, sólo verifican
    # existencia y escriben. El porqué del corte está en el encabezado de ese módulo.
    def cambiar_estado(self, id: UUID, data: CambiarEstadoRequest, empresa_id: Optional[UUID] = None) -> ObjetivoResponse:
        """Mueve el objetivo a otro estado del kanban. Ver `_objetivos_write.cambiar_estado`."""
        return cambiar_estado(self._repo, id, data, empresa_id)

    def delete(self, id: UUID, empresa_id: Optional[UUID] = None) -> None:
        """Elimina el objetivo y sus subobjetivos. Ver `_objetivos_write.eliminar`."""
        eliminar(self._repo, id, empresa_id)
