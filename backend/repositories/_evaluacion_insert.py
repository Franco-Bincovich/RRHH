"""
El insert en lote de las tablas de evaluaciones, con su verificación POR CONTEO.

Vivía en `evaluacion_repo` como `_insert_completo`; salió al partirse el repo por entidad, porque
lo usan los dos lados (evaluados y resultados) y no podía quedar en ninguno de los dos.

🔴 VERIFICA QUE VUELVAN TODAS LAS FILAS, y ése es su motivo de existir. Un insert parcial de
PostgREST no levanta excepción: devuelve las que entraron. Sin este conteo, `confirmar()` de
evaluaciones daría por bueno un lote incompleto y recién se notaría al mirar las métricas.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from utils.errors import AppError


def insert_completo(tabla: str, filas: List[dict], error_msg: str) -> List[dict]:
    """Inserta `filas` (bulk); [] si no hay. DB_ERROR si el insert no devuelve TODAS las esperadas
    (no silencia parcial/vacío) — para que la verificación por conteo del import sea confiable."""
    if not filas:
        return []
    data = supabase_admin.table(tabla).insert(filas).execute().data or []
    if len(data) != len(filas):
        raise AppError(error_msg, "DB_ERROR", 500)
    return data


