"""
Servicio de offboarding. Lógica de negocio del módulo de Offboarding.
Flujo: router → service → repository → DB
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.offboarding_repo import OffboardingRepo
from schemas.offboarding import OffboardingCreate, OffboardingResponse
from services._audit_payloads_offboarding import payload_devolucion_activo
from services._limite_export import verificar_limite_export
from services._offboarding_entrevista import registrar as _registrar_entrevista
from services._offboarding_export import construir_filas_export
from services._offboarding_iniciar import iniciar as _iniciar
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger


class OffboardingService:
    def __init__(
        self,
        repo: Optional[OffboardingRepo] = None,
        empleado_repo: Optional[EmpleadoRepo] = None,
        audit: Optional[AuditService] = None,
    ) -> None:
        self._repo = repo or OffboardingRepo()
        self._empleado_repo = empleado_repo or EmpleadoRepo()
        self._audit = audit or AuditService()

    def get_offboardings_activos(self, empresa_id: Optional[UUID] = None) -> list[OffboardingResponse]:
        """
        Retorna todos los offboardings activos filtrados por empresa (None = todas)
        con sus activos y el progreso de devolución calculado.

        Returns:
            Lista de OffboardingResponse ordenada por fecha de creación.
        """
        return self._repo.find_activos(empresa_id)

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel") -> Descarga:
        """Exporta los offboardings ACTIVOS — los mismos que muestra la pantalla.

        Va por el mismo `find_activos` que el listado, así que el archivo no puede traer filas
        que la pantalla no muestre. El listado no tiene filtros: no hay ninguno que se pueda
        perder entre las dos puntas. Qué columnas salen y por qué, en _offboarding_export.
        """
        items = self._repo.find_activos(empresa_id)
        verificar_limite_export(len(items))
        datos = {"Offboardings": construir_filas_export(items)}
        return build_export(nombre="Offboardings", datos=datos, filename_base="offboardings", formato=formato)

    def iniciar_offboarding(self, data: OffboardingCreate, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> OffboardingResponse:
        """Inicia el offboarding de un empleado y lo da de baja.
        Ver services/_offboarding_iniciar.iniciar (el ORDEN de los gates es load-bearing)."""
        return _iniciar(self._repo, self._empleado_repo, self._audit, data, empresa_id, usuario_id)

    def registrar_entrevista(
        self, instancia_id: UUID, entrevista_salida: bool, notas: Optional[str] = None,
        usuario_id: Optional[str] = None, empresa_id: Optional[UUID] = None,
    ) -> bool:
        """Registra la entrevista de salida del offboarding. Ver _offboarding_entrevista."""
        return _registrar_entrevista(self._repo, self._audit, instancia_id, entrevista_salida,
                                     notas, usuario_id, empresa_id)

    def marcar_activo_devuelto(
        self, instancia_id: UUID, activo_id: UUID, devuelto: bool,
        usuario_id: Optional[str] = None, empresa_id: Optional[UUID] = None,
    ) -> bool:
        """
        Actualiza el estado de devolución de un activo corporativo en el offboarding.
        Registra el evento de auditoría tras la actualización exitosa (usuario_id = operador).

        Args:
            instancia_id: UUID de la instancia de offboarding.
            activo_id: UUID del activo a actualizar.
            devuelto: True para marcar como devuelto, False para revertir a pendiente.
            usuario_id: ID del operador que realiza el cambio (trazabilidad de audit).
            empresa_id: empresa activa del request. Acota la INSTANCIA a esa empresa antes de
                escribir (None = consolidado) y además viaja al payload de audit. Antes solo
                alimentaba la auditoría, así que un activo de otra empresa se actualizaba igual.

        Returns:
            True si la actualización fue exitosa.

        Raises:
            AppError: ACTIVO_NOT_FOUND (404) si el activo no pertenece a la instancia, o si la
                instancia no existe / es de otra empresa (mismo 404: no delata existencia ajena).
        """
        if not self._repo.find_instancia_min(str(instancia_id), empresa_id):
            raise AppError("Activo no encontrado en esta instancia", "ACTIVO_NOT_FOUND", 404)
        ok = self._repo.update_activo(str(instancia_id), str(activo_id), devuelto)
        if not ok:
            raise AppError(
                "Activo no encontrado en esta instancia",
                "ACTIVO_NOT_FOUND",
                404,
            )
        self._audit.registrar(**payload_devolucion_activo(
            instancia_id, activo_id, devuelto, usuario_id, str(empresa_id) if empresa_id else None,
        ))
        logger.info(
            "Activo de offboarding actualizado",
            extra={
                "instancia_id": str(instancia_id),
                "activo_id": str(activo_id),
                "devuelto": devuelto,
            },
        )
        return True
