"""
La tabla puente `objetivo_responsables` (migración 096): escritura y filtro.

Vive aparte de `objetivo_repo.py` por límite de líneas (el repo estaba en 80 contra un tope de
100 y esto no entraba). Molde: `_scope_filtros.py` — funciones libres que resuelven "qué filas
caen bajo este filtro" y se aplican sobre la query del repo.

🔴 EL FILTRO POR RESPONSABLE MIRA LOS DOS LADOS, y no es redundancia defensiva. Después de la
096 el dueño está SIEMPRE en la puente (el backfill lo garantiza para lo viejo y el service para
lo nuevo), así que bastaría con la puente. Pero las migraciones las corre Franco a mano y el
código se deploya antes: en la ventana entre el deploy y la 096, la puente está VACÍA, y un
filtro que mirara solo ahí devolvería CERO objetivos para todo responsable — el listado se
vaciaría sin ningún error. El `or` sobre `responsable_id` hace que esa ventana sea invisible.

Cuando la 096 esté corrida en producción esta rama deja de aportar, pero tampoco molesta: es un
predicado más en un OR sobre una columna indexada.
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin

_T_PUENTE = "objetivo_responsables"


def ids_de_responsable(user_id: str) -> List[str]:
    """Ids de los objetivos donde `user_id` figura en la puente."""
    filas = (supabase_admin.table(_T_PUENTE).select("objetivo_id")
             .eq("user_id", user_id).execute().data or [])
    return [f["objetivo_id"] for f in filas]


def aplicar_filtro_responsable(q, user_id: str):
    """Acota la query a los objetivos de `user_id`: por la puente O por ser su dueño."""
    ids = ids_de_responsable(user_id)
    if not ids:
        return q.eq("responsable_id", user_id)
    return q.or_(f"id.in.({','.join(ids)}),responsable_id.eq.{user_id}")


def set_responsables(objetivo_id: str, user_ids: List[str], dueno: Optional[str] = None) -> None:
    """Deja la puente con EXACTAMENTE `user_ids` (más el dueño, que siempre entra).

    Borra y reinserta en vez de calcular el diff: son a lo sumo un puñado de filas por objetivo
    y el diff sería más código para el mismo resultado. El dueño se agrega acá y no en el
    caller para que NINGÚN camino pueda dejar un objetivo cuyo dueño no figure entre sus
    responsables — que es un estado que la UI no sabría mostrar.
    """
    completos = list(dict.fromkeys([*( [dueno] if dueno else [] ), *user_ids]))
    supabase_admin.table(_T_PUENTE).delete().eq("objetivo_id", objetivo_id).execute()
    if completos:
        supabase_admin.table(_T_PUENTE).insert(
            [{"objetivo_id": objetivo_id, "user_id": u} for u in completos]).execute()


def sincronizar_desde_update(repo, objetivo_id: str, data, empresa_id=None) -> None:
    """Aplica `data.responsables` a la puente, resolviendo quién es el dueño.

    El dueño sale del propio patch si la edición lo cambia, y si no, del objetivo tal como está
    hoy. Sin esa segunda rama, editar solo la lista de responsables dejaría al dueño afuera de
    su propio objetivo.
    """
    actual = repo.find_by_id(objetivo_id, empresa_id)
    dueno = str(data.responsable_id) if data.responsable_id else (actual.responsable_id if actual else None)
    set_responsables(objetivo_id, [str(u) for u in data.responsables], dueno)
