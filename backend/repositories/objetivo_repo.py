"""Repositorio de objetivos. Acceso a Supabase con supabase_admin.

Enriquecido en _objetivo_row.py, jerarquía en _objetivos_arbol.py, puente de responsables en
_objetivo_responsables.py, el armado de la query del listado (orden + filtros + el predicado de
empresa) en _objetivo_filtros.py y la traducción schema → columnas en _objetivo_payload.py: los
cinco salieron de acá por límite de líneas.

🔴 `supabase_admin.table(...)` se queda ACÁ, en el repo, y los satélites reciben la query ya
construida. El motivo está en el encabezado de _objetivo_filtros: el espía de los tests parchea
`supabase_admin` módulo por módulo, y un satélite que importara el cliente por su cuenta se
saltearía el parcheo y pegaría a la red de verdad.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._objetivo_filtros import aplicar_filtros, aplicar_orden, con_empresa
from repositories._objetivo_payload import patch_edicion, payload_alta
from repositories._objetivo_responsables import set_responsables, sincronizar_desde_update
from repositories._objetivo_row import _build
from repositories._objetivos_arbol import armar_arbol, tiene_hijos as _tiene_hijos
from schemas.objetivo import ObjetivoCreate, ObjetivoResponse, ObjetivoUpdate
from schemas.objetivo_filtros import SIN_FILTROS, ObjetivosFiltros
from utils.errors import AppError
from utils.logger import logger

_T = "objetivos"


class ObjetivoRepo:
    def find_all(self, empresa_id: Optional[UUID] = None,
                 filtros: ObjetivosFiltros = SIN_FILTROS) -> List[ObjetivoResponse]:
        """Árbol de objetivos con filtros opcionales.

        RAÍCES por fecha_entrega ascendente (nulos al final) con sus hijos anidados debajo. El
        orden y los seis filtros los arma `_objetivo_filtros`; acá quedan la ida a la base y el
        anidado, que lo hace `_objetivos_arbol.armar_arbol`.

        🔴 LOS FILTROS VIAJAN EN UN OBJETO Y `empresa_id` NO. Con los tres de la migración 119
        esta firma habría tenido SIETE `Optional[str]` seguidos, que es el corrimiento silencioso
        de argumentos del bloque B. `empresa_id` queda suelto a propósito: es la barrera
        multiempresa, no un filtro de pantalla, y explícito no se puede perder pasando un objeto
        vacío. El razonamiento completo está en `schemas/objetivo_filtros.py`.
        """
        q = aplicar_orden(supabase_admin.table(_T).select("*"))
        q = aplicar_filtros(q, empresa_id, filtros)
        return armar_arbol(_build(q.execute().data or []))

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        q = con_empresa(supabase_admin.table(_T).select("*").eq("id", id), empresa_id)
        res = q.maybe_single().execute()
        return _build([res.data])[0] if (res and res.data) else None

    def save(self, data: ObjetivoCreate) -> ObjetivoResponse:
        """Inserta un objetivo y retorna el registro enriquecido.

        🔴 El 23505 del índice único NO se traduce acá. Lo hace el service, con
        `_objetivos_validaciones.duplicado_a_409`, porque el mismo choque puede venir del alta y
        de la edición y la respuesta tiene que ser la misma. Ver ese módulo.
        """
        res = supabase_admin.table(_T).insert(payload_alta(data)).execute()
        if not res.data:
            logger.error("Supabase insert vacío en objetivos")
            raise AppError("Error al crear el objetivo", "DB_ERROR", 500)
        nuevo_id = str(res.data[0]["id"])
        set_responsables(nuevo_id, [str(u) for u in (data.responsables or [])],
                         str(data.responsable_id))
        return self.find_by_id(nuevo_id)  # type: ignore[return-value]

    def update(self, id: str, data: ObjetivoUpdate, empresa_id: Optional[UUID] = None) -> Optional[ObjetivoResponse]:
        patch = patch_edicion(data)
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
