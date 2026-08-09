"""
Servicio de vacantes. Lógica de negocio del módulo de Vacantes y Pipeline.
Flujo: router → service → repository → DB
"""
from typing import List, Optional
from uuid import UUID

from repositories.candidato_repo import CandidatoRepo
from repositories.integracion_remitente_repo import IntegracionRemitenteRepo
from repositories.vacante_repo import VacanteRepo
from schemas.vacante import AvisoPostulacionResponse, CandidatoCreate, CandidatoResponse, VacanteCreate, VacanteResponse, VacanteUpdate
from services._limite_export import verificar_limite_export
from services._vacante_aviso import aviso as _aviso
from services._vacante_candidatos import agregar, mover
from services._vacantes_export import construir_filas_export
from services._vacante_write import actualizar as _actualizar
from services._vacante_write import crear as _crear
from services._vacante_write import eliminar as _eliminar
from services.adjunto_service import AdjuntoService
from services.audit_service import AuditService
from services.cv_service import CvService
from services.export import Descarga, build_export
from utils.errors import AppError

class VacanteService:
    def __init__(self, repo: Optional[VacanteRepo] = None, candidato_repo: Optional[CandidatoRepo] = None, cv_service: Optional[CvService] = None, adjunto_service: Optional[AdjuntoService] = None, audit: Optional[AuditService] = None, remitente_repo: Optional[IntegracionRemitenteRepo] = None) -> None:
        self._repo = repo or VacanteRepo()
        self._candidato_repo = candidato_repo or CandidatoRepo()
        self._cv = cv_service or CvService()
        self._adjuntos = adjunto_service or AdjuntoService()
        self._audit = audit or AuditService()
        self._remitente_repo = remitente_repo or IntegracionRemitenteRepo()

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

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel",
                 estado: Optional[str] = None) -> Descarga:
        """Exporta el listado de vacantes con el MISMO filtro que la pantalla.

        Va por el mismo `find_all` que `get_vacantes`, así que el archivo no puede traer filas
        que el listado no muestre. Qué columnas salen y por qué, en _vacantes_export.
        """
        items = self._repo.find_all(estado, empresa_id)
        verificar_limite_export(len(items))
        datos = {"Vacantes": construir_filas_export(items)}
        return build_export(nombre="Vacantes", datos=datos, filename_base="vacantes", formato=formato)

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
        """Crea una vacante en estado 'nueva'. Ver services/_vacante_write.crear."""
        return _crear(self._repo, self._audit, data, created_by)

    def update_vacante(self, id: UUID, data: VacanteUpdate, empresa_id: Optional[UUID] = None,
                       usuario_id: Optional[str] = None) -> VacanteResponse:
        """Actualización parcial de la vacante. Ver services/_vacante_write.actualizar."""
        return _actualizar(self._repo, self._audit, id, data, empresa_id, usuario_id)

    def get_aviso(self, id: UUID, empresa_id: Optional[UUID] = None) -> AvisoPostulacionResponse:
        """Texto listo para pegar en el aviso de LinkedIn. Ver services/_vacante_aviso."""
        return _aviso(self._repo, self._remitente_repo, id, empresa_id)

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
        """Elimina la vacante y congela el nombre de la búsqueda en sus candidatos.
        Ver services/_vacante_write.eliminar (el ORDEN del borrado es load-bearing)."""
        _eliminar(self._repo, self._candidato_repo, self._adjuntos, self._audit,
                  id, empresa_id, rol, usuario_id)
