"""
Servicio de lectura de candidatos para la sección Candidatos.
Resuelve el "nombre del grupo" de cada candidato: título vivo de su vacante, o el
nombre congelado si la búsqueda fue borrada (vacante_id NULL).
Flujo: router → service → repository.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories.candidato_repo import CandidatoRepo
from repositories.vacante_repo import VacanteRepo
from schemas.vacante import CandidatoGrupoResponse
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger

_CV_BUCKET = "cvs"


def _grupo_vivo(titulo: str, area_nombre: Optional[str]) -> str:
    """Arma 'Título — Área' de una vacante viva (omite el área si no existe)."""
    return f"{titulo} — {area_nombre}" if area_nombre else titulo


class CandidatoService:
    def __init__(
        self, candidato_repo: Optional[CandidatoRepo] = None, vacante_repo: Optional[VacanteRepo] = None,
        audit: Optional[AuditService] = None,
    ) -> None:
        self._candidato_repo = candidato_repo or CandidatoRepo()
        self._vacante_repo = vacante_repo or VacanteRepo()
        self._audit = audit or AuditService()

    def listar_todos_candidatos(self, empresa_id: Optional[UUID] = None) -> List[CandidatoGrupoResponse]:
        """
        Lista todos los candidatos de la empresa (con y sin vacante), resolviendo el nombre
        del grupo y si la búsqueda sigue activa.

        N+1 evitado: se juntan los vacante_id distintos y se traen las vacantes vivas en UNA
        sola query (find_by_ids); el resto se resuelve en memoria.

        Args:
            empresa_id: filtra por empresa. None = todas (vista consolidada).
        """
        candidatos = self._candidato_repo.find_all_candidatos(empresa_id)
        ids_vivos = {c.vacante_id for c in candidatos if c.vacante_id}
        titulos = {
            v.id: _grupo_vivo(v.titulo, v.area_nombre)
            for v in self._vacante_repo.find_by_ids(list(ids_vivos))
        }
        salida: List[CandidatoGrupoResponse] = []
        for c in candidatos:
            activa = bool(c.vacante_id) and c.vacante_id in titulos
            grupo = titulos.get(c.vacante_id) if activa else c.busqueda_congelada
            salida.append(
                CandidatoGrupoResponse(**c.model_dump(), grupo_nombre=grupo, busqueda_activa=activa)
            )
        return salida

    def cv_signed_url(self, candidato_id: str, empresa_id: Optional[UUID] = None) -> str:
        """Signed URL temporal (3600 s) del CV del candidato, sobre el bucket privado 'cvs'.

        Raises: CANDIDATO_NOT_FOUND (404) si no existe o es de otra empresa (fail-closed);
        CV_NOT_FOUND (404) si el candidato no tiene CV cargado.
        """
        candidato = self._candidato_repo.find_by_id(candidato_id, empresa_id)
        if not candidato:
            raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
        if not candidato.cv_storage_path:
            raise AppError("El candidato no tiene CV cargado", "CV_NOT_FOUND", 404)
        res = supabase_admin.storage.from_(_CV_BUCKET).create_signed_url(
            path=candidato.cv_storage_path, expires_in=3600
        )
        return res["signedURL"]

    def delete_candidato(self, candidato_id: str, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> None:
        """Elimina un candidato HUÉRFANO (sin búsqueda) y su CV del Storage. Solo huérfanos: los de
        búsqueda viva se gestionan desde la vacante. Si el remove físico del CV falla → log y sigue
        con el borrado de la fila. Raises CANDIDATO_NOT_FOUND (404), CANDIDATO_ACTIVO (400)."""
        cand = self._candidato_repo.find_by_id(candidato_id, empresa_id)
        if not cand:
            raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
        if cand.vacante_id is not None:
            raise AppError("No se puede eliminar un candidato de una búsqueda activa", "CANDIDATO_ACTIVO", 400)
        if cand.cv_storage_path:  # guard: nunca remove sobre key vacía; usa la key de la DB tal cual
            try:
                supabase_admin.storage.from_(_CV_BUCKET).remove([cand.cv_storage_path])
            except Exception as exc:  # storage falló: se conserva el flujo, objeto huérfano en Storage
                logger.error("Storage remove falló (CV)", extra={"candidato_id": candidato_id, "error": str(exc)})
        self._candidato_repo.delete(candidato_id, empresa_id)
        # 🔴 La empresa del evento sale del CANDIDATO (leído arriba), no del header: auditar es
        # una ACCIÓN y la empresa sale de la entidad afectada. Con el header, una baja hecha en
        # modo consolidado (empresa_id=None) grababa el evento sin empresa aunque el candidato
        # sí la tuviera — ya pasó una vez en producción. Ver "Vista vs Acción" en CLAUDE.md.
        self._audit.registrar(
            usuario_id=usuario_id, entidad="candidato", registro_id=candidato_id, accion="DELETE",
            evento="baja_candidato", empresa_id=cand.empresa_id,
            datos_anteriores={"nombre": f"{cand.nombre} {cand.apellido}", "email": cand.email}, datos_nuevos=None,
        )
        logger.info("Candidato eliminado", extra={"candidato_id": candidato_id})
