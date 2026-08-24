"""Las tres queries de HITOS de un plan de carrera.

Salen de `planes_carrera_repo` porque ese archivo llegó a su límite de 100 al agregarle la
columna `tipo` al alta, y porque son una unidad con nombre propio: el repo del plan responde
por `planes_carrera` y esto por su tabla hija. Mismo corte que `_hora_row` o
`_onboarding_templates_row`, y el repo delega igual que `find_previa` en `cadena_previa`.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.sucesion import HitoResponse
from utils.errors import AppError

_HIT = "planes_carrera_hitos"


def _fila(r: dict) -> HitoResponse:
    """Fila cruda → `HitoResponse`. Movido tal cual desde `planes_carrera_repo._hito_row`:
    `nombre` en la base es `titulo` en el schema, y `completado` se deriva del estado."""
    return HitoResponse(
        id=r["id"], plan_id=r["plan_id"], titulo=r["nombre"],
        descripcion=r.get("descripcion"), completado=r.get("estado") == "completado",
        fecha_objetivo=str(r["fecha_objetivo"]) if r.get("fecha_objetivo") else None,
    )


def listar(plan_id: str) -> list[HitoResponse]:
    """Todos los hitos de un plan."""
    res = supabase_admin.table(_HIT).select("*").eq("plan_id", plan_id).execute()
    return [_fila(r) for r in (res.data or [])]


def crear(plan_id: str, titulo: str, descripcion: Optional[str],
          fecha_objetivo: Optional[str], empresa_id: str, tipo: str = "otro") -> HitoResponse:
    """Alta de un hito.

    🔴 `tipo` VA SIEMPRE y por eso NO puede caer en el filtro de `None` de abajo: la columna es
    NOT NULL **sin default** y el schema no la tenía, así que el INSERT salía sin ella y Postgres
    lo rechazaba con 23502 → el endpoint devolvía 500 SIEMPRE. El vocabulario y el porqué del
    default están en `schemas/sucesion.HitoBodyCreate`.
    """
    payload: dict = {k: v for k, v in {
        "plan_id": plan_id, "nombre": titulo, "tipo": tipo, "empresa_id": empresa_id,
        "descripcion": descripcion, "fecha_objetivo": fecha_objetivo}.items() if v is not None}
    ins = supabase_admin.table(_HIT).insert(payload).execute()
    if not ins.data:
        raise AppError("Error al crear hito", "DB_ERROR", 500)
    return _fila(ins.data[0])


def completar(hito_id: str, empresa_id: Optional[UUID] = None) -> bool:
    """Marca el hito como completado. Con `empresa_id` acota el UPDATE a esa empresa."""
    q = (supabase_admin.table(_HIT)
         .update({"estado": "completado", "fecha_completada": date.today().isoformat()})
         .eq("id", hito_id))
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    return bool(q.execute().data)
