"""
Servicio de vacantes. Lógica de negocio del módulo de Vacantes y Pipeline.
Flujo: router → service → repository → DB
"""
from typing import List, Optional
from uuid import UUID

from repositories.candidato_repo import CandidatoRepo
from repositories.vacante_repo import VacanteRepo
from schemas.vacante import CandidatoCreate, CandidatoResponse, VacanteCreate, VacanteResponse, VacanteUpdate
from services._vacante_candidatos import agregar, mover
from services.adjunto_service import AdjuntoService
from services.audit_service import AuditService
from services.cv_service import CvService
from utils.errors import AppError
from utils.logger import logger

_ESTADOS = {"nueva", "en_proceso", "con_candidatos", "cerrada"}


class VacanteService:
    def __init__(self, repo: Optional[VacanteRepo] = None, candidato_repo: Optional[CandidatoRepo] = None, cv_service: Optional[CvService] = None, adjunto_service: Optional[AdjuntoService] = None, audit: Optional[AuditService] = None) -> None:
        self._repo = repo or VacanteRepo()
        self._candidato_repo = candidato_repo or CandidatoRepo()
        self._cv = cv_service or CvService()
        self._adjuntos = adjunto_service or AdjuntoService()
        self._audit = audit or AuditService()

    def get_vacantes(self, estado: Optional[str] = None, empresa_id: Optional[UUID] = None) -> List[VacanteResponse]:
        """
        Retorna la lista de vacantes, opcionalmente filtrada por estado y empresa.

        Args:
            estado: Filtro por estado ('nueva'|'en_proceso'|'con_candidatos'|'cerrada').
            empresa_id: Filtra por empresa. None = todas las empresas (vista consolidada).

        Returns:
            Lista de VacanteResponse ordenada por fecha de creación descendente.
        """
        return self._repo.find_all(estado, empresa_id)

    def get_vacante(self, id: UUID, empresa_id: Optional[UUID] = None) -> VacanteResponse:
        """
        Retorna el detalle de una vacante por ID.

        Args:
            id: UUID de la vacante a consultar.
            empresa_id: Si se provee, valida que la vacante pertenezca a esa empresa.

        Raises:
            AppError: VACANTE_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
        """
        vacante = self._repo.find_by_id(str(id), empresa_id)
        if not vacante:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        return vacante

    def create_vacante(self, data: VacanteCreate, created_by: str) -> VacanteResponse:
        """
        Crea una nueva vacante en estado 'nueva'. empresa_id viene en el body.

        Args:
            data: Datos de la vacante validados por Pydantic (incluye empresa_id).
            created_by: ID del usuario que realiza la operación (trazabilidad).
        """
        vacante = self._repo.save(data)
        self._audit.registrar(
            usuario_id=created_by, entidad="vacante", registro_id=vacante.id, accion="INSERT",
            evento="alta_vacante", empresa_id=vacante.empresa_id, datos_anteriores=None,
            datos_nuevos={"titulo": vacante.titulo, "area_id": vacante.area_id, "estado": vacante.estado},
        )
        logger.info("Vacante creada", extra={"vacante_id": vacante.id, "created_by": created_by})
        return vacante

    def update_vacante(self, id: UUID, data: VacanteUpdate, empresa_id: Optional[UUID] = None,
                       usuario_id: Optional[str] = None) -> VacanteResponse:
        """
        Actualiza los campos de una vacante existente (actualización parcial).

        Args:
            id: UUID de la vacante a actualizar.
            data: Campos a actualizar — solo los no-None se aplican.
            empresa_id: Si se provee, el UPDATE solo afecta vacantes de esa empresa.

        Raises:
            AppError: ESTADO_INVALIDO (400) si el estado no está en el enum.
            AppError: VACANTE_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
        """
        if data.estado and data.estado not in _ESTADOS:
            raise AppError(
                f"Estado inválido. Permitidos: {', '.join(_ESTADOS)}", "ESTADO_INVALIDO", 400
            )
        # Lectura previa para el diff: `update` devuelve la fila YA actualizada, así que sin esto
        # el evento no podría decir de qué valor se venía. El 404 es el mismo de abajo.
        previa = self._repo.find_by_id(str(id), empresa_id)
        if not previa:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        vacante = self._repo.update(str(id), data, empresa_id)
        if not vacante:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        tocados = data.model_dump(exclude_none=True)
        self._audit.registrar(
            usuario_id=usuario_id, entidad="vacante", registro_id=str(id), accion="UPDATE",
            evento="edicion_vacante", empresa_id=vacante.empresa_id,
            datos_anteriores={k: getattr(previa, k, None) for k in tocados},
            datos_nuevos={k: getattr(vacante, k, None) for k in tocados},
        )
        logger.info("Vacante actualizada", extra={"vacante_id": str(id)})
        return vacante

    def get_candidatos(self, vacante_id: UUID, empresa_id: Optional[UUID] = None) -> List[CandidatoResponse]:
        """Candidatos de una vacante por fecha. Raises VACANTE_NOT_FOUND (404) si no existe/otra empresa."""
        if not self._repo.find_by_id(str(vacante_id), empresa_id):
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        return self._candidato_repo.find_candidatos(str(vacante_id), empresa_id)

    def add_candidato(
        self, vacante_id: UUID, data: CandidatoCreate, empresa_id: Optional[UUID] = None,
        cv_content: Optional[bytes] = None, cv_filename: Optional[str] = None,
        cv_content_type: Optional[str] = None, usuario_id: Optional[str] = None,
    ) -> CandidatoResponse:
        """Agrega un candidato con CV opcional. Delegado a _vacante_candidatos.agregar."""
        return agregar(self._repo, self._candidato_repo, self._cv, self._audit, vacante_id, data,
                       empresa_id, cv_content, cv_filename, cv_content_type, usuario_id)

    def mover_candidato(self, candidato_id: UUID, etapa: str, empresa_id: Optional[UUID] = None,
                        usuario_id: Optional[str] = None) -> CandidatoResponse:
        """Mueve un candidato de etapa. Delegado a _vacante_candidatos.mover."""
        return mover(self._candidato_repo, self._audit, candidato_id, etapa, empresa_id, usuario_id)

    def delete_vacante(self, id: UUID, empresa_id: Optional[UUID] = None, rol: Optional[str] = None, usuario_id: Optional[str] = None) -> None:
        """Elimina la vacante. Orden estricto: (1) congela el nombre en sus candidatos (sobreviven
        vía FK SET NULL, migración 071), (2) borra físicamente + soft-delete sus imágenes, (3) borra
        la fila. Raises VACANTE_NOT_FOUND (404)."""
        vac = self._repo.find_by_id(str(id), empresa_id)
        if not vac:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
        texto = f"{vac.titulo} — {vac.area_nombre}" if vac.area_nombre else vac.titulo
        self._candidato_repo.congelar_busqueda(str(id), texto, empresa_id)  # ANTES de borrar la vacante
        self._adjuntos.eliminar_todos_por_entidad("vacante", str(id), empresa_id, rol, usuario_id)
        self._repo.delete(str(id), empresa_id)
        self._audit.registrar(
            usuario_id=usuario_id, entidad="vacante", registro_id=str(id), accion="DELETE",
            evento="baja_vacante", empresa_id=vac.empresa_id,
            datos_anteriores={"titulo": vac.titulo}, datos_nuevos=None,
        )
        logger.info("Vacante eliminada", extra={"vacante_id": str(id)})
