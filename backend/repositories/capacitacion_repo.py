"""Repositorio de catálogo de capacitaciones. Acceso a Supabase con supabase_admin.

El enriquecido (`_build`) vive en `_capacitacion_row` (molde `_asignacion_row`): este archivo
estaba en 98/100 y las tres columnas de la migración 116 no entraban en el `save()`.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._capacitacion_row import _build
from schemas.capacitacion import CapacitacionCreate, CapacitacionResponse
from utils.errors import AppError
from utils.logger import logger

_T = "capacitaciones"


class CapacitacionRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, solo_activos: bool = True) -> List[CapacitacionResponse]:
        """Retorna capacitaciones ordenadas por nombre, filtradas por empresa y/o solo activas."""
        q = supabase_admin.table(_T).select("*").order("nombre")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if solo_activos:
            q = q.eq("activo", True)
        return _build(q.execute().data or [])

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[CapacitacionResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if (res and res.data) else None

    def save(self, data: CapacitacionCreate) -> CapacitacionResponse:
        """Inserta una capacitación y retorna el registro enriquecido."""
        res = supabase_admin.table(_T).insert({
            "empresa_id": str(data.empresa_id),
            "nombre": data.nombre.strip(),
            "descripcion": data.descripcion,
            "categoria": data.categoria,
            "duracion_horas": data.duracion_horas,
            "entidad_capacitadora": data.entidad_capacitadora,
            "modalidad": data.modalidad,
            "tipo": data.tipo,
            "obligatoria": data.obligatoria,
        }).execute()
        if not res.data:
            logger.error("Supabase insert vacío en capacitaciones")
            raise AppError("Error al crear la capacitación", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, empresa_id: Optional[UUID], payload: dict) -> Optional[CapacitacionResponse]:
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

    def set_activo(self, id: str, empresa_id: Optional[UUID], activo: bool) -> bool:
        q = supabase_admin.table(_T).update({"activo": activo}).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)

    def has_asignaciones(self, id: str) -> bool:
        """Retorna True si hay al menos una asignación para esta capacitación."""
        res = supabase_admin.table("empleado_capacitacion").select("id").eq("capacitacion_id", id).limit(1).execute()
        return bool(res.data)

    def find_empresa_for(self, id: str, empresa_id: Optional[str] = None) -> Optional[str]:
        """
        Retorna el empresa_id de la capacitación, o None si no existe.

        Con `empresa_id`, el filtro va EN EL WHERE (Forma A) y devuelve None también cuando la
        capacitación existe pero es de OTRA empresa: el caller no puede distinguir los dos casos
        aunque quiera. Es lo que permite que el service responda un 404 único en vez del
        EMPRESA_MISMATCH (422) que confirmaba la existencia del recurso ajeno.
        """
        q = supabase_admin.table(_T).select("empresa_id").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", empresa_id)
        res = q.maybe_single().execute()
        return str(res.data["empresa_id"]) if (res and res.data) else None
