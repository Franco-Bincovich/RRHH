"""Repositorio de vacaciones. Acceso a Supabase con supabase_admin."""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._rango_fechas import aplicar_rango
from repositories._vacaciones_empleado_repo import datos_para_saldo, empresa_de_empleado
from repositories._vacaciones_utils import TABLE, aplicar_filtro_estado, build_responses
from repositories._vacaciones_write_repo import actualizar, cancelar, guardar
from schemas.vacaciones import SolicitudVacacionesResponse

_T = TABLE


class VacacionesRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_ids: Optional[List[str]] = None, page: int = 1, page_size: int = 20, estado: Optional[str] = None, today: Optional[date] = None, *, desde: Optional[date] = None, hasta: Optional[date] = None) -> Tuple[List[SolicitudVacacionesResponse], int]:
        """Retorna (página filtrada por empresa/empleado_ids/estado si se proveen, total real del filtro).
        empleado_ids=None → sin filtro por empleado; la intersección ownership∩área la arma el service.
        estado → filtro server-side (el total refleja el estado, para paginar y exportar bien).
        desde/hasta → SOLAPAMIENTO con el rango, keyword-only (semántica en _rango_fechas)."""
        # `.order("id")` = desempate. `fecha_desde` sola NO es un orden total (varias solicitudes
        # arrancan el mismo día) y entre empatadas Postgres no garantiza el mismo orden en dos
        # consultas con OFFSET distinto: una fila puede salir en dos páginas o en ninguna.
        # El `id` va ASC aunque la fecha vaya DESC — es la forma del índice de la migración 118.
        q = supabase_admin.table(_T).select("*", count="exact").order("fecha_desde", desc=True).order("id")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_ids is not None:
            q = q.in_("empleado_id", empleado_ids)
        q = aplicar_filtro_estado(q, estado, today)
        q = aplicar_rango(q, desde, hasta)
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

    # ── Lookups sobre `empleados` (delegados a _vacaciones_empleado_repo) ──

    def find_empresa_for_empleado(self, empleado_id: str) -> Optional[str]:
        """La empresa del empleado. Delegado a _vacaciones_empleado_repo."""
        return empresa_de_empleado(empleado_id)

    def find_datos_para_saldo(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> Optional[dict]:
        """Los tres campos del cálculo de saldo. Delegado a _vacaciones_empleado_repo."""
        return datos_para_saldo(empleado_id, empresa_id)

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
        periodo: Optional[int] = None, dias_liquidados: int = 0,
    ) -> SolicitudVacacionesResponse:
        """Inserta una solicitud y devuelve el registro enriquecido (ver _vacaciones_write_repo)."""
        return guardar(empleado_id, empresa_id, fecha_desde, fecha_hasta, dias, tipo,
                       comentario, self.find_by_id, periodo, dias_liquidados)

    def update(self, id: str, patch: dict, empresa_id: Optional[UUID] = None) -> Optional[SolicitudVacacionesResponse]:
        """Edita la solicitud con la empresa en el WHERE (ver _vacaciones_write_repo)."""
        return actualizar(id, patch, empresa_id, self.find_by_id)

    def cancel(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[SolicitudVacacionesResponse]:
        """Setea cancelada=True, restringiendo por empresa si se provee (ver _vacaciones_write_repo)."""
        return cancelar(id, empresa_id, self.find_by_id)
