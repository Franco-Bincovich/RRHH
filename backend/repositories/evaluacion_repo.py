"""
Repositorio de resultados de evaluaciones importados (service_key; control app-level).
Cubre las tres tablas del lote: evaluacion_lotes / _evaluados / _resultados. Escritura por
lote (bulk insert) + lecturas por padre. Sin lógica de import. Patrón defensivo de respuesta
Supabase (res and res.data), como en cesion_repo/empleado_repo. Un repo más a portar a asyncpg.
"""
from typing import List, Optional, Tuple

from integrations.supabase_client import supabase_admin
from repositories import _evaluacion_evaluados_repo as _ev
from repositories._evaluacion_insert import insert_completo
from repositories._evaluacion_lotes_enrich import enriquecer_lotes
from schemas.evaluacion_resultados import EvaluadoResponse, LoteResponse, ResultadoResponse
from utils.errors import AppError
from utils.logger import logger

_LOTES = "evaluacion_lotes"
_EVALUADOS = "evaluacion_evaluados"
_RESULTADOS = "evaluacion_resultados"


class EvaluacionRepo:
    # ── Lotes ──
    def crear_lote(self, datos: dict) -> LoteResponse:
        """Inserta un lote y devuelve el registro creado."""
        res = supabase_admin.table(_LOTES).insert(datos).execute()
        if not res or not res.data:
            logger.error("Supabase insert vacío en evaluacion_lotes")
            raise AppError("Error al guardar el lote de evaluación", "DB_ERROR", 500)
        return LoteResponse.model_validate(res.data[0])

    def find_lote_by_id(self, id: str) -> Optional[LoteResponse]:
        """Lote por UUID. None si no existe."""
        res = supabase_admin.table(_LOTES).select("*").eq("id", id).maybe_single().execute()
        return LoteResponse.model_validate(res.data) if res and res.data else None

    def find_lote_by_periodo(self, empresa_id: str, periodo: str) -> Optional[LoteResponse]:
        """Lote de (empresa, periodo) — base del reemplazo al reimportar. None si no existe."""
        res = (supabase_admin.table(_LOTES).select("*")
               .eq("empresa_id", empresa_id).eq("periodo", periodo).maybe_single().execute())
        return LoteResponse.model_validate(res.data) if res and res.data else None

    def delete_lote(self, id: str) -> bool:
        """Borra el lote; el CASCADE de las FK elimina sus evaluados y resultados. True si borró."""
        res = supabase_admin.table(_LOTES).delete().eq("id", id).execute()
        return bool(res and res.data)

    def update_periodo_lote(self, id: str, periodo: str) -> None:
        """Renombra el período de un lote (por id). DB_ERROR si el update no afecta ninguna fila."""
        res = supabase_admin.table(_LOTES).update({"periodo": periodo}).eq("id", id).execute()
        if not res or not res.data:
            raise AppError("Error al renombrar el lote de evaluación", "DB_ERROR", 500)

    def find_lotes(self, empresa_id: Optional[str] = None) -> List[LoteResponse]:
        """Lotes (recientes primero) enriquecidos (empresa, quién importó, conteo), lookups batch."""
        q = supabase_admin.table(_LOTES).select("*")
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        res = q.order("created_at", desc=True).execute()
        return enriquecer_lotes(res.data or [] if res else [])

    # ── Evaluados (delegados a _evaluacion_evaluados_repo) ──

    def crear_evaluados(self, filas: List[dict]) -> List[EvaluadoResponse]:
        """Alta en lote. Delegado a _evaluacion_evaluados_repo."""
        return _ev.crear_evaluados(filas)

    def find_evaluados(self, lote_id: str) -> List[EvaluadoResponse]:
        """El lote ENTERO (métricas y ficha). Delegado a _evaluacion_evaluados_repo."""
        return _ev.find_evaluados(lote_id)

    def find_evaluados_pagina(self, lote_id: str, page: int = 1, page_size: int = 20,
                              sector=None, perfil=None, con_nota=None, empleado_ids=None):
        """Una página con los filtros en el WHERE. Delegado a _evaluacion_evaluados_repo."""
        return _ev.find_evaluados_pagina(lote_id, page, page_size, sector, perfil, con_nota,
                                         empleado_ids)

    def sectores_del_lote(self, lote_id: str) -> List[str]:
        """Los sectores distintos del lote. Delegado a _evaluacion_evaluados_repo."""
        return _ev.sectores_del_lote(lote_id)

    # ── Resultados ──
    def crear_resultados(self, filas: List[dict]) -> List[ResultadoResponse]:
        """Inserta N resultados (bulk). [] si no hay; DB_ERROR si el insert no devuelve todas."""
        data = insert_completo(_RESULTADOS, filas, "Error al guardar los resultados del lote")
        return [ResultadoResponse.model_validate(r) for r in data]

    def find_resultados_por_evaluados(self, ids: List[str]) -> List[ResultadoResponse]:
        """Resultados de varios evaluados (todo el lote) en una sola query. [] si no hay ids."""
        if not ids:
            return []
        res = supabase_admin.table(_RESULTADOS).select("*").in_("evaluado_id", ids).order("orden").execute()
        return [ResultadoResponse.model_validate(r) for r in (res.data or [])] if res else []
