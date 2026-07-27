"""Repositorio de ausencias. Acceso a Supabase con supabase_admin."""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._rango_fechas import aplicar_rango
from schemas.ausencias import AusenciaResponse
from utils.errors import AppError
from utils.logger import logger

_T, _TA = "solicitudes_ausencia", "tipos_ausencia"


def _q(table: str, cols: str, ids: list) -> list:
    return supabase_admin.table(table).select(cols).in_("id", ids).execute().data or []


def _build(rows: List[dict]) -> List[AusenciaResponse]:
    """Enriquece filas con empresa_nombre, empleado_nombre, area_nombre y tipo_nombre."""
    if not rows:
        return []
    empresa_map = {e["id"]: e["nombre"] for e in _q("empresas", "id, nombre", list({r["empresa_id"] for r in rows}))}
    emp_data = _q("empleados", "id, nombre, apellido, area_id", list({r["empleado_id"] for r in rows}))
    emp_map = {e["id"]: {"nombre": f"{e['nombre']} {e['apellido']}", "area_id": e.get("area_id")} for e in emp_data}
    area_ids = list({e["area_id"] for e in emp_data if e.get("area_id")})
    area_map = {a["id"]: a["nombre"] for a in (_q("areas", "id, nombre", area_ids) if area_ids else [])}
    tipo_map = {t["id"]: t["nombre"] for t in _q(_TA, "id, nombre", list({r["tipo_id"] for r in rows}))}
    result = []
    for r in rows:
        emp = emp_map.get(r["empleado_id"]) or {}
        aid = emp.get("area_id")
        result.append(AusenciaResponse.model_validate({
            **r,
            "empresa_nombre": empresa_map.get(r["empresa_id"]),
            "empleado_nombre": emp.get("nombre"),
            "area_id": aid,
            "area_nombre": area_map.get(aid) if aid else None,
            "tipo_nombre": tipo_map.get(r["tipo_id"]),
        }))
    return result


class AusenciasRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_ids: Optional[List[str]] = None, tipo_id: Optional[UUID] = None, page: int = 1, page_size: int = 20, *, desde: Optional[date] = None, hasta: Optional[date] = None) -> Tuple[List[AusenciaResponse], int]:
        """Retorna (página filtrada por empresa/empleado_ids/tipo, total real del filtro).
        empleado_ids=None → sin filtro por empleado; la intersección ownership∩área la arma el service.
        desde/hasta → SOLAPAMIENTO con el rango, keyword-only (semántica en _rango_fechas)."""
        q = supabase_admin.table(_T).select("*", count="exact").order("fecha_desde", desc=True)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_ids is not None:
            q = q.in_("empleado_id", empleado_ids)
        if tipo_id:
            q = q.eq("tipo_id", str(tipo_id))
        q = aplicar_rango(q, desde, hasta)
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return _build(res.data or []), res.count or 0

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[AusenciaResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if res.data else None

    def find_empresa_for_empleado(self, empleado_id: str) -> Optional[str]:
        """Retorna el empresa_id del empleado, o None si no existe."""
        res = supabase_admin.table("empleados").select("empresa_id").eq("id", empleado_id).maybe_single().execute()
        return str(res.data["empresa_id"]) if res.data else None

    def save(self, empleado_id: str, empresa_id: str, tipo_id: str, fecha_desde: date, fecha_hasta: date, dias: int, justificada: bool, motivo: Optional[str]) -> AusenciaResponse:
        """Inserta una ausencia y retorna el registro enriquecido."""
        res = supabase_admin.table(_T).insert({
            "empleado_id": empleado_id, "empresa_id": empresa_id, "tipo_id": tipo_id,
            "fecha_desde": str(fecha_desde), "fecha_hasta": str(fecha_hasta),
            "dias": dias, "justificada": justificada, "motivo": motivo,
        }).execute()
        if not res.data:
            logger.error("Supabase insert vacío en solicitudes_ausencia")
            raise AppError("Error al registrar la ausencia", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, empresa_id: Optional[UUID], payload: dict) -> Optional[AusenciaResponse]:
        if payload:
            q = supabase_admin.table(_T).update(payload).eq("id", id)
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            q.execute()
        return self.find_by_id(id, empresa_id)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = supabase_admin.table(_T).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)
