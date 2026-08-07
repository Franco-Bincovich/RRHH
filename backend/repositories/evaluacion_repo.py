"""
Repositorio de resultados de evaluaciones importados (service_key; control app-level).
Cubre las tres tablas del lote: evaluacion_lotes / _evaluados / _resultados. Escritura por
lote (bulk insert) + lecturas por padre. Sin lógica de import. Patrón defensivo de respuesta
Supabase (res and res.data), como en cesion_repo/empleado_repo. Un repo más a portar a asyncpg.
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from repositories._evaluacion_lotes_enrich import enriquecer_lotes
from schemas.evaluacion_resultados import EvaluadoResponse, LoteResponse, ResultadoResponse
from utils.errors import AppError
from utils.logger import logger

_LOTES = "evaluacion_lotes"
_EVALUADOS = "evaluacion_evaluados"
_RESULTADOS = "evaluacion_resultados"


def _insert_completo(tabla: str, filas: List[dict], error_msg: str) -> List[dict]:
    """Inserta `filas` (bulk); [] si no hay. DB_ERROR si el insert no devuelve TODAS las esperadas
    (no silencia parcial/vacío) — para que la verificación por conteo del import sea confiable."""
    if not filas:
        return []
    data = supabase_admin.table(tabla).insert(filas).execute().data or []
    if len(data) != len(filas):
        raise AppError(error_msg, "DB_ERROR", 500)
    return data


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

    # ── Evaluados ──
    def crear_evaluados(self, filas: List[dict]) -> List[EvaluadoResponse]:
        """Inserta N evaluados (bulk). [] si no hay; DB_ERROR si el insert no devuelve todas."""
        data = _insert_completo(_EVALUADOS, filas, "Error al guardar los evaluados del lote")
        return [EvaluadoResponse.model_validate(r) for r in data]

    def find_evaluados(self, lote_id: str) -> List[EvaluadoResponse]:
        """Evaluados de un lote, ordenados por apellido y nombre."""
        res = (supabase_admin.table(_EVALUADOS).select("*").eq("lote_id", lote_id)
               .order("apellido_evaluado").order("nombre_evaluado").execute())
        return [EvaluadoResponse.model_validate(r) for r in (res.data or [])] if res else []

    # ── Resultados ──
    def crear_resultados(self, filas: List[dict]) -> List[ResultadoResponse]:
        """Inserta N resultados (bulk). [] si no hay; DB_ERROR si el insert no devuelve todas."""
        data = _insert_completo(_RESULTADOS, filas, "Error al guardar los resultados del lote")
        return [ResultadoResponse.model_validate(r) for r in data]

    def find_resultados_por_evaluados(self, ids: List[str]) -> List[ResultadoResponse]:
        """Resultados de varios evaluados (todo el lote) en una sola query. [] si no hay ids."""
        if not ids:
            return []
        res = supabase_admin.table(_RESULTADOS).select("*").in_("evaluado_id", ids).order("orden").execute()
        return [ResultadoResponse.model_validate(r) for r in (res.data or [])] if res else []
