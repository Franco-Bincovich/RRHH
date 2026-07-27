"""
Repositorio de áreas. Acceso directo a Supabase con supabase_admin.
Interfaz pública: find_all · find_by_id · save · update · delete
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from schemas.area import AreaCreate, AreaResponse, AreaUpdate

_TABLE = "areas"
_EMPLEADOS_TABLE = "empleados"
_SELECT = "*, empleados!fk_areas_responsable(nombre, apellido)"


def _counts_by_area() -> dict[str, int]:
    # Excluye 'baja': licencia sigue siendo headcount del área
    rows = supabase_admin.table(_EMPLEADOS_TABLE).select("area_id").neq("estado", "baja").execute().data or []
    counts: dict[str, int] = {}
    for row in rows:
        if aid := row.get("area_id"):
            counts[aid] = counts.get(aid, 0) + 1
    return counts


def _to_response(row: dict, counts: dict[str, int]) -> AreaResponse:
    emp = row.get("empleados") or {}
    responsable_nombre = (
        f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip() or None
    )
    return AreaResponse(
        id=str(row["id"]),
        empresa_id=str(row["empresa_id"]) if row.get("empresa_id") else None,
        nombre=row["nombre"],
        descripcion=row.get("descripcion"),
        responsable_id=str(row["responsable_id"]) if row.get("responsable_id") else None,
        responsable_nombre=responsable_nombre,
        cantidad_empleados=counts.get(str(row["id"]), 0),
        created_at=row["created_at"],
    )


class AreaRepo:
    def find_all(self, empresa_id: Optional[str] = None) -> List[AreaResponse]:
        """Retorna áreas activas, opcionalmente filtradas por empresa_id."""
        query = (
            supabase_admin.table(_TABLE)
            .select(_SELECT)
            .eq("activo", True)
            .order("nombre")
        )
        if empresa_id:
            query = query.eq("empresa_id", empresa_id)
        res = query.execute()
        counts = _counts_by_area()
        return [_to_response(r, counts) for r in (res.data or [])]

    def find_by_id(self, id: str, empresa_id: Optional[str] = None) -> Optional[AreaResponse]:
        """Área activa por id. Si empresa_id se provee, valida pertenencia (None = consolidado).

        maybe_single (no single): con .single() Supabase LANZA cuando no hay filas, así que el
        `return None` de abajo era inalcanzable y un id inexistente daba 500 en vez de 404. Con
        el filtro de empresa eso se volvía la respuesta normal para toda área ajena.
        """
        q = supabase_admin.table(_TABLE).select(_SELECT).eq("id", id).eq("activo", True)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        res = q.maybe_single().execute()
        if not res or not res.data:
            return None
        return _to_response(res.data, _counts_by_area())

    def save(self, data: AreaCreate) -> AreaResponse:
        payload = data.model_dump(exclude_none=True)
        res = supabase_admin.table(_TABLE).insert(payload).execute()
        counts = _counts_by_area()
        return _to_response(res.data[0], counts)

    def update(self, id: str, data: AreaUpdate, empresa_id: Optional[str] = None) -> Optional[AreaResponse]:
        """Actualización parcial. empresa_id restringe el WHERE (None = consolidado)."""
        patch = data.model_dump(exclude_none=True)
        if not patch:
            return self.find_by_id(id, empresa_id)
        q = supabase_admin.table(_TABLE).update(patch).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        res = q.execute()
        if not res.data:
            return None
        counts = _counts_by_area()
        return _to_response(res.data[0], counts)

    def delete(self, id: str, empresa_id: Optional[str] = None) -> bool:
        """Soft delete (activo=False). empresa_id restringe el WHERE (None = consolidado)."""
        q = supabase_admin.table(_TABLE).update({"activo": False}).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        return bool(q.execute().data)
