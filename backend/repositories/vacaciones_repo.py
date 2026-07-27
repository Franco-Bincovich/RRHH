"""Repositorio de vacaciones. Acceso a Supabase con supabase_admin."""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._vacaciones_utils import aplicar_filtro_estado, build_responses
from schemas.vacaciones import SolicitudVacacionesResponse
from utils.errors import AppError
from utils.logger import logger

_T = "solicitudes_vacaciones"


class VacacionesRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_ids: Optional[List[str]] = None, page: int = 1, page_size: int = 20, estado: Optional[str] = None, today: Optional[date] = None) -> Tuple[List[SolicitudVacacionesResponse], int]:
        """Retorna (página filtrada por empresa/empleado_ids/estado si se proveen, total real del filtro).
        empleado_ids=None → sin filtro por empleado; la intersección ownership∩área la arma el service.
        estado → filtro server-side (el total refleja el estado, para paginar y exportar bien)."""
        q = supabase_admin.table(_T).select("*", count="exact").order("fecha_desde", desc=True)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_ids is not None:
            q = q.in_("empleado_id", empleado_ids)
        q = aplicar_filtro_estado(q, estado, today)
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return build_responses(res.data or []), res.count or 0

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[SolicitudVacacionesResponse]:
        """Busca por UUID. Si empresa_id se provee, valida pertenencia."""
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return build_responses([res.data])[0] if res.data else None

    def find_overlapping(
        self, empleado_id: str, fecha_desde: date, fecha_hasta: date,
        tipo: str, exclude_id: Optional[str] = None,
    ) -> List[dict]:
        """Solicitudes no canceladas del mismo empleado y tipo que solapan el rango.
        Tipos distintos pueden coexistir en las mismas fechas — no se cruzan."""
        q = (
            supabase_admin.table(_T).select("id")
            .eq("empleado_id", empleado_id).eq("cancelada", False).eq("tipo", tipo)
            .lte("fecha_desde", str(fecha_hasta)).gte("fecha_hasta", str(fecha_desde))
        )
        if exclude_id:
            q = q.neq("id", exclude_id)
        return q.execute().data or []

    def find_empresa_for_empleado(self, empleado_id: str) -> Optional[str]:
        """Retorna el empresa_id del empleado, o None si no existe."""
        res = supabase_admin.table("empleados").select("empresa_id").eq("id", empleado_id).maybe_single().execute()
        return str(res.data["empresa_id"]) if res.data else None

    def find_dias_asignados(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> Optional[int]:
        """dias_vacaciones_asignados del empleado, o None si no existe o es de otra empresa
        (empresa_id None = consolidado, no restringe)."""
        q = supabase_admin.table("empleados").select("dias_vacaciones_asignados").eq("id", empleado_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return res.data["dias_vacaciones_asignados"] if res.data else None

    def find_vacaciones_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> List[SolicitudVacacionesResponse]:
        """Solicitudes tipo='vacaciones' no canceladas del empleado (para cálculo de saldo).
        Si empresa_id se provee, restringe a esa empresa (None = consolidado)."""
        q = (supabase_admin.table(_T).select("*")
             .eq("empleado_id", empleado_id).eq("tipo", "vacaciones").eq("cancelada", False))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return build_responses(q.execute().data or [])

    def save(
        self, empleado_id: str, empresa_id: str, fecha_desde: date, fecha_hasta: date,
        dias: int, tipo: str, comentario: Optional[str],
    ) -> SolicitudVacacionesResponse:
        """Inserta una solicitud y devuelve el registro enriquecido."""
        payload = {
            "empleado_id": empleado_id, "empresa_id": empresa_id,
            "fecha_desde": str(fecha_desde), "fecha_hasta": str(fecha_hasta),
            "dias": dias, "tipo": tipo, "comentario": comentario, "cancelada": False,
        }
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            logger.error("Supabase insert vacío en solicitudes_vacaciones")
            raise AppError("Error al registrar vacaciones", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def cancel(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[SolicitudVacacionesResponse]:
        """Setea cancelada=True. Si empresa_id se provee, restringe el WHERE por empresa."""
        q = supabase_admin.table(_T).update({"cancelada": True}).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return self.find_by_id(id, empresa_id) if res.data else None
