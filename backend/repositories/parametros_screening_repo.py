"""
Repositorio del criterio configurable del clasificador de CVs (migración 100).

Mismo patrón que `configuracion_repo`: `empresa_id IS NULL` identifica la fila GLOBAL, así que
las lecturas vienen de a pares (la de la empresa y la global) y el service resuelve el COALESCE.

🔴 Filtrar por NULL en PostgREST es `.is_("empresa_id", "null")`, NO `.eq("empresa_id", None)`.
Ese último manda `empresa_id=eq.None`, que compara contra el string "None" y no matchea nada, en
silencio — devolvería "no hay fila global" y el clasificador quedaría sin criterio.
"""
from typing import Any, Dict, Optional

from integrations.supabase_client import supabase_admin
from utils.errors import AppError

_T = "parametros_screening"

_COLS = "def_relevante, def_dudoso, def_no_relevante, instrucciones"


class ParametrosScreeningRepo:
    def find(self, empresa_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Criterio de una empresa, o el de la fila global si `empresa_id` es None."""
        q = supabase_admin.table(_T).select(_COLS)
        q = q.is_("empresa_id", "null") if empresa_id is None else q.eq("empresa_id", empresa_id)
        res = q.maybe_single().execute()
        return res.data if res and res.data else None

    def upsert(self, empresa_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea o pisa la fila de la empresa. Upsert y no update porque la empresa puede no tener
        fila propia todavía: hasta ahora venía siguiendo la global.

        `on_conflict="empresa_id"` apunta al índice único parcial ux_parametros_screening_por_empresa.
        """
        fila = {**data, "empresa_id": empresa_id}
        res = supabase_admin.table(_T).upsert(fila, on_conflict="empresa_id").execute()
        if not res.data:
            raise AppError("No se pudo guardar el criterio de screening", "DB_ERROR", 500)
        return res.data[0]

    def borrar_propia(self, empresa_id: str) -> None:
        """
        Borra la fila de la empresa para que vuelva a heredar la global. Es el "restaurar
        defaults" de la UI.

        🔴 Restaurar es BORRAR LA PROPIA, no copiar los textos globales a la fila de la empresa.
        Si se copiaran, la empresa quedaría con `es_propia=True` y una foto congelada de los
        defaults de hoy: un ajuste posterior del criterio global no la alcanzaría, y la pantalla
        diría "criterio propio" sobre un texto que nadie escribió.

        🔴 El `.eq` no es opcional: un DELETE sin filtro se llevaría también la fila global y
        dejaría a TODAS las empresas sin criterio.
        """
        supabase_admin.table(_T).delete().eq("empresa_id", empresa_id).execute()
