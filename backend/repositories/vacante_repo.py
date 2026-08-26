"""
Repositorio de vacantes. Acceso a Supabase con supabase_admin.
Interfaz: find_all · find_by_id · save · update · update_estado · save_linkedin_data
El write path vive en `_vacante_write_repo.py` (este archivo estaba en 100/100).
Todas las operaciones de lectura/escritura reciben empresa_id opcional (multiempresa).

El SELECT con joins (`_JOIN`) y el mapper (`_vrow`) viven en `repositories/_vacante_row.py`.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._vacante_row import _JOIN, _vrow
from repositories._vacante_write_repo import (
    actualizar, borrar, cambiar_estado, guardar, guardar_linkedin,
)
from schemas.vacante import VacanteCreate, VacanteResponse, VacanteUpdate
from utils.logger import logger

_V = "vacantes"


class VacanteRepo:
    def find_all(self, estado: Optional[str] = None, empresa_id: Optional[UUID] = None,
                 page: int = 1, page_size: int = 20) -> Tuple[List[VacanteResponse], int]:
        """Pagina de vacantes (mas recientes primero) + el total REAL del filtro.

        `.order("id")` = desempate: varias vacantes de una misma busqueda se crean en el mismo
        lote y comparten `created_at`. ASC aunque la fecha vaya DESC — es la forma de
        `idx_vacantes_empresa_created` (migracion 118).
        """
        q = (supabase_admin.table(_V).select(_JOIN, count="exact")
             .order("created_at", desc=True).order("id"))
        if estado:
            q = q.eq("estado", estado)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        return [_vrow(r) for r in (res.data or [])], (res.count or 0)

    def find_by_ids(self, ids: List[str]) -> List[VacanteResponse]:
        """Trae varias vacantes por id en UNA query (evita N+1 al resolver grupos de candidatos)."""
        if not ids:
            return []
        res = supabase_admin.table(_V).select(_JOIN).in_("id", ids).execute()
        return [_vrow(r) for r in (res.data or [])]

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[VacanteResponse]:
        """Busca vacante por UUID. Si empresa_id se provee, valida pertenencia."""
        q = supabase_admin.table(_V).select(_JOIN).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _vrow(res.data) if (res and res.data) else None

    def find_by_codigo(self, codigo: str) -> Optional[VacanteResponse]:
        """Busca vacante por su código (`ECO-2026`). CASE-INSENSITIVE. None si no existe.

        `ilike` y no `eq`: el código llega del ASUNTO DE UN MAIL escrito por un candidato, así
        que `[eco-2026]` tiene que resolver igual que `[ECO-2026]`. Con `eq` ese fallo no da
        error — manda el CV a "sin asignar" sin motivo visible. Sin comodines es igualdad exacta,
        y el CHECK de la 122 deja `%`/`_` afuera del formato JUSTO por esto: un código con `%`
        haría que esto devuelva varias filas, y `maybe_single()` sobre varias es un 500.
        🔴 NO RECIBE `empresa_id`, Y NO ES UN OLVIDO: el código es ÚNICO EN TODO EL SISTEMA
        (mig 097): la casilla es una sola y quien manda el mail no aporta empresa. La empresa se
        DERIVA de la vacante encontrada — Vista vs Acción."""
        res = supabase_admin.table(_V).select(_JOIN).ilike("codigo", codigo).maybe_single().execute()
        return _vrow(res.data) if res and res.data else None

    def codigos(self) -> List[str]:
        """TODOS los códigos del sistema, para que el matcher sepa qué buscar (mig 122: el código
        ya no tiene forma que adivinar). UNA query por CORRIDA, no por mail — `codigos_en` los
        recibe como parámetro obligatorio para que ese viaje no se esconda adentro del loop. Sin
        `empresa_id` por lo mismo que `find_by_codigo`. Solo la columna: con `_JOIN` esto sería
        el listado entero con sus embeds."""
        res = supabase_admin.table(_V).select("codigo").execute()
        return [r["codigo"] for r in (res.data or []) if r.get("codigo")]

    # ── Escrituras (delegadas a _vacante_write_repo) ──

    def save(self, data: VacanteCreate) -> VacanteResponse:
        """Alta de vacante. Delegado a _vacante_write_repo.guardar."""
        return guardar(data, self.find_by_id)

    def update(self, id: str, data: VacanteUpdate, empresa_id: Optional[UUID] = None) -> Optional[VacanteResponse]:
        """Actualizacion parcial. Delegado a _vacante_write_repo.actualizar."""
        return actualizar(id, data, empresa_id, self.find_by_id)

    def update_estado(self, id: str, estado: str) -> Optional[VacanteResponse]:
        """Cambio de estado. Delegado a _vacante_write_repo.cambiar_estado."""
        return cambiar_estado(id, estado, self.find_by_id)

    def save_linkedin_data(self, id: str, post_id: str, url: str, email_contacto: str) -> None:
        """Datos de publicacion en LinkedIn. Delegado a _vacante_write_repo.guardar_linkedin."""
        guardar_linkedin(id, post_id, url, email_contacto)

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> None:
        """Baja FISICA. Delegado a _vacante_write_repo.borrar."""
        borrar(id, empresa_id)
