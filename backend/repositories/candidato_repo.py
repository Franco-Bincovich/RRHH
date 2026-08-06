"""
Repositorio de candidatos. Acceso a Supabase con supabase_admin.
Interfaz pública: find_candidatos · find_all_candidatos · save_candidato · update_etapa_candidato
Todas las operaciones reciben empresa_id opcional para filtrado multiempresa.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.vacante import CandidatoCreate, CandidatoResponse
from utils.errors import AppError
from utils.logger import logger

_C = "candidatos"


def _crow(r: dict) -> CandidatoResponse:
    vid = r.get("vacante_id")
    emp = r.get("empresa_id")
    return CandidatoResponse(
        id=str(r["id"]), vacante_id=str(vid) if vid else None,
        # El `select("*")` ya la traía; el mapper la descartaba. La necesita el evento de
        # auditoría de la baja (empresa DEL REGISTRO, no del header).
        empresa_id=str(emp) if emp else None,
        nombre=r["nombre"], apellido=r["apellido"], email=r["email"],
        telefono=r.get("telefono"),
        cargo_anterior=r.get("cargo_anterior"), empresa_anterior=r.get("empresa_anterior"),
        etapa_pipeline=r.get("etapa", "postulado"), score_ia=r.get("score_ia"),
        busqueda_congelada=r.get("busqueda_congelada"),
        cv_storage_path=r.get("cv_storage_path"),
        created_at=r["created_at"],
    )


class CandidatoRepo:
    def find_candidatos(self, vacante_id: str, empresa_id: Optional[UUID] = None) -> List[CandidatoResponse]:
        """Retorna candidatos de una vacante, filtrados por empresa si se provee."""
        q = supabase_admin.table(_C).select("*").eq("vacante_id", vacante_id).order("created_at")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_crow(r) for r in (q.execute().data or [])]

    def find_all_candidatos(self, empresa_id: Optional[UUID] = None) -> List[CandidatoResponse]:
        """Retorna TODOS los candidatos de la empresa (con y sin vacante_id), más recientes primero.
        NO filtra por vacante_id: incluye los huérfanos de búsquedas borradas."""
        q = supabase_admin.table(_C).select("*").order("created_at", desc=True)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_crow(r) for r in (q.execute().data or [])]

    def find_by_id(self, candidato_id: str, empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
        """Busca un candidato por UUID. Si empresa_id se provee, valida pertenencia (fail-closed)."""
        q = supabase_admin.table(_C).select("*").eq("id", candidato_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _crow(res.data) if res and res.data else None

    def save_candidato(self, vacante_id: str, data: CandidatoCreate, empresa_id: str) -> CandidatoResponse:
        """Inserta un candidato con el empresa_id heredado de su vacante."""
        payload = data.model_dump(exclude_none=True)
        payload["vacante_id"] = vacante_id
        payload["empresa_id"] = empresa_id
        payload["etapa"] = "postulado"
        res = supabase_admin.table(_C).insert(payload).execute()
        if not res.data:
            logger.error("Supabase insert vacío en candidatos")
            raise AppError("Error al crear candidato", "DB_ERROR", 500)
        return _crow(res.data[0])

    def set_cv(self, candidato_id: str, cv_storage_path: str) -> None:
        """Guarda el storage_path del CV en la fila del candidato (bucket privado 'cvs')."""
        supabase_admin.table(_C).update({"cv_storage_path": cv_storage_path}).eq("id", candidato_id).execute()

    def update_etapa_candidato(self, candidato_id: str, etapa: str, empresa_id: Optional[UUID] = None) -> Optional[CandidatoResponse]:
        """Actualiza la etapa del pipeline de un candidato."""
        q = supabase_admin.table(_C).update({"etapa": etapa}).eq("id", candidato_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return _crow(res.data[0]) if res.data else None

    def delete(self, candidato_id: str, empresa_id: Optional[UUID] = None) -> None:
        """Borra FÍSICAMENTE la fila del candidato (filtra por empresa si se provee, fail-closed)."""
        q = supabase_admin.table(_C).delete().eq("id", candidato_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        q.execute()

    def congelar_busqueda(self, vacante_id: str, texto: str, empresa_id: Optional[UUID] = None) -> None:
        """Graba busqueda_congelada en todos los candidatos de una vacante (antes de borrarla)."""
        q = supabase_admin.table(_C).update({"busqueda_congelada": texto}).eq("vacante_id", vacante_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        q.execute()
