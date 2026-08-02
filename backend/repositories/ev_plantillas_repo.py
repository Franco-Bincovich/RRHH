"""Repositorio de plantillas y criterios de evaluación de desempeño.

Los mappers de fila y el enriquecimiento por lotes viven en `_ev_plantillas_row.py` (el repo
estaba en 129 líneas contra el límite de 100). Acá quedan solo las queries.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._ev_plantillas_row import crit, enrich
from schemas.evaluaciones import (
    CriterioCreate, CriterioResponse, PlantillaCreate, PlantillaResponse,
)
from utils.errors import AppError

_TP, _TC = "ev_plantillas", "ev_criterios"




class EvPlantillasRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, solo_activas: bool = True) -> List[PlantillaResponse]:
        """Retorna plantillas con sus criterios, filtradas por empresa."""
        q = supabase_admin.table(_TP).select(f"*, {_TC}(*)").order("nombre")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if solo_activas:
            q = q.eq("activa", True)
        return enrich(q.execute().data or [])

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[PlantillaResponse]:
        q = supabase_admin.table(_TP).select(f"*, {_TC}(*)").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return enrich([res.data])[0] if res and res.data else None

    def save(self, data: PlantillaCreate) -> PlantillaResponse:
        """Inserta plantilla y retorna el registro enriquecido."""
        payload = {k: v for k, v in {
            "empresa_id": str(data.empresa_id), "nombre": data.nombre.strip(),
            "descripcion": data.descripcion, "tipo_escala": data.tipo_escala,
            "escala_min": data.escala_min, "escala_max": data.escala_max,
            "opciones_cualitativas": data.opciones_cualitativas,
            "area_id": str(data.area_id) if data.area_id else None,
        }.items() if v is not None}
        res = supabase_admin.table(_TP).insert(payload).execute()
        if not res.data:
            raise AppError("Error al crear la plantilla", "DB_ERROR", 500)
        return self.find_by_id(res.data[0]["id"])  # type: ignore[return-value]

    def update(self, id: str, empresa_id: Optional[UUID], payload: dict) -> Optional[PlantillaResponse]:
        if payload:
            q = supabase_admin.table(_TP).update(payload).eq("id", id)
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            q.execute()
        return self.find_by_id(id, empresa_id)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = supabase_admin.table(_TP).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)

    def has_ciclos(self, id: str) -> bool:
        res = supabase_admin.table("ev_ciclos").select("id").eq("plantilla_id", id).limit(1).execute()
        return bool(res.data)

    # ── Criterios ─────────────────────────────────────────────────────────────

    def find_criterios(self, plantilla_id: str) -> List[CriterioResponse]:
        rows = supabase_admin.table(_TC).select("*").eq("plantilla_id", plantilla_id).order("orden").execute().data or []
        return [crit(r) for r in rows]

    def add_criterio(self, plantilla_id: str, empresa_id: str, data: CriterioCreate) -> CriterioResponse:
        res = supabase_admin.table(_TC).insert({
            "plantilla_id": plantilla_id, "empresa_id": empresa_id,
            "nombre": data.nombre.strip(), "descripcion": data.descripcion,
            "peso": data.peso, "orden": data.orden,
        }).execute()
        if not res.data:
            raise AppError("Error al crear el criterio", "DB_ERROR", 500)
        return crit(res.data[0])

    def update_criterio(self, criterio_id: str, empresa_id: str, payload: dict) -> Optional[CriterioResponse]:
        if payload:
            supabase_admin.table(_TC).update(payload).eq("id", criterio_id).eq("empresa_id", empresa_id).execute()
        res = supabase_admin.table(_TC).select("*").eq("id", criterio_id).maybe_single().execute()
        return crit(res.data) if res and res.data else None

    def delete_criterio(self, criterio_id: str, empresa_id: str) -> bool:
        return bool(supabase_admin.table(_TC).delete().eq("id", criterio_id).eq("empresa_id", empresa_id).execute().data)
