"""Repositorio de ausencias. Acceso a Supabase con supabase_admin."""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._ausencia_row import _build
from repositories._rango_fechas import aplicar_rango
from schemas.ausencias import AusenciaResponse
from utils.errors import AppError
from utils.logger import logger

# `_TA` (tipos_ausencia) se fue a `_ausencia_row.py`, que es su único consumidor. Acá quedaba
# como nombre suelto desde la división de la migración 088.
_T = "solicitudes_ausencia"


class AusenciasRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_ids: Optional[List[str]] = None, tipo_ids: Optional[List[str]] = None, page: int = 1, page_size: int = 20, *, desde: Optional[date] = None, hasta: Optional[date] = None) -> Tuple[List[AusenciaResponse], int]:
        """Retorna (página filtrada por empresa/empleado_ids/tipo, total real del filtro).
        empleado_ids=None → sin filtro por empleado; la intersección ownership∩área la arma el service.
        desde/hasta → SOLAPAMIENTO con el rango, keyword-only (semántica en _rango_fechas)."""
        # `.order("id")` = desempate, simetrico con vacaciones_repo (ver el porque ahi). `id` ASC
        # aunque la fecha vaya DESC: es la forma del indice `idx_sa_empresa_fecha` + mig 118.
        q = supabase_admin.table(_T).select("*", count="exact").order("fecha_desde", desc=True).order("id")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_ids is not None:
            q = q.in_("empleado_id", empleado_ids)
        if tipo_ids:
            # 🔴 `.in_()` y NO `.eq()`, desde la migración 088. Las ausencias apuntan a la HOJA,
            # nunca al padre: filtrar por un tipo padre con un `.eq` devolvería CERO filas, sin
            # error y sin aviso. La familia (el tipo + sus hijos) la resuelve el service, que es
            # el mismo punto por el que pasa el export — si se resolviera acá, el export estaría
            # bien igual, pero cualquier otro caller futuro del repo podría saltearlo.
            q = q.in_("tipo_id", [str(t) for t in tipo_ids])
        q = aplicar_rango(q, desde, hasta)
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return _build(res.data or []), res.count or 0

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[AusenciaResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if (res and res.data) else None

    def find_empresa_for_empleado(self, empleado_id: str) -> Optional[str]:
        """Retorna el empresa_id del empleado, o None si no existe."""
        res = supabase_admin.table("empleados").select("empresa_id").eq("id", empleado_id).maybe_single().execute()
        return str(res.data["empresa_id"]) if (res and res.data) else None

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
