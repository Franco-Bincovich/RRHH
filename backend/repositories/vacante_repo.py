"""
Repositorio de vacantes. Acceso a Supabase con supabase_admin.
Interfaz: find_all · find_by_id · save · update · update_estado · save_linkedin_data
Todas las operaciones de lectura/escritura reciben empresa_id opcional (multiempresa).

El SELECT con joins (`_JOIN`) y el mapper (`_vrow`) viven en `repositories/_vacante_row.py`.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._vacante_row import _JOIN, _vrow
from schemas.vacante import VacanteCreate, VacanteResponse, VacanteUpdate
from utils.errors import AppError
from utils.logger import logger

_V = "vacantes"


class VacanteRepo:
    def find_all(self, estado: Optional[str] = None, empresa_id: Optional[UUID] = None) -> List[VacanteResponse]:
        """Retorna vacantes ordenadas por fecha desc, con filtros opcionales de estado y empresa."""
        q = supabase_admin.table(_V).select(_JOIN).order("created_at", desc=True)
        if estado:
            q = q.eq("estado", estado)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_vrow(r) for r in (q.execute().data or [])]

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
        return _vrow(res.data) if res.data else None

    def find_by_codigo(self, codigo: str) -> Optional[VacanteResponse]:
        """Busca vacante por su código (`VAC-0001`). CASE-INSENSITIVE. None si no existe.

        `ilike` y no `eq`: el código llega del ASUNTO DE UN MAIL escrito por un candidato, así
        que `[vac-0001]` tiene que resolver igual que `[VAC-0001]`. Con `eq` ese fallo no da
        error — manda el CV a "sin asignar" sin motivo visible. Sin comodines es igualdad exacta
        (el CHECK de formato solo admite `VAC-` + dígitos, así que `%`/`_` no pueden aparecer).
        🔴 NO RECIBE `empresa_id`, Y NO ES UN OLVIDO: el código es ÚNICO EN TODO EL SISTEMA
        (mig 097): la casilla es una sola y quien manda el mail no aporta empresa. La empresa se
        DERIVA de la vacante encontrada — Vista vs Acción."""
        res = supabase_admin.table(_V).select(_JOIN).ilike("codigo", codigo).maybe_single().execute()
        return _vrow(res.data) if res and res.data else None

    def save(self, data: VacanteCreate) -> VacanteResponse:
        """Inserta una vacante con estado='nueva' y devuelve el registro con joins."""
        payload = data.model_dump()
        payload["area_id"] = str(payload["area_id"])
        payload["empresa_id"] = str(payload["empresa_id"])
        payload["estado"] = "nueva"
        res = supabase_admin.table(_V).insert(payload).execute()
        if not res.data:
            logger.error("Supabase insert vacío en vacantes")
            raise AppError("Error al crear vacante", "DB_ERROR", 500)
        return self.find_by_id(str(res.data[0]["id"]))  # type: ignore[return-value]

    def update(self, id: str, data: VacanteUpdate, empresa_id: Optional[UUID] = None) -> Optional[VacanteResponse]:
        """Actualiza campos no-None. Si empresa_id se provee, restringe el WHERE."""
        patch = data.model_dump(exclude_none=True)
        if not patch:
            return self.find_by_id(id, empresa_id)
        if "area_id" in patch:
            patch["area_id"] = str(patch["area_id"])
        q = supabase_admin.table(_V).update(patch).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return self.find_by_id(id, empresa_id) if res.data else None

    def update_estado(self, id: str, estado: str) -> Optional[VacanteResponse]:
        """Actualiza el estado de una vacante (sin filtro de empresa — uso interno)."""
        res = supabase_admin.table(_V).update({"estado": estado}).eq("id", id).execute()
        return self.find_by_id(id) if res.data else None

    def save_linkedin_data(self, id: str, post_id: str, url: str, email_contacto: str) -> None:
        """Guarda los datos de publicación en LinkedIn en la vacante."""
        supabase_admin.table(_V).update(
            {"linkedin_post_id": post_id, "linkedin_url": url, "email_contacto": email_contacto}
        ).eq("id", id).execute()

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> None:
        """Borra FÍSICAMENTE la fila de la vacante (filtra por empresa si se provee).
        Los candidatos sobreviven por la FK ON DELETE SET NULL (migración 071)."""
        q = supabase_admin.table(_V).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        q.execute()
