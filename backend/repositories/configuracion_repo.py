"""
Repositorio de la configuración de reglas (migración 085): parámetros escalares y escala
de vacaciones.

`empresa_id IS NULL` identifica la fila GLOBAL, así que las lecturas vienen de a pares: la
de la empresa y la global. Filtrar por NULL en PostgREST es `.is_("empresa_id", "null")`,
NO `.eq("empresa_id", None)` — ese último manda `empresa_id=eq.None`, que compara contra el
string "None" y no matchea nada, en silencio.
"""
from typing import Any, Dict, List, Optional

from integrations.supabase_client import supabase_admin
from utils.errors import AppError

_PARAMS, _ESCALA = "parametros_empresa", "reglas_vacaciones_escala"

_COLS_PARAMS = (
    "base_dias_habiles, corte_antiguedad_mes, periodo_vacacional_desde_mes, "
    "periodo_vacacional_hasta_mes, primer_anio_mes_corte, primer_anio_dias, vencimiento_anios"
)


class ConfiguracionRepo:
    def find_parametros(self, empresa_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parámetros de una empresa, o de la fila global si `empresa_id` es None."""
        q = supabase_admin.table(_PARAMS).select(_COLS_PARAMS)
        q = q.is_("empresa_id", "null") if empresa_id is None else q.eq("empresa_id", empresa_id)
        res = q.maybe_single().execute()
        return res.data if res and res.data else None

    def upsert_parametros(self, empresa_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea o pisa la fila de la empresa. Es upsert y no update porque la empresa puede no
        tener fila propia todavía: hasta ahora venía siguiendo la global.

        `on_conflict="empresa_id"` apunta al índice único parcial ux_parametros_empresa_por_empresa.
        """
        fila = {**data, "empresa_id": empresa_id}
        res = supabase_admin.table(_PARAMS).upsert(fila, on_conflict="empresa_id").execute()
        if not res.data:
            raise AppError("No se pudo guardar la configuración", "DB_ERROR", 500)
        return res.data[0]

    def find_escala(self, empresa_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Tramos de una empresa (o de la escala global si es None), ordenados por antigüedad.

        El ORDEN LO PONE LA QUERY, no el service: el tramo aplicable es el de mayor
        antiguedad_anios que no supere la del empleado, y esa búsqueda se lee sobre una lista
        ordenada. Ordenar en Python dejaría la query libre de romperse sin que nadie lo note.
        """
        q = supabase_admin.table(_ESCALA).select("antiguedad_anios, dias")
        q = q.is_("empresa_id", "null") if empresa_id is None else q.eq("empresa_id", empresa_id)
        return q.order("antiguedad_anios").execute().data or []

    def replace_escala(self, empresa_id: str, tramos: List[Dict[str, Any]]) -> None:
        """
        Reemplaza la escala completa de la empresa: borra la suya y escribe la nueva.

        🔴 Borra SOLO donde empresa_id = la empresa. Sin ese `.eq`, un DELETE sin filtro se
        llevaría también la fila global y dejaría sin reglas a TODAS las demás empresas.

        ⚠️ Los dos pasos NO son una transacción: PostgREST no la ofrece entre llamadas. El
        borrado va primero porque el índice único (empresa_id, antiguedad_anios) impide
        insertar los nuevos antes de sacar los viejos. Si el INSERT falla, la empresa queda
        SIN tramos propios y vuelve a heredar la escala global — un estado válido y
        documentado, no datos corruptos, y el AppError le dice al usuario que reintente.
        """
        supabase_admin.table(_ESCALA).delete().eq("empresa_id", empresa_id).execute()
        if not tramos:
            return
        filas = [{**t, "empresa_id": empresa_id} for t in tramos]
        res = supabase_admin.table(_ESCALA).insert(filas).execute()
        if not res.data or len(res.data) != len(filas):
            raise AppError("No se pudo guardar la escala completa", "DB_ERROR", 500)
