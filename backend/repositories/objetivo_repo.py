"""Repositorio de objetivos. Acceso a Supabase con supabase_admin.

Enriquecido en _objetivo_row.py, jerarquía en _objetivos_arbol.py, puente de responsables en
_objetivo_responsables.py y el armado de la query del listado (orden + filtros + el predicado de
empresa) en _objetivo_filtros.py: los cuatro salieron de acá por límite de líneas.

🔴 `supabase_admin.table(...)` se queda ACÁ, en el repo, y los satélites reciben la query ya
construida. El motivo está en el encabezado de _objetivo_filtros: el espía de los tests parchea
`supabase_admin` módulo por módulo, y un satélite que importara el cliente por su cuenta se
saltearía el parcheo y pegaría a la red de verdad.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._objetivo_filtros import aplicar_filtros, aplicar_orden, con_empresa
from repositories._objetivo_responsables import set_responsables, sincronizar_desde_update
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
        orden y los cuatro filtros los arma `_objetivo_filtros`; acá quedan la ida a la base y el
        anidado, que lo hace `_objetivos_arbol.armar_arbol`.
        """
        q = aplicar_orden(supabase_admin.table(_T).select("*"))
        q = aplicar_filtros(q, empresa_id, estado, responsable_id, prioridad)
        return armar_arbol(_build(q.execute().data or []))

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        q = con_empresa(supabase_admin.table(_T).select("*").eq("id", id), empresa_id)
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
            con_empresa(supabase_admin.table(_T).update(patch).eq("id", id), empresa_id).execute()
        return self.find_by_id(id, empresa_id)

    def set_estado(self, id: str, estado: str, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        """Actualiza solo el estado (alimenta el movimiento kanban)."""
        q = supabase_admin.table(_T).update({"estado": estado}).eq("id", id)
        con_empresa(q, empresa_id).execute()
        return self.find_by_id(id, empresa_id)

    def tiene_hijos(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        """¿El objetivo tiene subobjetivos? Ver _objetivos_arbol.tiene_hijos."""
        return _tiene_hijos(id, empresa_id)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        q = con_empresa(supabase_admin.table(_T).delete().eq("id", id), empresa_id)
        return bool(q.execute().data)
