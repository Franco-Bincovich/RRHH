"""Repositorio de objetivos. Acceso a Supabase con supabase_admin.

Enriquecido en _objetivo_row.py, jerarquía en _objetivos_arbol.py y puente de responsables en
_objetivo_responsables.py: los tres salieron de acá por límite de líneas.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._objetivo_responsables import (
    aplicar_filtro_responsable, set_responsables, sincronizar_desde_update,
)
from repositories._objetivo_row import _build
from repositories._objetivos_arbol import armar_arbol, tiene_hijos as _tiene_hijos
from schemas.objetivo import ObjetivoCreate, ObjetivoResponse, ObjetivoUpdate
from utils.errors import AppError
from utils.logger import logger

_T = "objetivos"


class ObjetivoRepo:
    def find_all(
        self,
        empresa_id:     Optional[UUID] = None,
        estado:         Optional[str]  = None,
        responsable_id: Optional[str]  = None,
        prioridad:      Optional[str]  = None,
    ) -> List[ObjetivoResponse]:
        """Árbol de objetivos con filtros opcionales.

        RAÍCES por fecha_entrega ascendente (nulos al final) con sus hijos anidados debajo. El
        orden sigue viniendo de la query; el anidado lo arma `_objetivos_arbol.armar_arbol`.
        El filtro por responsable mira la puente Y la columna de dueño.
        """
        q = supabase_admin.table(_T).select("*").order("fecha_entrega", desc=False)
        if empresa_id:     q = q.eq("empresa_id",     str(empresa_id))
        if estado:         q = q.eq("estado",         estado)
        if prioridad:      q = q.eq("prioridad",      prioridad)
        if responsable_id: q = aplicar_filtro_responsable(q, responsable_id)
        return armar_arbol(_build(q.execute().data or []))

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _build([res.data])[0] if res.data else None

    def save(self, data: ObjetivoCreate) -> ObjetivoResponse:
        """Inserta un objetivo y retorna el registro enriquecido."""
        payload: dict = {
            "empresa_id":     str(data.empresa_id),
            "responsable_id": str(data.responsable_id),
            "titulo":         data.titulo.strip(),
            "prioridad":      data.prioridad,
        }
        if data.descripcion:   payload["descripcion"]   = data.descripcion
        if data.fecha_entrega: payload["fecha_entrega"] = str(data.fecha_entrega)
        if data.parent_id:     payload["parent_id"]     = str(data.parent_id)
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            logger.error("Supabase insert vacío en objetivos")
            raise AppError("Error al crear el objetivo", "DB_ERROR", 500)
        nuevo_id = str(res.data[0]["id"])
        set_responsables(nuevo_id, [str(u) for u in (data.responsables or [])],
                         str(data.responsable_id))
        return self.find_by_id(nuevo_id)  # type: ignore[return-value]

    def update(self, id: str, data: ObjetivoUpdate, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        # 🔴 `responsables` NO es columna de `objetivos`: va a la puente. En el patch, el UPDATE
        # fallaría con "column does not exist" y el fake de Supabase no lo podría desmentir.
        patch = {k: (str(v) if k in ("responsable_id", "parent_id", "fecha_entrega") else v)
                 for k, v in data.model_dump(exclude_none=True).items() if k != "responsables"}
        if data.responsables is not None:
            sincronizar_desde_update(self, id, data, empresa_id)
        if patch:
            q = supabase_admin.table(_T).update(patch).eq("id", id)
            if empresa_id:
                q = q.eq("empresa_id", str(empresa_id))
            q.execute()
        return self.find_by_id(id, empresa_id)

    def set_estado(self, id: str, estado: str, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        """Actualiza solo el estado (alimenta el movimiento kanban)."""
        q = supabase_admin.table(_T).update({"estado": estado}).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        q.execute()
        return self.find_by_id(id, empresa_id)

    def tiene_hijos(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        """¿El objetivo tiene subobjetivos? Ver _objetivos_arbol.tiene_hijos."""
        return _tiene_hijos(id, empresa_id)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = supabase_admin.table(_T).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return bool(q.execute().data)
