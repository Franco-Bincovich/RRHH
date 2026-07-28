"""
Servicio de offboarding. Lógica de negocio del módulo de Offboarding.
Flujo: router → service → repository → DB
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.offboarding_repo import OffboardingRepo
from schemas.offboarding import OffboardingCreate, OffboardingResponse
from services._audit_payloads import payload_devolucion_activo, payload_inicio_offboarding
from services._empleado_scope import ensure_empleado_de_empresa
from services._offboarding_entrevista import registrar as _registrar_entrevista
from services.audit_service import AuditService
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

    def iniciar_offboarding(self, data: OffboardingCreate, empresa_id: Optional[UUID] = None, usuario_id: Optional[str] = None) -> OffboardingResponse:
        """
        Inicia el proceso de offboarding para un empleado.
        La empresa en la que se escribe se hereda del empleado (es un dato del empleado, no del
        contexto de sesión) — eso NO cambia. empresa_id del header se usa solo como barrera de
        a qué empleado se puede apuntar; validado eso, ambas coinciden por construcción.
        Crea la instancia y los activos corporativos por defecto a devolver.
        Registra el evento de auditoría tras crear la instancia (usuario_id = operador).

        Args:
            data: Datos del offboarding — empleado_id, motivo y fecha_ultimo_dia opcional.
            empresa_id: empresa activa del request. Acota A QUÉ EMPLEADO se puede apuntar (no la
                empresa en la que se escribe, que se deriva del empleado). None = todas.

        Returns:
            OffboardingResponse con la instancia creada y activos por defecto.

        Raises:
            AppError: EMPLEADO_NOT_FOUND (404) si el empleado no existe o es de otra empresa.
            AppError: OFFBOARDING_ALREADY_ACTIVE (409) si el empleado ya tiene un offboarding activo.
        """
        empleado = ensure_empleado_de_empresa(self._empleado_repo, data.empleado_id, empresa_id)

        existente = self._repo.find_by_empleado(str(data.empleado_id))
        if existente:
            raise AppError(
                "El empleado ya tiene un proceso de offboarding activo",
                "OFFBOARDING_ALREADY_ACTIVE",
                409,
            )

        empresa_id_str = empleado.empresa_id or ""
        offboarding = self._repo.create_offboarding(data, empresa_id_str)
        self._audit.registrar(**payload_inicio_offboarding(offboarding, usuario_id, empresa_id_str or None))

        fecha_egreso = data.fecha_ultimo_dia or (date.today() + timedelta(days=30))
        empresa_uuid = UUID(empresa_id_str) if empresa_id_str else None
        if not self._empleado_repo.dar_de_baja(str(data.empleado_id), fecha_egreso, empresa_uuid):
            logger.warning(
                "Offboarding iniciado pero no se pudo actualizar estado del empleado",
                extra={
                    "empleado_id": str(data.empleado_id),
                    "instancia_id": str(offboarding.id),
                },
            )

        logger.info(
            "Offboarding iniciado",
            extra={
                "empleado_id": str(data.empleado_id),
                "motivo": data.motivo,
                "instancia_id": str(offboarding.id),
            },
        )
        return offboarding

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
