"""
Mapper de `eventos_agenda`: fila cruda → `EventoResponse`, con los tres nombres resueltos POR
LOTE (la empresa, quién lo creó y quién lo resolvió).

🔴 LOOKUPS BATCH Y NO EMBEDS DE POSTGREST, por el mismo motivo que en recategorizaciones y con un
agravante propio: `eventos_agenda` tiene **DOS FKs a `users`** (`created_by` y `resuelta_por`).
Un embed `users(nombre)` desde esta tabla es AMBIGUO de entrada y PostgREST responde **300
PGRST201**, con el único síntoma de una pantalla en blanco. Con lookups batch el problema no
existe: son tres selects de columnas planas, sin ninguna relación declarada.

⚠️ **NO ES N+1.** Se juntan los ids de TODA la página y se hace UNA query por dimensión (dos, en
realidad: los dos ids de usuario se resuelven con un solo `in_` sobre `users`), sin importar si
la página trae 1 fila o 100. El anti-patrón sería consultar por fila.

Los tres nombres son DERIVADOS: no son datos de la fila sino resultado de cómo se la leyó. Por
eso quedan fuera del diff de auditoría (`_DERIVADOS_EVENTO`), que es el bug del "diff fantasma"
que este repo ya cerró una vez.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.evento_agenda import EventoResponse

TABLE = "eventos_agenda"

# Columnas de la tabla, sin embeds. El `*` sería equivalente hoy, pero enumerar deja el spec
# validable por `tests/test_selects_repos.py` contra `db/schema.sql`.
SELECT = ("id, empresa_id, nombre, fecha, descripcion, dias_aviso, es_publica, "
          "resuelta, resuelta_at, resuelta_por, created_by, created_at, updated_at")


def _mapa(tabla: str, ids: list, campos: str, armar) -> dict:
    """{id: etiqueta} para un lote de ids. Dict vacío si no hay ids (no consulta al pedo)."""
    if not ids:
        return {}
    filas = supabase_admin.table(tabla).select(campos).in_("id", ids).execute().data or []
    return {f["id"]: armar(f) for f in filas}


def build(rows: List[dict]) -> List[EventoResponse]:
    """Enriquece un lote de filas con la empresa y los dos nombres de usuario.

    🔑 LOS DOS IDS DE USUARIO SE PIDEN EN UNA SOLA QUERY, uniendo `created_by` y `resuelta_por`
    en el mismo `in_`. Son la misma tabla y la misma proyección: separarlos duplicaría la ida a
    la base para no ganar nada, y en la agenda lo normal es que el que resolvió sea el que cargó.

    Los nombres quedan en None si el id no se encuentra. `resuelta_por` además puede ser NULL por
    diseño (su FK es ON DELETE SET NULL, y un evento sin resolver no tiene ninguno). Un nombre
    que no resuelve no puede tumbar la lectura de la agenda.
    """
    if not rows:
        return []
    empresa_map = _mapa("empresas", list({r["empresa_id"] for r in rows if r.get("empresa_id")}),
                        "id, nombre", lambda f: f["nombre"])
    user_ids = {r[c] for r in rows for c in ("created_by", "resuelta_por") if r.get(c)}
    user_map = _mapa("users", list(user_ids), "id, nombre, apellido",
                     lambda f: f"{f['nombre']} {f['apellido']}")
    return [
        EventoResponse.model_validate({
            **r,
            "empresa_nombre": empresa_map.get(r.get("empresa_id")),
            "created_by_nombre": user_map.get(r.get("created_by")),
            "resuelta_por_nombre": user_map.get(r.get("resuelta_por")),
        })
        for r in rows
    ]
