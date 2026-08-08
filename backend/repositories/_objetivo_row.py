"""
El enriquecido de una fila de objetivo: empresa, responsable, título del padre y la lista
completa de responsables, todos resueltos a nombre.

Molde: `_inventario_items_row.py` y `_empleado_row.py` — la forma de la lectura y su traducción
a schema viven en un solo lugar para que no puedan divergir entre los tres métodos que la usan
(`find_all`, `find_by_id` y, por su vía, `save`/`update`/`set_estado`). Vive aparte porque
`objetivo_repo.py` estaba en 99 contra un límite de 100 y no admitía una línea más.

🔴 `responsable_id` apunta a `users`, NO a `empleados` — este tablero es de tareas del equipo de
RRHH, no de los 31 empleados. Es una decisión de producto cerrada, y es la razón por la que el
lookup de personas pega a `users`.

🔴 TODO SE RESUELVE CON LOOKUPS BATCH (un `IN` por dimensión) Y **CERO EMBEDS DE POSTGREST**, a
propósito. `objetivos` pasó a tener DOS relaciones contra `users` —la columna `responsable_id` y
la tabla puente `objetivo_responsables`—, y ese es exactamente el escenario que produce un
PGRST201: un embed `users(...)` que hoy resolvería, con dos caminos posibles se vuelve ambiguo y
el endpoint devuelve 300 sin que ningún test con el fake de Supabase pueda verlo. Con lookups
batch el problema no se evita: no existe. Además es el patrón que este archivo ya usaba.

🔴 `parent_titulo` es un campo DERIVADO de otra fila, no una columna. Alimenta la columna
"Objetivo padre" del export. Como todo derivado de join, NUNCA debe entrar en un diff de
auditoría (ver la regla de `sin_derivados` en services/_audit_payloads.py) — hoy el módulo no
audita nada, pero el día que lo haga esto ya está dicho.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.objetivo import ObjetivoResponse, ResponsableItem


def _responsables_map(objetivo_ids: List[str]) -> dict:
    """objetivo_id → [user_id, ...], leído de la puente en UNA sola consulta."""
    filas = (supabase_admin.table("objetivo_responsables").select("objetivo_id, user_id")
             .in_("objetivo_id", objetivo_ids).execute().data or [])
    out: dict = {}
    for f in filas:
        out.setdefault(f["objetivo_id"], []).append(f["user_id"])
    return out


def _build(rows: List[dict]) -> List[ObjetivoResponse]:
    """Enriquece filas con empresa, responsable, título del padre y lista de responsables."""
    if not rows:
        return []
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", list({r["empresa_id"] for r in rows})).execute().data or [])
    }
    resp_por_obj = _responsables_map([r["id"] for r in rows])
    # Un solo lookup de personas para las DOS necesidades: el dueño y los de la puente.
    user_ids = {r["responsable_id"] for r in rows} | {u for v in resp_por_obj.values() for u in v}
    user_map = {
        u["id"]: f"{u['nombre']} {u['apellido']}"
        for u in (supabase_admin.table("users").select("id, nombre, apellido")
                  .in_("id", list(user_ids)).execute().data or [])
    }
    padre_ids = list({r["parent_id"] for r in rows if r.get("parent_id")})
    padre_map = {
        p["id"]: p["titulo"]
        for p in (supabase_admin.table("objetivos").select("id, titulo")
                  .in_("id", padre_ids).execute().data or [])
    } if padre_ids else {}
    return [
        ObjetivoResponse.model_validate({
            **r,
            "empresa_nombre":    empresa_map.get(r["empresa_id"]),
            "responsable_nombre": user_map.get(r["responsable_id"]),
            "parent_titulo":     padre_map.get(r.get("parent_id")),
            "responsables": [
                ResponsableItem(id=uid, nombre=user_map.get(uid))
                # Fallback al dueño: si la puente todavía no tiene filas para este objetivo
                # (fila anterior al backfill de la 096), la lista no puede salir vacía — el
                # dueño SIEMPRE es responsable.
                for uid in resp_por_obj.get(r["id"], [r["responsable_id"]])
            ],
        })
        for r in rows
    ]
